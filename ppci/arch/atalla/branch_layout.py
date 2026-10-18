"""Expand out-of-range conditionals without rescheduling existing packets."""

from ..generic_instructions import Label, PseudoInstruction
from .instructions import Beqs, Bnes, Blts, Bges, Bgts, Bles, Jal
from .registers import R0


_INVERSE = {Beqs: Bnes, Bnes: Beqs, Blts: Bges, Bges: Blts,
            Bgts: Bles, Bles: Bgts}


def relax_branches(code, make_nop, width=4):
    """Return final layout and added instruction count (offsets are 5-byte words).

    Conditional branches are solo packets. Replace a far conditional with its
    inverse over a solo JAL; inserting a packet cannot invalidate dependencies.
    Repeat because an insertion can push another branch out of range. This runs
    after fall-through jump cleanup, which must not remove the new JALs.
    """
    added = 0
    while True:
        labels, positions, pc = {}, {}, 0
        for index, ins in enumerate(code):
            if isinstance(ins, Label):
                labels[ins.name] = pc
            elif not isinstance(ins, PseudoInstruction):
                positions[index] = pc
                pc += 1
        far = {index for index, pos in positions.items()
               if type(code[index]) in _INVERSE
               and code[index].imm10 in labels
               and not -512 <= labels[code[index].imm10] - pos <= 511}
        if not far:
            return code, added
        result = []
        padding = {index + slot for index in far for slot in range(1, width)}
        for index, ins in enumerate(code):
            if index in padding:
                continue
            if index not in far:
                result.append(ins)
                continue
            name = "{}__branch_skip_{}".format(ins.imm10, added)
            while name in labels:
                name += "_"
            labels[name] = None
            skip = Label(name)
            result.append(_INVERSE[type(ins)](ins.rs1_rd, ins.rs2, name,
                                              jumps=[skip]))
            result.extend(make_nop() for _ in range(width - 1))
            result.append(Jal(R0, ins.imm10))
            result.extend(make_nop() for _ in range(width - 1))
            result.append(skip)
            added += 1
        code = result
