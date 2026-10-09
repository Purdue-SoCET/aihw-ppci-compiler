"""Loop unrolling by a factor of four.

This is a prototype pass. It only handles simple counting loops, which
after mem2reg look like this:

    preheader:
      jmp header
    header:
      i = phi preheader: start, iterator: i_next
      cjmp i < bound ? body : exit
    body:
      ...
      jmp iterator
    iterator:
      i_next = i + 1
      jmp header

The body and the iterator are copied three times onto the end of the
iterator, so that each trip around the loop does four iterations. Each
copy reads the values produced by the copy before it. The header phis are
then pointed at the values produced by the last copy.

Only loops with a constant start, a constant bound, a step of one and a
trip count that is a multiple of four are unrolled. All other loops are
left alone.
"""

from collections import namedtuple

from .. import ir
from ..graph.domtree import CfgInfo
from ..irutils.verify import Verifier
from .constantfolding import correct
from .transform import FunctionPass

SimpleLoop = namedtuple(
    "SimpleLoop",
    [
        "header",
        "body",
        "iterator",
        "exit",
        "preheader",
        "counter",
        "start",
        "bound",
        "increment",
    ],
)

# Instructions that can be copied. Vector load and store are included
# because the copy is appended after the original, so memory order is kept.
# Scalar load and store stay out.
CLONEABLE_TYPES = (
    ir.Const,
    ir.Binop,
    ir.Unop,
    ir.Cast,
    ir.VectorLoad,
    ir.VectorStore,
)


class LoopUnrollPass(FunctionPass):
    """Unroll simple counting loops by a factor of four."""

    factor = 4

    def on_function(self, function):
        cfg_info = CfgInfo(function)

        loops_by_header = {}
        for loop in cfg_info.cfg.calculate_loops():
            loops_by_header.setdefault(loop.header, []).append(loop)

        count = 0
        for loops in loops_by_header.values():
            simple_loop = find_simple_loop(loops, cfg_info, self.factor)
            if simple_loop is None:
                continue
            unroll_by_factor(simple_loop, self.factor)
            Verifier().verify_function(function)
            count += 1

        if count > 0:
            self.logger.debug(
                "Unrolled %i loops in %s by %i",
                count,
                function.name,
                self.factor,
            )


def find_simple_loop(loops, cfg_info, factor):
    """Check if the loops with a shared header form a simple counting loop.

    Returns a SimpleLoop when the loop can be unrolled, or None otherwise.
    """
    # Exactly one back edge. Two extra blocks means a body and an iterator.
    # One extra block means CleanPass already glued those into one latch.
    if len(loops) != 1:
        return None
    loop = loops[0]
    if len(loop.rest) not in (1, 2):
        return None
    if not cfg_info.has_block(loop.header):
        return None
    if not all(cfg_info.has_block(node) for node in loop.rest):
        return None

    header = cfg_info.get_block(loop.header)
    loop_blocks = {header} | {cfg_info.get_block(n) for n in loop.rest}

    # One way into the loop from outside:
    outside = [b for b in header.predecessors if b not in loop_blocks]
    if len(outside) != 1:
        return None
    preheader = outside[0]

    # The header decides between the body and the exit:
    cjump = header.last_instruction
    if not isinstance(cjump, ir.CJump):
        return None
    body = cjump.lab_yes
    exit_block = cjump.lab_no
    if body is header or body not in loop_blocks:
        return None
    if exit_block in loop_blocks:
        return None

    # Either the body jumps to a separate iterator, or the yes target is
    # already the latch and it jumps straight back to the header.
    if len(loop.rest) == 1:
        iterator = body
    else:
        iterator = (loop_blocks - {header, body}).pop()
        body_jump = body.last_instruction
        if not (
            isinstance(body_jump, ir.Jump) and body_jump.target is iterator
        ):
            return None
    iterator_jump = iterator.last_instruction
    if not (
        isinstance(iterator_jump, ir.Jump) and iterator_jump.target is header
    ):
        return None

    # The condition is "counter < constant bound":
    if cjump.cond != "<":
        return None
    counter = cjump.a
    bound = cjump.b
    if not (isinstance(counter, ir.Phi) and counter.block is header):
        return None
    if not isinstance(bound, ir.Const):
        return None
    if not isinstance(counter.ty, ir.IntegerTyp):
        return None

    # Every header phi gets one value from outside and one from the
    # iterator:
    for phi in header.phis:
        if set(phi.inputs) != {preheader, iterator}:
            return None

    # The counter starts at a constant and steps by one:
    start = counter.get_value(preheader)
    if not isinstance(start, ir.Const):
        return None
    increment = counter.get_value(iterator)
    if not is_increment_by_one(increment, counter):
        return None
    if increment.block not in (body, iterator):
        return None

    # The trip count is a multiple of the unroll factor:
    trip_count = correct(bound.value, counter.ty) - correct(
        start.value, counter.ty
    )
    if trip_count < factor or trip_count % factor != 0:
        return None

    # The body and iterator can be copied safely. When they are the same
    # latch, check that block once.
    seen = []
    for block in (body, iterator):
        if block in seen:
            continue
        seen.append(block)
        for instruction in block.instructions[:-1]:
            if type(instruction) not in CLONEABLE_TYPES:
                return None

    # The header only holds phis, constants and the conditional jump:
    for instruction in header.instructions[:-1]:
        if not isinstance(instruction, (ir.Phi, ir.Const)):
            return None

    return SimpleLoop(
        header=header,
        body=body,
        iterator=iterator,
        exit=exit_block,
        preheader=preheader,
        counter=counter,
        start=start,
        bound=bound,
        increment=increment,
    )


