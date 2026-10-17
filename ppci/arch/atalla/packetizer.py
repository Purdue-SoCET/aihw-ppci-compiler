"""Atalla dependency and functional-unit aware VLIW packetizer."""

from dataclasses import dataclass
from .latency import latency

FU_SCALAR_ALU = "scalar_alu"
FU_SCALAR_DIV = "scalar_div"
FU_BF16_ADD = "bf16_add"
FU_SCALAR_MUL = "scalar_mul"
FU_SCALAR_LDST = "scalar_ldst"
FU_VEC_ALU = "vec_alu"
FU_GSAU = "gsau"
FU_EXP = "exp"
FU_VLSU = "vlsu"
FU_SCPAD = "scpad"

SCALAR_FUS = {
    FU_SCALAR_ALU,
    FU_SCALAR_DIV,
    FU_BF16_ADD,
    FU_SCALAR_MUL,
    FU_SCALAR_LDST,
}
VEC_LANE_FUS = {FU_VEC_ALU, FU_GSAU, FU_EXP}
MAX_VEC_LANES = 2
MAX_VLSU = 4
MEM_TOUCH_FUS = {FU_SCALAR_LDST, FU_VLSU, FU_SCPAD, FU_GSAU}

OP_TO_FU = {
    "add.s": FU_SCALAR_ALU, "sub.s": FU_SCALAR_ALU,
    "or.s": FU_SCALAR_ALU, "and.s": FU_SCALAR_ALU,
    "xor.s": FU_SCALAR_ALU, "sll.s": FU_SCALAR_ALU,
    "srl.s": FU_SCALAR_ALU, "sra.s": FU_SCALAR_ALU,
    "lui.s": FU_SCALAR_ALU, "li.s": FU_SCALAR_ALU,
    "addi.s": FU_SCALAR_ALU, "subi.s": FU_SCALAR_ALU,
    "ori.s": FU_SCALAR_ALU, "andi.s": FU_SCALAR_ALU,
    "xori.s": FU_SCALAR_ALU, "slli.s": FU_SCALAR_ALU,
    "srli.s": FU_SCALAR_ALU, "srai.s": FU_SCALAR_ALU,
    "div.s": FU_SCALAR_DIV, "mod.s": FU_SCALAR_DIV,
    "divi.s": FU_SCALAR_DIV, "modi.s": FU_SCALAR_DIV,
    "bfts.s": FU_SCALAR_DIV, "rcp.bf": FU_SCALAR_DIV,
    "sqrt.bf": FU_SCALAR_DIV, "stbf.s": FU_SCALAR_DIV,
    "add.bf": FU_BF16_ADD, "sub.bf": FU_BF16_ADD,
    "mul.bf": FU_BF16_ADD,
    "mul.s": FU_SCALAR_MUL, "muli.s": FU_SCALAR_MUL,
    "lw.s": FU_SCALAR_LDST, "sw.s": FU_SCALAR_LDST,
    "lhw.s": FU_SCALAR_LDST, "shw.s": FU_SCALAR_LDST,
    "add.vv": FU_VEC_ALU, "sub.vv": FU_VEC_ALU,
    "mul.vv": FU_VEC_ALU, "rsum.vi": FU_VEC_ALU,
    "rmin.vi": FU_VEC_ALU, "rmax.vi": FU_VEC_ALU,
    "mgt.mvv": FU_VEC_ALU, "mlt.mvv": FU_VEC_ALU,
    "meq.mvv": FU_VEC_ALU, "mneq.mvv": FU_VEC_ALU,
    "mgt.mvs": FU_VEC_ALU, "mlt.mvs": FU_VEC_ALU,
    "meq.mvs": FU_VEC_ALU, "mneq.mvs": FU_VEC_ALU,
    "add.vs": FU_VEC_ALU, "sub.vs": FU_VEC_ALU,
    "mul.vs": FU_VEC_ALU,
    "gemm.vv": FU_GSAU, "lw.vi": FU_GSAU,
    "expi.vi": FU_EXP,
    "vreg.ld": FU_VLSU, "vreg.st": FU_VLSU,
    "scpad.ld": FU_SCPAD, "scpad.st": FU_SCPAD,
}


