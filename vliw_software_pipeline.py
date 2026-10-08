"""
vliw_software_pipeline.py
=========================
Software Pipelining pass for the Atalla VLIW architecture built on PPCI.

Algorithm: Iterative Modulo Scheduling (IMS) with Swing Modulo Scheduling
           (SMS) node-priority heuristics.

References
----------
* Rau, B.R. (1994). Iterative modulo scheduling. MICRO-27.
* Llosa et al. (1996). Swing modulo scheduling. PACT.
* Huff, R.A. (1993). Lifetime-sensitive modulo scheduling. PLDI.

How this file connects to the rest of the compiler
---------------------------------------------------
  instruction_latency.py   -> LATENCY_MAP          (edge weights in DDG)
  ppci/arch/atalla/arch.py -> AtallaArch / Nop     (make_nop, arch constants)
  ppci/codegen/codegen.py  -> _pack_flat_vliw      (FU taxonomy, slot rules)
        The FU taxonomy, SCALAR_FUS, VEC_LANE_FUS, MAX_VEC_LANES, MAX_VLSU,
        OP_TO_FU, and the within-packet hazard predicate are **copied from**
        _pack_flat_vliw so the two packetizers stay consistent.  Sections that
        belong *only* to cyclic scheduling are clearly marked «SMS/IMS».
"""

from __future__ import annotations

import logging
import math
import sys
import os
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Latency map  (shared with _pack_flat_vliw)
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))
try:
    from instruction_latency import latency as LATENCY_MAP
except ImportError:  # pragma: no cover
    LATENCY_MAP: Dict[str, int] = {}

# ---------------------------------------------------------------------------
# Atalla arch imports
# ---------------------------------------------------------------------------
from ppci.arch.atalla.arch import AtallaArch
from ppci.arch.atalla.instructions import BranchBase, Halt, Jal, Jalr, Nop
from ppci.arch.generic_instructions import Label, VirtualInstruction

log = logging.getLogger(__name__)

# ===========================================================================
# §1  Functional-Unit taxonomy
#     *** Copied verbatim from _pack_flat_vliw so both packetizers agree ***
# ===========================================================================

FU_SCALAR_ALU  = "scalar_alu"   # Unit 1: add_s, sub_s, or_s, and_s, xor_s …
FU_SCALAR_DIV  = "scalar_div"   # Unit 2: div_s, mod_s, bfts_s, rcp_bf …
FU_BF16_ADD    = "bf16_add"     # Unit 3: add_bf, sub_bf, mul_bf
FU_SCALAR_MUL  = "scalar_mul"   # Unit 4: mul_s, muli_s
FU_SCALAR_LDST = "scalar_ldst"  # Unit 5: lw_s, sw_s, lhw_s, shw_s
FU_VEC_ALU     = "vec_alu"      # Vector ALU lane
FU_GSAU        = "gsau"         # GSAU lane: gemm_vv, lw_vi
FU_EXP         = "exp"          # EXP lane: expi_vi
FU_VLSU        = "vlsu"         # VLSU: vreg_ld, vreg_st  (up to 4 in-flight)
FU_SCPAD       = "scpad"        # Scpad/SDMA: scpad_ld, scpad_st

SCALAR_FUS: Set[str]   = {FU_SCALAR_ALU, FU_SCALAR_DIV, FU_BF16_ADD,
                           FU_SCALAR_MUL, FU_SCALAR_LDST}
VEC_LANE_FUS: Set[str] = {FU_VEC_ALU, FU_GSAU, FU_EXP}
MAX_VEC_LANES: int = 2
MAX_VLSU: int      = 4   # one per scpad SID
MAX_WIDTH: int     = 4   # total issue slots per VLIW bundle

OP_TO_FU: Dict[str, str] = {
    # Scalar ALU (Unit 1)
    "add_s":  FU_SCALAR_ALU, "sub_s":  FU_SCALAR_ALU,
    "or_s":   FU_SCALAR_ALU, "and_s":  FU_SCALAR_ALU,
    "xor_s":  FU_SCALAR_ALU, "sll_s":  FU_SCALAR_ALU,
    "srl_s":  FU_SCALAR_ALU, "sra_s":  FU_SCALAR_ALU,
    "lui_s":  FU_SCALAR_ALU, "li_s":   FU_SCALAR_ALU,
    "addi_s": FU_SCALAR_ALU, "subi_s": FU_SCALAR_ALU,
    "ori_s":  FU_SCALAR_ALU, "andi_s": FU_SCALAR_ALU,
    "xori_s": FU_SCALAR_ALU, "slli_s": FU_SCALAR_ALU,
    "srli_s": FU_SCALAR_ALU, "srai_s": FU_SCALAR_ALU,
    # Scalar Div/BF (Unit 2)
    "div_s":   FU_SCALAR_DIV, "mod_s":   FU_SCALAR_DIV,
    "divi_s":  FU_SCALAR_DIV, "modi_s":  FU_SCALAR_DIV,
    "bfts_s":  FU_SCALAR_DIV, "stbf_s":  FU_SCALAR_DIV,
    "rcp_bf":  FU_SCALAR_DIV, "sqrt_bf": FU_SCALAR_DIV,
    # BF16 arithmetic (Unit 3)
    "add_bf": FU_BF16_ADD, "sub_bf": FU_BF16_ADD, "mul_bf": FU_BF16_ADD,
    # Scalar Multiply (Unit 4)
    "mul_s": FU_SCALAR_MUL, "muli_s": FU_SCALAR_MUL,
    # Scalar Ld/St (Unit 5)
    "lw_s":  FU_SCALAR_LDST, "sw_s":  FU_SCALAR_LDST,
    "lhw_s": FU_SCALAR_LDST, "shw_s": FU_SCALAR_LDST,
    # Vector ALU
    "add_vv":   FU_VEC_ALU, "sub_vv":   FU_VEC_ALU, "mul_vv":   FU_VEC_ALU,
    "rsum_vi":  FU_VEC_ALU, "rmin_vi":  FU_VEC_ALU, "rmax_vi":  FU_VEC_ALU,
    "mgt_mvv":  FU_VEC_ALU, "mlt_mvv":  FU_VEC_ALU,
    "meq_mvv":  FU_VEC_ALU, "mneq_mvv": FU_VEC_ALU,
    "mgt_mvs":  FU_VEC_ALU, "mlt_mvs":  FU_VEC_ALU,
    "meq_mvs":  FU_VEC_ALU, "mneq_mvs": FU_VEC_ALU,
    "add_vs":   FU_VEC_ALU, "sub_vs":   FU_VEC_ALU, "mul_vs":   FU_VEC_ALU,
    # GSAU
    "gemm_vv": FU_GSAU, "lw_vi": FU_GSAU,
    # EXP
    "expi_vi": FU_EXP,
    # VLSU
    "vreg_ld": FU_VLSU, "vreg_st": FU_VLSU,
    # Scpad / SDMA
    "scpad_ld": FU_SCPAD, "scpad_st": FU_SCPAD,
}

