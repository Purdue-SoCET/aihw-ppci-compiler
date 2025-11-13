import re
from collections import defaultdict
from instruction_latency import latency

def _int_or_none(tok):
    try:
        return int(tok, 0)
    except:
        return None

def parse_instruction(line):
    line = line.strip()
    if not line:
        return None
    line = re.split(r"[;#]", line, maxsplit=1)[0].strip()
    if not line:
        return None
    if line.endswith(":") or line.startswith("."):
        return None

    tokens = re.split(r"[,\s()]+", line)
    op = tokens[0]

    control = {"j", "jal", "jalr"}
    if op.startswith("b"):
        control.add(op)

    regs = []
    for t in tokens[1:]:
        if re.fullmatch(r"x\d+", t):
            regs.append(t)

    mem_key = None
    if op in control:
        dsts = []
        srcs = regs
    elif op.startswith("sw") or op.startswith("sd"):
        dsts = []
        srcs = regs
        if len(tokens) >= 4:
            base = tokens[3]
            imm = _int_or_none(tokens[2])
            if re.fullmatch(r"x\d+", base) and imm is not None:
                mem_key = (base, imm)
            else:
                mem_key = ("unknown", None)
    elif op.startswith("lw"):
        dsts = regs[:1]
        srcs = regs[1:2]
        if len(tokens) >= 4:
            base = tokens[3]
            imm = _int_or_none(tokens[2])
            if re.fullmatch(r"x\d+", base) and imm is not None:
                mem_key = (base, imm)
            else:
                mem_key = ("unknown", None)
    else:
        dsts = regs[:1]
        srcs = regs[1:]

    return op, dsts, srcs, mem_key


def build_dependency_graph(instructions, latency_map, single_lsu=True):
    last_write = {}
    last_mem_cycle = -1
    last_store_at = {}
    ready_time = [0 for _ in range(len(instructions))]

    for i in range(len(instructions)):
        op, dsts, srcs, mem_key = instructions[i]
        start = 0
        for s in srcs:
            if s in last_write:
                if last_write[s] > start:
                    start = last_write[s]

        is_load = op.startswith("lw")
        is_store = op.startswith("sw") or op.startswith("sd")
        is_mem = is_load or is_store

        # At most one memory op can issue per cycle. Force start to be strictly after the last memory issue if needed.
        if single_lsu and is_mem:
            if last_mem_cycle + 1 > start:
                start = last_mem_cycle + 1

        # If you know the (base, imm) and there was a prior store to that key, make the current memory op wait until that store’s completion.
        if is_mem and mem_key is not None:
            if is_load:
                if mem_key in last_store_at and last_store_at[mem_key] > start:
                    start = last_store_at[mem_key]
            else:
                if mem_key in last_store_at and last_store_at[mem_key] > start:
                    start = last_store_at[mem_key]

        ready_time[i] = start

        # Destination availability times
        latency = latency_map.get(op, 1)
        for d in dsts:
            last_write[d] = start + latency

        # Update memory scoreboards
        if is_mem:
            last_mem_cycle = start
            if is_store and mem_key is not None:
                last_store_at[mem_key] = start + latency

    return ready_time


def greedy_pack(instructions, ready_time, max_width=4):
    packets = [] # list of lists of instruction indices
    scheduled = [False for _ in range(len(instructions))] # marks whether instruction i has been placed alread
    current_cycle = 0 # packet time index

    def is_control(op):
        if op in {"j", "jal", "jalr"}:
            return True
        if op.startswith("b"):
            return True
        return False

    while not all(scheduled):
        packet = []
        packet_reads = set()
        packet_writes = set()
        mem_in_packet = False
        count = 0

        for i in range(len(instructions)):
            op, dsts, srcs, mem_key = instructions[i]
            # Skip if already scheduled
            if scheduled[i]:
                continue
            # Skip if not ready at this cycle
            if ready_time[i] > current_cycle:
                continue

            if is_control(op):
                if count == 0:
                    packet.append(i)
                    scheduled[i] = True
                break

            # Do not add another memory op if one is already in the packet
            is_mem = op.startswith("lw") or op.startswith("sw") or op.startswith("sd")
            if mem_in_packet and is_mem:
                continue

            # RAW hazards
            hazard = False
            for s in srcs:
                if s in packet_writes:
                    hazard = True
                    break
            # WAW and WAR hazards
            for d in dsts:
                if d in packet_writes or d in packet_reads:
                    hazard = True
                    break
            if hazard:
                continue

            # Update reads and writes sets, mark memory presence, mark scheduled, increase count, and stop if you reached the packet width
            packet.append(i)
            for s in srcs:
                packet_reads.add(s)
            for d in dsts:
                packet_writes.add(d)
            if is_mem:
                mem_in_packet = True
            scheduled[i] = True
            count += 1
            if count == max_width:
                break

        # If nothing was schedulable at this cycle, advance time and try again
        if len(packet) == 0:
            packets.append([])
            current_cycle += 1
            continue

        # Commit the packet and move to next cycle
        packets.append(packet)
        current_cycle += 1

    return packets


def packetize_basic_block(asm_str, latency_map):
    entries = [] # (original_line, parsed_tuple) pairs
    lines = asm_str.strip().splitlines()

    # Skip blanks and stuff the parser ignores
    for l in lines:
        s = l.strip()
        if not s:
            continue
        parsed = parse_instruction(s)
        if parsed:
            entries.append((s, parsed))

    if len(entries) == 0:
        return []

    parsed_insts = []
    for _, p in entries:
        parsed_insts.append(p)

    ready_time = build_dependency_graph(parsed_insts, latency_map, True)
    packet_indices = greedy_pack(parsed_insts, ready_time, 4)

    packets = []
    for pkt in packet_indices:
        instrs = []
        for i in pkt:
            instrs.append(entries[i][0])
        while len(instrs) < 4:
            instrs.append("nop")
        packets.append(instrs)
    return packets


if __name__ == "__main__":
    asm_block = """
addi x1, x0, 5
addi x2, x1, 3
mul  x3, x1, x2
sw   x1, 0(x2)
lw   x4, 0(x2)
sub  x2, x4, x5
sub  x4, x3, x2
add  x5, x4, x1
or   x6, x1, x2
L1:
add  x11, x12, x13
add  x12, x13, x14
add  x14, x15, x16
"""

    packets = packetize_basic_block(asm_block, latency)
    for i in range(len(packets)):
        print("Packet " + str(i) + ":")
        for ins in packets[i]:
            print("  ", ins)