def is_increment_by_one(value, counter):
    """Test if value is 'counter + 1' or '1 + counter'"""
    if type(value) is not ir.Binop or value.operation != "+":
        return False
    if value.a is counter:
        step = value.b
    elif value.b is counter:
        step = value.a
    else:
        return False
    return isinstance(step, ir.Const) and step.value == 1


def clone_instruction(instruction, value_map, suffix):
    """Create a copy of instruction with its operands looked up in
    value_map. Operands not in the map are shared with the original."""

    def lookup(value):
        return value_map.get(value, value)

    # A store is not a value, so it has no name or type to copy.
    if type(instruction) is ir.VectorStore:
        return ir.VectorStore(
            lookup(instruction.vec),
            lookup(instruction.addr),
            lookup(instruction.arg2),
            lookup(instruction.arg3),
            lookup(instruction.arg4),
        )

    name = f"{instruction.name}{suffix}"
    ty = instruction.ty
    if type(instruction) is ir.Const:
        return ir.Const(instruction.value, name, ty)
    elif type(instruction) is ir.Binop:
        return ir.Binop(
            lookup(instruction.a),
            instruction.operation,
            lookup(instruction.b),
            name,
            ty,
        )
    elif type(instruction) is ir.Unop:
        return ir.Unop(instruction.operation, lookup(instruction.a), name, ty)
    elif type(instruction) is ir.Cast:
        return ir.Cast(lookup(instruction.src), name, ty)
    elif type(instruction) is ir.VectorLoad:
        return ir.VectorLoad(
            lookup(instruction.addr),
            lookup(instruction.arg2),
            lookup(instruction.arg3),
            lookup(instruction.arg4),
            name,
            ty,
        )
    else:  # pragma: no cover
        raise NotImplementedError(str(instruction))


def _is_vector_work(instruction):
    """The add or store that consumes a loaded vector."""
    if type(instruction) is ir.VectorStore:
        return True
    return type(instruction) is ir.Binop and isinstance(instruction.ty, ir.VectorTyp)


def _early_load_copies(pairs):
    """The copied vector loads, plus any copied values those loads read."""
    loads = [copy for _, copy in pairs if type(copy) is ir.VectorLoad]
    if not loads:
        return [], pairs

    needed = set(loads)
    stack = []
    for load in loads:
        stack.extend(load.uses)
    seen = set()
    while stack:
        value = stack.pop()
        if value in seen:
            continue
        seen.add(value)
        needed.add(value)
        if isinstance(value, ir.Instruction):
            stack.extend(value.uses)

    early = [(orig, copy) for orig, copy in pairs if copy in needed]
    late = [(orig, copy) for orig, copy in pairs if copy not in needed]
    return early, late


def _hoist_before(block, needed, insert_before):
    """Move latch instructions the second loads read to before insert_before.

    Relative order is kept, so an address add stays after the constant it uses.
    """
    cutoff = insert_before.position
    movers = [
        ins
        for ins in block.instructions
        if ins in needed and ins.position >= cutoff
    ]
    for ins in movers:
        block.remove_instruction(ins)
    for ins in movers:
        block.insert_instruction(ins, before_instruction=insert_before)


def unroll_by_factor(loop, factor):
    """Copy the body and iterator factor-1 times onto the iterator.

    Copy n reads the values produced by copy n-1. When the latch has vector
    loads, every copied load is placed before the first vector add or store,
    so the loads are all in flight during the one load wait. The first loaded
    vectors stay live, so they cannot share vector registers with the copies.
    """
    header = loop.header
    iterator = loop.iterator

    # At the start of the next copy, each header phi holds the value coming
    # in over the back edge. After each copy that value is the copy's result.
    value_map = {phi: phi.get_value(iterator) for phi in header.phis}

    iterator_jump = iterator.last_instruction
    iterator_jump.remove_from_block()

    if loop.body is iterator:
        originals = list(iterator.instructions)
    else:
        originals = loop.body.instructions[:-1] + list(iterator.instructions)

    pairs = []
    for copy_index in range(1, factor):
        for instruction in originals:
            copy = clone_instruction(
                instruction, value_map, f"_{copy_index + 1}"
            )
            pairs.append((instruction, copy))
            value_map[instruction] = copy
        for phi in header.phis:
            incoming = phi.get_value(iterator)
            value_map[phi] = value_map.get(incoming, incoming)

    early, late = _early_load_copies(pairs)
    vector_work = [
        ins for ins in iterator.instructions if _is_vector_work(ins)
    ]
    if early and loop.body is iterator and vector_work:
        insert_before = vector_work[0]
        needed = set()
        stack = []
        for _, copy in early:
            stack.extend(copy.uses)
        while stack:
            value = stack.pop()
            if value in needed or not isinstance(value, ir.Instruction):
                continue
            if value.block is not iterator:
                continue
            needed.add(value)
            stack.extend(value.uses)
        _hoist_before(iterator, needed, insert_before)
        for _, copy in early:
            iterator.insert_instruction(copy, before_instruction=insert_before)
        for _, copy in late:
            iterator.add_instruction(copy)
    else:
        for _, copy in pairs:
            iterator.add_instruction(copy)

    iterator.add_instruction(iterator_jump)

    for phi in header.phis:
        old_value = phi.get_value(iterator)
        phi.set_incoming(iterator, value_map.get(old_value, old_value))