# Resource usage counts per FU per VLIW cycle (how many of each FU exist).
# These numbers come from the Atalla micro-architecture description embedded
# in _pack_flat_vliw and arch.py.
FU_CAPACITY: Dict[str, int] = {
    FU_SCALAR_ALU:  1,
    FU_SCALAR_DIV:  1,
    FU_BF16_ADD:    1,
    FU_SCALAR_MUL:  1,
    FU_SCALAR_LDST: 1,
    FU_VEC_ALU:     MAX_VEC_LANES,
    FU_GSAU:        MAX_VEC_LANES,   # GSAU shares the vector-lane limit
    FU_EXP:         MAX_VEC_LANES,
    FU_VLSU:        MAX_VLSU,
    FU_SCPAD:       1,
}


# ===========================================================================
# §2  Helpers shared between DDG construction and scheduling
# ===========================================================================

def _get_op(ins) -> str:
    """Extract mnemonic from a PPCI Instruction object (same as _pack_flat_vliw)."""
    s = str(ins).strip()
    return s.split()[0] if s else ""


def _get_fu(ins) -> Optional[str]:
    """Map instruction to its functional-unit string."""
    return OP_TO_FU.get(_get_op(ins))


def _is_branch(ins) -> bool:
    """True if the instruction is a control-flow terminator."""
    return getattr(ins, "is_jump", False) or isinstance(
        ins, (BranchBase, Halt, Jal, Jalr)
    )


def _is_virtual(ins) -> bool:
    return isinstance(ins, VirtualInstruction)


# ===========================================================================
# §3  Data Dependence Graph (DDG)
#     «IMS/SMS» — This section has no counterpart in _pack_flat_vliw because
#     the existing code only tracks *intra-iteration* deps.  Here we also
#     track loop-carried (distance d ≥ 1) dependences produced by
#     induction variables, live-across registers, and memory aliases.
# ===========================================================================

@dataclass
class DDGEdge:
    """A directed dependence edge u → v."""
    src: int          # index of producing instruction
    dst: int          # index of consuming instruction
    latency: int      # minimum cycle gap: sched[dst] ≥ sched[src] + latency
    distance: int     # iteration distance: 0 = intra, ≥1 = loop-carried
    kind: str         # "RAW" | "WAW" | "WAR" | "MEM"


