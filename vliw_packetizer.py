import re
from collections import defaultdict
from instruction_latency import latency

def _int_or_none(tok):
    try:
        return int(tok, 0)
    except:
        return None

def is_control_op(op):
    if op in {"j", "jal", "jalr"}:
        return True
    if op.startswith("b"):
        return True
    return False

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

        if single_lsu and is_mem:
            if last_mem_cycle + 1 > start:
                start = last_mem_cycle + 1

        if is_mem and mem_key is not None:
            if is_load:
                if mem_key in last_store_at and last_store_at[mem_key] > start:
                    start = last_store_at[mem_key]
            else:
                if mem_key in last_store_at and last_store_at[mem_key] > start:
                    start = last_store_at[mem_key]

        ready_time[i] = start

        latency = latency_map.get(op, 1)
        for d in dsts:
            last_write[d] = start + latency

        if is_mem:
            last_mem_cycle = start
            if is_store and mem_key is not None:
                last_store_at[mem_key] = start + latency

    return ready_time


def greedy_pack(instructions, ready_time, max_width=4):
    packets = []
    scheduled = [False for _ in range(len(instructions))]
    current_cycle = 0

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
            if scheduled[i]:
                continue
            if ready_time[i] > current_cycle:
                continue

            if is_control(op):
                if count == 0:
                    packet.append(i)
                    scheduled[i] = True
                break

            is_mem = op.startswith("lw") or op.startswith("sw") or op.startswith("sd")
            if mem_in_packet and is_mem:
                continue

            hazard = False
            for s in srcs:
                if s in packet_writes:
                    hazard = True
                    break
            for d in dsts:
                if d in packet_writes or d in packet_reads:
                    hazard = True
                    break
            if hazard:
                continue

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

        if len(packet) == 0:
            packets.append([])
            current_cycle += 1
            continue

        packets.append(packet)
        current_cycle += 1

    return packets


def vliw_packetizer(asm_str, latency_map):
    lines = asm_str.strip().splitlines()

    blocks = []
    current_entries = []  # (original_line, parsed_tuple) per basic block

    for l in lines:
        s = l.strip()
        if not s:
            continue

        # Start a new basic block at labels
        if s.endswith(":"):
            if current_entries:
                blocks.append(current_entries)
                current_entries = []
            continue

        parsed = parse_instruction(s)
        if not parsed:
            continue

        op, dsts, srcs, mem_key = parsed
        current_entries.append((s, parsed))

        # End the current basic block after a control flow instruction
        if is_control_op(op):
            blocks.append(current_entries)
            current_entries = []

    if current_entries:
        blocks.append(current_entries)

    if len(blocks) == 0:
        return []

    all_block_packets = []

    for entries in blocks:
        parsed_insts = [p for _, p in entries]
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

        all_block_packets.append(packets)

    return all_block_packets


if __name__ == "__main__":
    asm_block = """
start:
addi x1, x0, 1
addi x2, x0, 2
beq  x1, x2, L_taken
addi x3, x0, 3
addi x4, x0, 4
j    L_end

L_taken:
addi x5, x0, 5
addi x6, x0, 6

L_end:
addi x7, x0, 7
"""

    blocks = vliw_packetizer(asm_block, latency)
    for b, packets in enumerate(blocks):
        print("Basic block", b)
        for i, pkt in enumerate(packets):
            print("  Packet " + str(i) + ":")
            for ins in pkt:
                print("    ", ins)