@dataclass
class Operation:
    mnemonic: str
    reads: set
    writes: set
    is_control: bool = False
    mem_key: tuple = None


def packetize(infos, labels, width=4):
    """Schedule real, non-NOP operations; remap labels to reordered block starts.

    Each result row contains source indices. Empty rows are latency stalls.
    RAW/WAW edges use producer latency, WAR edges retain all readers, and
    memory operations remain ordered conservatively. Priority is critical path
    length with source-order ties. Control operations occupy a packet alone.
    """
    n_instructions = len(infos)
    if not infos:
        return [], []

    starts = {0, *labels.values()}
    starts.update(
        idx + 1
        for idx, info in enumerate(infos)
        if info.is_control and idx + 1 < n_instructions
    )
    labels_at_source: dict[int, list[str]] = {}
    for name, source_idx in labels.items():
        labels_at_source.setdefault(source_idx, []).append(name)
    ordered_starts = sorted(starts)
    blocks = [
        list(
            range(
                start,
                ordered_starts[pos + 1]
                if pos + 1 < len(ordered_starts)
                else n_instructions,
            )
        )
        for pos, start in enumerate(ordered_starts)
        if start < n_instructions
    ]

    issue_cycle = [-1] * n_instructions
    packets: list[list[int]] = []
    current_cycle = 0

    for block in blocks:
        block_packet_start = len(packets)
        local_count = len(block)
        local_index = {global_i: local_i for local_i, global_i in enumerate(block)}
        block_latency = [latency.get(infos[idx].mnemonic.replace('.', '_'), 1) for idx in block]
        dependencies: list[list[tuple[int, int]]] = [[] for _ in block]
        last_def: dict[str, int] = {}
        last_read: dict[str, set[int]] = {}
        last_mem: int | None = None
        last_store_at: dict[tuple, int] = {}

        for local_i, global_i in enumerate(block):
            info = infos[global_i]
            fu = OP_TO_FU.get(info.mnemonic)

            for reg in info.reads:
                if reg in last_def:
                    producer = last_def[reg]
                    dependencies[local_i].append(
                        (producer, block_latency[producer])
                    )

            for reg in info.writes:
                if reg in last_def:
                    producer = last_def[reg]
                    dependencies[local_i].append(
                        (producer, block_latency[producer])
                    )
                if reg in last_read:
                    dependencies[local_i].extend(
                        (reader, 1) for reader in last_read[reg]
                    )

            for reg in info.writes:
                last_def[reg] = local_i
                last_read.pop(reg, None)
            for reg in info.reads:
                last_read.setdefault(reg, set()).add(local_i)

            is_mem = fu in MEM_TOUCH_FUS
            if is_mem:
                if last_mem is not None:
                    dependencies[local_i].append((last_mem, 1))
                scalar_mem_key = (
                    info.mem_key
                    if fu == FU_SCALAR_LDST
                    and (info.mnemonic.startswith("lw") or info.mnemonic.startswith("sw"))
                    else None
                )
                if scalar_mem_key is not None and scalar_mem_key in last_store_at:
                    producer = last_store_at[scalar_mem_key]
                    dependencies[local_i].append(
                        (producer, block_latency[producer])
                    )
                last_mem = local_i
                if info.mnemonic.startswith("sw") and scalar_mem_key is not None:
                    last_store_at[scalar_mem_key] = local_i

            if info.is_control:
                dependencies[local_i].extend((prior, 1) for prior in range(local_i))

        for local_i, edges in enumerate(dependencies):
            strongest: dict[int, int] = {}
            for predecessor, edge_latency in edges:
                strongest[predecessor] = max(
                    strongest.get(predecessor, -1), edge_latency
                )
            dependencies[local_i] = list(strongest.items())

        successors: list[list[tuple[int, int]]] = [[] for _ in block]
        for local_i, edges in enumerate(dependencies):
            for predecessor, edge_latency in edges:
                successors[predecessor].append((local_i, edge_latency))

        critical_path = [0] * local_count
        for local_i in range(local_count - 1, -1, -1):
            critical_path[local_i] = max(
                (
                    edge_latency + critical_path[successor]
                    for successor, edge_latency in successors[local_i]
                ),
                default=0,
            )

        indegree = [len(edges) for edges in dependencies]
        ready_cycle = [0] * local_count
        local_issue = [-1] * local_count
        scheduled = 0

        while scheduled < local_count:
            packet: list[int] = []
            packet_reads: set[str] = set()
            packet_writes: set[str] = set()
            scalar_fus: set[str] = set()
            vector_fus: set[str] = set()
            vlsu_count = 0
            sdma_used = False

            candidates = [
                local_i
                for local_i in range(local_count)
                if local_issue[local_i] == -1
                and indegree[local_i] == 0
                and ready_cycle[local_i] <= current_cycle
            ]
            candidates.sort(key=lambda local_i: (-critical_path[local_i], local_i))

            emitted_control = False
            for local_i in candidates:
                if len(packet) >= width or emitted_control:
                    break

                global_i = block[local_i]
                info = infos[global_i]
                if info.is_control:
                    if packet:
                        continue
                    packet.append(global_i)
                    local_issue[local_i] = current_cycle
                    issue_cycle[global_i] = current_cycle
                    emitted_control = True
                    break

                fu = OP_TO_FU.get(info.mnemonic)
                if fu in SCALAR_FUS and fu in scalar_fus:
                    continue
                if fu in VEC_LANE_FUS:
                    if fu in vector_fus or len(vector_fus) >= MAX_VEC_LANES:
                        continue
                if fu == FU_VLSU and vlsu_count >= MAX_VLSU:
                    continue
                if fu == FU_SCPAD and sdma_used:
                    continue
                if info.reads & packet_writes:
                    continue
                if info.writes & (packet_reads | packet_writes):
                    continue

                packet.append(global_i)
                local_issue[local_i] = current_cycle
                issue_cycle[global_i] = current_cycle
                packet_reads.update(info.reads)
                packet_writes.update(info.writes)
                if fu in SCALAR_FUS:
                    scalar_fus.add(fu)
                elif fu in VEC_LANE_FUS:
                    vector_fus.add(fu)
                elif fu == FU_VLSU:
                    vlsu_count += 1
                elif fu == FU_SCPAD:
                    sdma_used = True

            packets.append(packet)

            for global_i in packet:
                local_i = local_index[global_i]
                for successor, edge_latency in successors[local_i]:
                    ready_cycle[successor] = max(
                        ready_cycle[successor], current_cycle + edge_latency
                    )
                    indegree[successor] -= 1

            scheduled += len(packet)
            current_cycle += 1

        first_scheduled = next(
            (
                packets[pos][0]
                for pos in range(block_packet_start, len(packets))
                if packets[pos]
            ),
            None,
        )
        if first_scheduled is not None:
            for name in labels_at_source.get(block[0], []):
                labels[name] = first_scheduled

    return issue_cycle, packets


def check_metrics(metrics):
    """Verify encoder counts against the simulator's independently decoded image."""
    pairs = (
        (metrics["instructions_after_encoding"], metrics["packet_slots_filled"]),
        (metrics["packets_after_encoding"], metrics["packets_static_total"]),
        (metrics["nop_packets"],
         metrics["packets_static_total"] - metrics["packets_static_non_nop"]),
    )
    if any(expected != actual for expected, actual in pairs):
        raise ValueError("Packetization counts disagree with the decoded simulator image")