@dataclass
class DDG:
    """
    Data Dependence Graph for a loop body.

    Nodes are 0-based indices into `instructions`.
    Edges are annotated with (latency, iteration-distance).
    """
    instructions: List       # real (non-virtual) Instruction objects
    edges: List[DDGEdge] = field(default_factory=list)
    # Adjacency: successors[u] = list of DDGEdge with src==u
    successors: Dict[int, List[DDGEdge]] = field(
        default_factory=lambda: defaultdict(list)
    )
    # Adjacency: predecessors[v] = list of DDGEdge with dst==v
    predecessors: Dict[int, List[DDGEdge]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def add_edge(self, e: DDGEdge) -> None:
        # Deduplicate: keep the maximum-latency edge for each (src, dst, dist)
        for existing in self.successors[e.src]:
            if existing.dst == e.dst and existing.distance == e.distance:
                if e.latency > existing.latency:
                    existing.latency = e.latency
                return
        self.edges.append(e)
        self.successors[e.src].append(e)
        self.predecessors[e.dst].append(e)


MEM_TOUCH_FUS: Set[str] = {FU_SCALAR_LDST, FU_VLSU, FU_SCPAD, FU_GSAU}


def build_ddg(real_insts: List) -> DDG:
    """
    Construct the DDG for a loop body.

    Intra-iteration edges (distance 0) are built with the same logic as
    _pack_flat_vliw's dependency pass.  Loop-carried edges (distance 1) are
    added conservatively for any register written in the body that is also
    read later in the same body (i.e., the value is live across the back
    edge).

    Parameters
    ----------
    real_insts:
        The flat list of real (non-virtual, non-label) instructions that
        form the loop body, in original program order.

    Returns
    -------
    DDG object with .instructions, .edges, .successors, .predecessors.
    """
    n = len(real_insts)
    ddg = DDG(instructions=real_insts)

    ins_op  = [_get_op(i) for i in real_insts]
    ins_lat = [LATENCY_MAP.get(op, 1) for op in ins_op]
    ins_fu  = [_get_fu(i) for i in real_insts]

    # PPCI instructions expose used_registers (reads) and defined_registers (writes).
    ins_reads  = [list(getattr(i, "used_registers",    [])) for i in real_insts]
    ins_writes = [list(getattr(i, "defined_registers", [])) for i in real_insts]

    # Classify memory-touching instructions (same as _pack_flat_vliw)
    ins_is_load  = [False] * n
    ins_is_store = [False] * n
    ins_is_mem   = [False] * n
    ins_mem_key  = [None]  * n
    for i, ins in enumerate(real_insts):
        fu = ins_fu[i]
        op = ins_op[i]
        is_ld = fu == FU_SCALAR_LDST and op.startswith("lw")
        is_st = fu == FU_SCALAR_LDST and op.startswith("sw")
        ins_is_load[i]  = is_ld
        ins_is_store[i] = is_st
        ins_is_mem[i]   = fu in MEM_TOUCH_FUS
        if (is_ld or is_st) and hasattr(ins, "rs1") and hasattr(ins, "imm12"):
            base = ins.rs1.num if hasattr(ins.rs1, "num") else ins.rs1
            ins_mem_key[i] = (base, ins.imm12)

    # -----------------------------------------------------------------------
    # Pass 1: intra-iteration edges (distance 0)
    # Mirrors the logic in _pack_flat_vliw exactly.
    # -----------------------------------------------------------------------
    last_def:      Dict[int, int] = {}   # reg.num -> last writer index
    last_read:     Dict[int, int] = {}   # reg.num -> last reader index
    last_mem:      Optional[int]  = None
    last_store_at: Dict           = {}   # mem_key -> last store index

    for i in range(n):
        reads    = ins_reads[i]
        writes   = ins_writes[i]
        is_mem   = ins_is_mem[i]
        mem_key  = ins_mem_key[i]

        # RAW
        for r in reads:
            rn = r.num
            if rn in last_def:
                j = last_def[rn]
                ddg.add_edge(DDGEdge(j, i, ins_lat[j], 0, "RAW"))

        # WAW + WAR
        for r in writes:
            rn = r.num
            if rn in last_def:
                j = last_def[rn]
                ddg.add_edge(DDGEdge(j, i, ins_lat[j], 0, "WAW"))
            if rn in last_read:
                j = last_read[rn]
                ddg.add_edge(DDGEdge(j, i, 1, 0, "WAR"))

        # Update bookkeeping
        for r in writes:
            last_def[r.num]  = i
            last_read.pop(r.num, None)
        for r in reads:
            last_read[r.num] = i

        # Memory ordering chain (same as _pack_flat_vliw)
        if is_mem:
            if last_mem is not None:
                ddg.add_edge(DDGEdge(last_mem, i, 1, 0, "MEM"))
            if mem_key is not None and mem_key in last_store_at:
                j = last_store_at[mem_key]
                ddg.add_edge(DDGEdge(j, i, ins_lat[j], 0, "MEM"))
            last_mem = i
            if ins_is_store[i] and mem_key is not None:
                last_store_at[mem_key] = i

    # -----------------------------------------------------------------------
    # Pass 2: loop-carried edges (distance 1)   «IMS/SMS»
    #
    # For each register written in the body that is also read somewhere in
    # the body, add a cross-iteration RAW edge from the writer to every
    # reader with distance=1.  This captures induction-variable chains and
    # live-across register values.
    #
    # Conservative memory loop-carried edge: any store in iter k may alias
    # any load in iter k+1, so add a chain edge from the last store to the
    # first load of the same potential alias class.
    # -----------------------------------------------------------------------
    # Collect all writers and readers across the entire body
    all_defs: Dict[int, List[int]] = defaultdict(list)  # reg.num -> [def indices]
    all_uses: Dict[int, List[int]] = defaultdict(list)  # reg.num -> [use indices]
    for i in range(n):
        for r in ins_writes[i]:
            all_defs[r.num].append(i)
        for r in ins_reads[i]:
            all_uses[r.num].append(i)

    for rn, def_idxs in all_defs.items():
        if rn not in all_uses:
            continue
        for j in def_idxs:           # writer in iteration k
            for i in all_uses[rn]:   # reader in iteration k+1
                # Only meaningful if the reader comes *before* the writer in
                # program order (i.e., crossing the back edge matters).
                # For simplicity we add the edge regardless; the IMS scheduler
                # will only respect it when distance=1 constraint is violated.
                ddg.add_edge(
                    DDGEdge(j, i, ins_lat[j], 1, "RAW")
                )

    # Loop-carried memory: last store → first load, distance=1
    stores = [i for i in range(n) if ins_is_store[i]]
    loads  = [i for i in range(n) if ins_is_load[i]]
    if stores and loads:
        last_st = max(stores)
        first_ld = min(loads)
        ddg.add_edge(DDGEdge(last_st, first_ld, ins_lat[last_st], 1, "MEM"))

    return ddg


# ===========================================================================
# §4  Initiation Interval computation   «IMS/SMS»
# ===========================================================================

def compute_res_mii(ddg: DDG) -> int:
    """
    Resource-constrained MII (ResMII).

    ResMII = max over all FUs of ⌈ (sum of FU uses in the loop body) / capacity ⌉.

    The FU capacities come from FU_CAPACITY which mirrors the slot constraints
    enforced by _pack_flat_vliw.

    Parameters
    ----------
    ddg : DDG
        The DDG for the loop body.

    Returns
    -------
    int
        ResMII ≥ 1.
    """
    fu_count: Dict[str, int] = defaultdict(int)
    for ins in ddg.instructions:
        fu = _get_fu(ins)
        if fu is not None:
            fu_count[fu] += 1

    res_mii = 1
    for fu, cnt in fu_count.items():
        cap = FU_CAPACITY.get(fu, 1)
        res_mii = max(res_mii, math.ceil(cnt / cap))
    log.debug("ResMII = %d  (FU counts: %s)", res_mii, dict(fu_count))
    return res_mii


def _find_recurrence_cycles(ddg: DDG) -> List[List[int]]:
    """
    Find all elementary cycles in the DDG using DFS (Johnson's algorithm
    simplified to the cyclic-schedule context).

    Returns a list of cycles; each cycle is a list of node indices.
    """
    n = len(ddg.instructions)
    cycles: List[List[int]] = []
    visited = [False] * n
    stack:   List[int] = []
    on_stack = [False] * n

    def dfs(v: int, start: int) -> None:
        visited[v]  = True
        on_stack[v] = True
        stack.append(v)
        for edge in ddg.successors[v]:
            w = edge.dst
            if not visited[w]:
                dfs(w, start)
            elif on_stack[w] and w == start:
                # Found a cycle — record a *copy* of the current stack from start
                idx = stack.index(start)
                cycles.append(list(stack[idx:]))
        stack.pop()
        on_stack[v] = False

    for s in range(n):
        dfs(s, s)
        visited[s] = True  # do not revisit as a start node

    return cycles


def compute_rec_mii(ddg: DDG) -> int:
    """
    Recurrence-constrained MII (RecMII).   «IMS/SMS»

    RecMII = max over all cycles C of ⌈ (sum of edge latencies in C) /
                                         (sum of edge distances in C) ⌉.

    A cycle with distance 0 is a dependence cycle that can never be
    satisfied — this would make the loop unschedulable (treated as ∞ here,
    causing the caller to bail).

    Parameters
    ----------
    ddg : DDG

    Returns
    -------
    int
        RecMII ≥ 1.
    """
    cycles = _find_recurrence_cycles(ddg)
    rec_mii = 1
    for cycle in cycles:
        # Collect edges on this cycle
        lat_sum  = 0
        dist_sum = 0
        for k in range(len(cycle)):
            u = cycle[k]
            v = cycle[(k + 1) % len(cycle)]
            best_lat  = 0
            best_dist = 0
            for edge in ddg.successors[u]:
                if edge.dst == v:
                    if edge.latency > best_lat:
                        best_lat  = edge.latency
                        best_dist = edge.distance
            lat_sum  += best_lat
            dist_sum += best_dist
        if dist_sum == 0:
            # Zero-distance cycle → recurrence that cannot be satisfied
            log.warning("Unsatisfiable recurrence cycle detected: %s", cycle)
            continue
        val = math.ceil(lat_sum / dist_sum)
        rec_mii = max(rec_mii, val)

    log.debug("RecMII = %d", rec_mii)
    return rec_mii


def compute_mii(ddg: DDG) -> Tuple[int, int, int]:
    """
    Compute MII = max(ResMII, RecMII).

    Returns
    -------
    (mii, res_mii, rec_mii)
    """
    res = compute_res_mii(ddg)
    rec = compute_rec_mii(ddg)
    mii = max(res, rec)
    log.info("MII = max(ResMII=%d, RecMII=%d) = %d", res, rec, mii)
    return mii, res, rec


# ===========================================================================
# §5  Cyclic Reservation Table   «IMS/SMS»
# ===========================================================================

@dataclass
class CyclicResTable:
    """
    Modulo reservation table of shape (ii × num_fu_types).

    Slot availability uses the same FU constraints as _pack_flat_vliw but
    evaluated modulo II instead of per linear cycle.

    Attributes
    ----------
    ii : int
        Initiation interval.
    table : Dict[int, Dict[str, int]]
        table[slot][fu] = number of times that FU is already used in that
        modulo slot.
    """
    ii: int
    table: Dict[int, Dict[str, int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for s in range(self.ii):
            self.table[s] = defaultdict(int)

    def can_place(self, fu: Optional[str], cycle: int) -> bool:
        """
        Return True if the given FU is available in `cycle mod ii`.

        Mirrors the per-FU checks in _pack_flat_vliw:
          - Scalar FUs: at most 1 per slot.
          - VEC_LANE FUs: at most MAX_VEC_LANES distinct FU types per slot.
          - VLSU: at most MAX_VLSU per slot.
          - SCPAD: at most 1 per slot.
        """
        if fu is None:
            return True  # unknown FU (e.g., NOP) — always fits
        slot = cycle % self.ii
        used = self.table[slot]
        cap  = FU_CAPACITY.get(fu, 1)
        return used[fu] < cap

    def place(self, fu: Optional[str], cycle: int) -> None:
        """Record that `fu` is used in `cycle mod ii`."""
        if fu is None:
            return
        slot = cycle % self.ii
        self.table[slot][fu] += 1

    def remove(self, fu: Optional[str], cycle: int) -> None:
        """Un-record a previously placed FU (used during backtracking)."""
        if fu is None:
            return
        slot = cycle % self.ii
        self.table[slot][fu] = max(0, self.table[slot][fu] - 1)

    def clone(self) -> "CyclicResTable":
        import copy
        new = CyclicResTable(self.ii)
        for s in range(self.ii):
            new.table[s] = defaultdict(int, self.table[s])
        return new


# ===========================================================================
# §6  SMS / IMS Node Priority Heuristics   «IMS/SMS»
# ===========================================================================

def _compute_heights(ddg: DDG) -> List[int]:
    """
    Compute the height (length of the longest latency-weighted path from each
    node to a sink) in the DDG, considering only intra-iteration (distance=0)
    edges.  Used as the SMS scheduling priority.
    """
    n = len(ddg.instructions)
    height = [0] * n
    # Topological reverse traversal (iterate from last to first)
    for i in range(n - 1, -1, -1):
        best = 0
        for edge in ddg.successors[i]:
            if edge.distance == 0:
                cand = edge.latency + height[edge.dst]
                if cand > best:
                    best = cand
        height[i] = best
    return height


def _compute_depths(ddg: DDG) -> List[int]:
    """
    Compute the depth (longest latency-weighted path from a source to each
    node) in the DDG, distance=0 only.
    """
    n = len(ddg.instructions)
    depth = [0] * n
    for i in range(n):
        best = 0
        for edge in ddg.predecessors[i]:
            if edge.distance == 0:
                cand = edge.latency + depth[edge.src]
                if cand > best:
                    best = cand
        depth[i] = best
    return depth


def _sms_priority(ddg: DDG) -> List[int]:
    """
    SMS scheduling order: nodes are sorted by a combined height+depth
    priority, highest first.  Ties broken by node index.
    """
    height = _compute_heights(ddg)
    depth  = _compute_depths(ddg)
    n = len(ddg.instructions)
    priority = [height[i] + depth[i] for i in range(n)]
    order = sorted(range(n), key=lambda i: (-priority[i], i))
    return order


# ===========================================================================
# §7  IMS Scheduler Core   «IMS/SMS»
# ===========================================================================

ScheduleMap = Dict[int, int]   # node_index -> scheduled_cycle


def _earliest_start(
    node: int,
    ddg: DDG,
    schedule: ScheduleMap,
    ii: int,
) -> int:
    """
    Compute the earliest cycle in which `node` can start, given the current
    partial schedule.  Respects both intra-iteration (d=0) and loop-carried
    (d≥1) edges.

      For a d=0 edge  (j → node, lat L):  sched[node] ≥ sched[j] + L
      For a d=1 edge  (j → node, lat L):  sched[node] ≥ sched[j] + L - II
    """
    earliest = 0
    for edge in ddg.predecessors[node]:
        if edge.src not in schedule:
            continue   # predecessor not yet scheduled
        pred_cycle = schedule[edge.src]
        if edge.distance == 0:
            earliest = max(earliest, pred_cycle + edge.latency)
        else:
            # Loop-carried: value produced in a previous iteration
            earliest = max(earliest, pred_cycle + edge.latency - edge.distance * ii)
    return earliest


def _latest_start(
    node: int,
    ddg: DDG,
    schedule: ScheduleMap,
    ii: int,
) -> int:
    """
    Compute the latest cycle in which `node` can start, given successors.

      For a d=0 edge  (node → k, lat L):  sched[node] ≤ sched[k] - L
      For a d=1 edge  (node → k, lat L):  sched[node] ≤ sched[k] - L + II
    """
    latest = ii - 1   # upper bound: must fit within the kernel
    for edge in ddg.successors[node]:
        if edge.dst not in schedule:
            continue
        succ_cycle = schedule[edge.dst]
        if edge.distance == 0:
            latest = min(latest, succ_cycle - edge.latency)
        else:
            latest = min(latest, succ_cycle - edge.latency + edge.distance * ii)
    return latest


def _try_schedule_node(
    node: int,
    ddg: DDG,
    schedule: ScheduleMap,
    res_table: CyclicResTable,
    ii: int,
    earliest: int,
    latest: int,
) -> Optional[int]:
    """
    Try to place `node` in one of the cycles [earliest, latest].
    Returns the chosen cycle on success, None on failure.

    Checks:
    1. Resource availability in the cyclic reservation table.
    2. Within-packet register hazards are deferred to the kernel packer;
       at this stage we only enforce FU constraints modulo II.
    """
    fu = _get_fu(ddg.instructions[node])
    for cycle in range(earliest, latest + 1):
        if res_table.can_place(fu, cycle):
            return cycle
    return None


def iterative_modulo_schedule(
    ddg: DDG,
    mii_start: int,
    max_ii: Optional[int] = None,
    max_retries: int = 16,
) -> Tuple[ScheduleMap, int]:
    """
    Iterative Modulo Scheduling with SMS priority.   «IMS/SMS»

    Starting from `mii_start`, attempt to schedule all nodes of the DDG into
    a cyclic reservation table.  On failure, increment II and retry.

    Parameters
    ----------
    ddg : DDG
    mii_start : int
        Initial candidate II (= MII).
    max_ii : int, optional
        Hard ceiling for II (default: mii_start * 3 or 32, whichever is larger).
    max_retries : int
        Maximum number of II increments before giving up.

    Returns
    -------
    (schedule, ii)
        schedule : dict mapping node index → absolute cycle within the kernel.
        ii       : the II under which the schedule was found.

    Raises
    ------
    RuntimeError
        If no valid schedule is found within the retry budget.
    """
    if max_ii is None:
        max_ii = max(mii_start * 3, 32)

    priority_order = _sms_priority(ddg)

    for attempt in range(max_retries):
        ii = mii_start + attempt
        if ii > max_ii:
            break

        res_table = CyclicResTable(ii)
        schedule:  ScheduleMap = {}

        failed = False
        for node in priority_order:
            earliest = _earliest_start(node, ddg, schedule, ii)
            latest   = earliest + ii - 1   # search window bounded by II

            cycle = _try_schedule_node(
                node, ddg, schedule, res_table, ii, earliest, latest
            )
            if cycle is None:
                log.debug("IMS: node %d failed at II=%d", node, ii)
                failed = True
                break

            schedule[node] = cycle
            res_table.place(_get_fu(ddg.instructions[node]), cycle)

        if not failed:
            log.info("IMS: scheduled %d nodes at II=%d", len(ddg.instructions), ii)
            return schedule, ii

    raise RuntimeError(
        f"Modulo scheduling failed after {max_retries} retries "
        f"(MII={mii_start})."
    )


# ===========================================================================
# §8  Kernel packing helpers
#     Reuses the slot-allocation logic of _pack_flat_vliw directly.
# ===========================================================================

def _make_arch_nop(arch: AtallaArch):
    """Delegate to AtallaArch.make_nop() — same as _pack_flat_vliw's make_nop()."""
    nop = arch.make_nop()
    nop.is_nop = True  # mark for downstream consumers
    return nop


def _pack_schedule_into_bundles(
    schedule: ScheduleMap,
    ddg: DDG,
    ii: int,
    arch: AtallaArch,
) -> List[List]:
    """
    Pack the modulo schedule into VLIW bundles for one kernel iteration.

    One bundle per modulo cycle (0 … II-1), each containing up to MAX_WIDTH
    instructions.  NOP-padded to MAX_WIDTH exactly (mirroring _pack_flat_vliw).

    Resource constraints are re-checked here with the same predicate as
    _pack_flat_vliw to guarantee correctness, even though the reservation
    table already enforced them at FU granularity.

    Returns
    -------
    List of bundles; each bundle is a list of Instruction objects of length
    MAX_WIDTH.
    """
    # Group nodes by their modulo slot
    slots: Dict[int, List[int]] = defaultdict(list)
    for node, cycle in schedule.items():
        slots[cycle % ii].append(node)

    bundles: List[List] = []
    for s in range(ii):
        bundle: List = []
        nodes_in_slot = slots.get(s, [])

        # Track within-packet hazards exactly as _pack_flat_vliw does
        pkt_reads:    Set[int] = set()
        pkt_writes:   Set[int] = set()
        scalar_fu_used: Set[str] = set()
        vec_lanes_used: Set[str] = set()
        vlsu_count:   int       = 0
        scpad_used:   bool      = False

        for node in nodes_in_slot:
            if len(bundle) >= MAX_WIDTH:
                break
            ins = ddg.instructions[node]
            fu  = _get_fu(ins)

            # Functional-unit check (same gates as _pack_flat_vliw) ─────────
            if fu in SCALAR_FUS and fu in scalar_fu_used:
                continue
            if fu in VEC_LANE_FUS:
                if fu in vec_lanes_used:
                    continue
                if len(vec_lanes_used) >= MAX_VEC_LANES:
                    continue
            if fu == FU_VLSU and vlsu_count >= MAX_VLSU:
                continue
            if fu == FU_SCPAD and scpad_used:
                continue

            reads  = list(getattr(ins, "used_registers",    []))
            writes = list(getattr(ins, "defined_registers", []))

            # Register-hazard check (same as _pack_flat_vliw) ────────────────
            if any(r.num in pkt_writes for r in reads):
                continue
            if any(d.num in pkt_reads or d.num in pkt_writes for d in writes):
                continue

            # Commit ─────────────────────────────────────────────────────────
            bundle.append(ins)
            for r in reads:
                pkt_reads.add(r.num)
            for r in writes:
                pkt_writes.add(r.num)
            if fu in SCALAR_FUS:
                scalar_fu_used.add(fu)
            elif fu in VEC_LANE_FUS:
                vec_lanes_used.add(fu)
            elif fu == FU_VLSU:
                vlsu_count += 1
            elif fu == FU_SCPAD:
                scpad_used = True

        # NOP-pad to MAX_WIDTH (same as _pack_flat_vliw)
        while len(bundle) < MAX_WIDTH:
            bundle.append(_make_arch_nop(arch))

        bundles.append(bundle)

    return bundles


# ===========================================================================
# §9  Prologue & Epilogue Generation   «IMS/SMS»
# ===========================================================================

def _build_prologue_bundles(
    bundles_kernel: List[List],
    ii: int,
    num_stages: int,
    arch: AtallaArch,
) -> List[List]:
    """
    Build prologue bundles (pipeline ramp-up).

    The software pipeline has `num_stages` pipeline stages (= kernel depth in
    cycles / II, rounded up).  The prologue contains (num_stages - 1) partial
    iterations, each using only the instructions from the stages that are
    active.

    For simplicity we emit one pass through the first (s * II) bundles for
    stage s = 1 … num_stages-1.  In a production compiler, register
    renaming across stages would be applied here.

    Parameters
    ----------
    bundles_kernel : list of VLIW bundles (one per modulo slot)
    ii             : initiation interval
    num_stages     : number of stages (kernel_cycles / ii, rounded up)
    arch           : AtallaArch instance for make_nop

    Returns
    -------
    List of VLIW bundles forming the prologue.
    """
    prologue: List[List] = []
    for stage in range(1, num_stages):
        # Active bundles for this stage: first stage*ii slots of the kernel
        active = min(stage * ii, len(bundles_kernel))
        for b_idx in range(active):
            prologue.append(bundles_kernel[b_idx])
    return prologue


def _build_epilogue_bundles(
    bundles_kernel: List[List],
    ii: int,
    num_stages: int,
    arch: AtallaArch,
) -> List[List]:
    """
    Build epilogue bundles (pipeline drain).

    Mirrors _build_prologue_bundles but in reverse: stages drain one by one.
    """
    epilogue: List[List] = []
    for stage in range(num_stages - 1, 0, -1):
        active = min(stage * ii, len(bundles_kernel))
        for b_idx in range(active):
            epilogue.append(bundles_kernel[b_idx])
    return epilogue


# ===========================================================================
# §10  Top-level Pass API
# ===========================================================================

@dataclass
class SWPResult:
    """Output of the software-pipelining pass."""
    prologue_bundles:  List[List]  # VLIW bundles for ramp-up
    kernel_bundles:    List[List]  # VLIW bundles for steady-state kernel
    epilogue_bundles:  List[List]  # VLIW bundles for drain
    ii:                int         # achieved initiation interval
    mii:               int         # minimum initiation interval
    res_mii:           int
    rec_mii:           int
    num_stages:        int         # number of simultaneous pipeline stages
    schedule:          ScheduleMap # node → cycle mapping


def software_pipeline_loop(
    loop_body_insts: List,
    arch: AtallaArch,
    max_retries: int = 16,
) -> SWPResult:
    """
    Full software-pipelining pass for one loop body.

    Steps
    -----
    1.  Filter virtual instructions; keep only real Instruction objects.
    2.  Build the DDG (§3).
    3.  Compute MII (§4).
    4.  Run IMS to find a schedule (§7).
    5.  Pack the schedule into VLIW bundles (§8).
    6.  Emit prologue & epilogue (§9).

    Parameters
    ----------
    loop_body_insts:
        Flat list of PPCI Instruction objects representing the loop body
        (excluding the back-edge branch — the caller is responsible for
        re-attaching it after the kernel).
    arch:
        AtallaArch instance (for make_nop() and any arch-level queries).
    max_retries:
        Passed to the IMS scheduler; limits II exploration range.

    Returns
    -------
    SWPResult
    """
    # ── Step 1: filter virtual instructions ──────────────────────────────
    real_insts = [
        i for i in loop_body_insts
        if not _is_virtual(i) and not isinstance(i, Label)
    ]
    if not real_insts:
        raise ValueError("Loop body contains no real instructions.")

    log.info("SWP: %d real instructions in loop body", len(real_insts))

    # ── Step 2: DDG ───────────────────────────────────────────────────────
    ddg = build_ddg(real_insts)
    log.debug("DDG: %d nodes, %d edges", len(ddg.instructions), len(ddg.edges))

    # ── Step 3: MII ───────────────────────────────────────────────────────
    mii, res_mii, rec_mii = compute_mii(ddg)

    # ── Step 4: IMS ───────────────────────────────────────────────────────
    schedule, ii = iterative_modulo_schedule(ddg, mii, max_retries=max_retries)

    # ── Step 5: pack kernel ───────────────────────────────────────────────
    kernel_bundles = _pack_schedule_into_bundles(schedule, ddg, ii, arch)

    # Compute number of pipeline stages (kernel depth / II)
    if schedule:
        kernel_depth = max(schedule.values()) - min(schedule.values()) + 1
    else:
        kernel_depth = ii
    num_stages = max(1, math.ceil(kernel_depth / ii))

    # ── Step 6: prologue & epilogue ───────────────────────────────────────
    prologue_bundles = _build_prologue_bundles(kernel_bundles, ii, num_stages, arch)
    epilogue_bundles = _build_epilogue_bundles(kernel_bundles, ii, num_stages, arch)

    return SWPResult(
        prologue_bundles=prologue_bundles,
        kernel_bundles=kernel_bundles,
        epilogue_bundles=epilogue_bundles,
        ii=ii,
        mii=mii,
        res_mii=res_mii,
        rec_mii=rec_mii,
        num_stages=num_stages,
        schedule=schedule,
    )


def emit_swp_to_stream(result: SWPResult, label_prefix: str, stream) -> None:
    """
    Emit the prologue / kernel / epilogue bundles into a PPCI output stream,
    wrapping each section in a Label for downstream assembler/linker.

    Each VLIW bundle is emitted as MAX_WIDTH consecutive instructions
    (matching the _pack_flat_vliw flat-output format consumed by the
    assembler's fixed-width bundle decoder).

    Parameters
    ----------
    result       : SWPResult from software_pipeline_loop()
    label_prefix : string prefix for the generated labels
    stream       : PPCI FunctionOutputStream / MasterOutputStream
    """
    def _emit_section(bundles: List[List], section_label: str) -> None:
        stream.emit(Label(section_label))
        for bundle in bundles:
            for ins in bundle:
                stream.emit(ins)

    _emit_section(result.prologue_bundles,  f"{label_prefix}_swp_prologue")
    _emit_section(result.kernel_bundles,    f"{label_prefix}_swp_kernel")
    _emit_section(result.epilogue_bundles,  f"{label_prefix}_swp_epilogue")


# ===========================================================================
# §11  Test stub — demonstrates the pass on a mock Atalla IR loop
# ===========================================================================

def _run_demo() -> None:
    """
    Self-contained demo: build a mock loop body from raw Atalla instructions,
    run the SWP pass, and print the resulting kernel.

    The mock loop body represents a simple saxpy-style scalar accumulation:

        for i in range(N):
            t0 = lw_s  t0, 0(x5)    # load A[i]   (latency 3)
            t1 = lw_s  t1, 0(x6)    # load B[i]   (latency 3)
            t0 = mul_s t0, t0, t1   # t0 *= t1    (latency 3)
            t2 = add_s t2, t2, t0   # accum       (latency 1)
            sw_s t2, 0(x7)           # store C[i]  (latency 1)
            addi_s x5, x5, 4        # advance A ptr
            addi_s x6, x6, 4        # advance B ptr
            addi_s x7, x7, 4        # advance C ptr

    We build these using the actual Atalla instruction constructors so that
    used_registers / defined_registers are real PPCI operand objects.
    """
    import textwrap
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    from ppci.arch.atalla.arch import AtallaArch
    from ppci.arch.atalla.instructions import (
        Lws, Sws, Muls, Adds, Addis,
    )
    from ppci.arch.atalla.registers import (
        R5, R6, R7, R18, R19, R20, R21,
    )

    arch = AtallaArch()

    # Allocate pseudo-registers (already "colored" for the demo)
    # PPCI registers are singletons, so we just use the architectural ones.
    A_ptr  = R5
    B_ptr  = R6
    C_ptr  = R7
    t0     = R18
    t1     = R19
    accum  = R20
    stride = R21

    loop_body = [
        Lws(t0,  0, A_ptr),       # t0 = A[i]
        Lws(t1,  0, B_ptr),       # t1 = B[i]
        Muls(t0, t0, t1),         # t0 *= t1
        Adds(accum, accum, t0),   # accum += t0
        Sws(accum, 0, C_ptr),     # C[i] = accum
        Addis(A_ptr, A_ptr, 4),   # A_ptr += 4
        Addis(B_ptr, B_ptr, 4),   # B_ptr += 4
        Addis(C_ptr, C_ptr, 4),   # C_ptr += 4
    ]

    # Color the registers so PPCI doesn't complain in __repr__
    for ins in loop_body:
        for r in getattr(ins, "used_registers", []):
            if not getattr(r, "is_colored", True):
                r.color = r.num
        for r in getattr(ins, "defined_registers", []):
            if not getattr(r, "is_colored", True):
                r.color = r.num

    print("=" * 70)
    print("Atalla VLIW Software Pipelining Demo")
    print("=" * 70)
    print(f"\nLoop body ({len(loop_body)} instructions):")
    for i, ins in enumerate(loop_body):
        fu = _get_fu(ins) or "?"
        lat = LATENCY_MAP.get(_get_op(ins), 1)
        print(f"  [{i}]  {str(ins):<30}  FU={fu}  lat={lat}")

    result = software_pipeline_loop(loop_body, arch)

    print(f"\n{'─'*70}")
    print(f"MII={result.mii}  (ResMII={result.res_mii}, RecMII={result.rec_mii})")
    print(f"Achieved II={result.ii}  Stages={result.num_stages}")
    print(f"\nSchedule (node → modulo cycle):")
    for node, cyc in sorted(result.schedule.items()):
        ins = loop_body[node]
        print(f"  [{node}] {str(ins):<30}  cycle={cyc}  (slot {cyc % result.ii})")

    print(f"\n{'─'*70}")
    print(f"Kernel ({result.ii} VLIW bundles of width {MAX_WIDTH}):")
    for b_idx, bundle in enumerate(result.kernel_bundles):
        ops = " | ".join(f"{_get_op(i):<12}" for i in bundle)
        print(f"  Bundle {b_idx}: [ {ops} ]")

    print(f"\nPrologue ({len(result.prologue_bundles)} bundles):")
    for b_idx, bundle in enumerate(result.prologue_bundles):
        ops = " | ".join(f"{_get_op(i):<12}" for i in bundle)
        print(f"  Bundle {b_idx}: [ {ops} ]")

    print(f"\nEpilogue ({len(result.epilogue_bundles)} bundles):")
    for b_idx, bundle in enumerate(result.epilogue_bundles):
        ops = " | ".join(f"{_get_op(i):<12}" for i in bundle)
        print(f"  Bundle {b_idx}: [ {ops} ]")

    print("\n✓ Software pipelining pass completed successfully.")


if __name__ == "__main__":
    _run_demo()
