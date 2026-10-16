"""SSA merge dependencies, instruction selection, and all-lane execution checks."""

import io

import pytest

from ppci import api, ir
from ppci.binutils.outstream import TextOutputStream
from ppci.codegen.burg import BurgSystem
from ppci.utils.tree import Tree


def test_pattern_matching_requires_all_operands():
    system = BurgSystem()
    system.add_terminal("ADD")
    # Terminal children stand in for registers; different arities cannot match.
    child = Tree("ADD")
    assert not system.tree_terminal_equal(Tree("ADD", child, child), Tree("ADD", child))


def test_merge_is_a_real_ssa_use_and_replaced_once():
    a, b, merge = [ir.Undefined(name, ir.vec) for name in ("a", "b", "merge")]
    mask = ir.Const(1, "mask", ir.i32)
    node = ir.VecOpMasked("+", a, b, mask, "result", ir.vec)
    assert node.merge is a
    node.replace_use(a, merge)
    assert node.arg1 is merge and node.merge is merge
    assert node not in a.used_by
    assert node in merge.used_by
    assert set(node.uses) == {merge, b, mask}


def test_masked_destination_read_tracks_register_replacement():
    from ppci.arch.atalla.vector_instructions import AddVv
    from ppci.arch.atalla.vector_registers import V1, V2, V3, V4
    from ppci.arch.atalla.mask_registers import M1

    ins = AddVv(V1, V2, V3, M1)
    ins.preserves_lanes = True
    assert V1 in ins.used_registers and V1 in ins.defined_registers
    ins.replace_register(V1, V4)  # The same replacement used during spilling.
    assert V1 not in ins.used_registers
    assert V4 in ins.used_registers and V4 in ins.defined_registers


@pytest.fixture
def execute(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    builder = pytest.importorskip("build_compiler")
    from functional_sim import run as simulator

    def run(source, level=2, vector_registers=None):
        arch = api.get_arch("atalla")
        if vector_registers is not None:
            for cls in arch.info.register_classes:
                if ir.vec in cls.ir_types:
                    monkeypatch.setattr(cls, "registers", cls.registers[:vector_registers])
        module = api.atalla_c_to_ir(io.StringIO(source), arch)
        api.optimize(module, level=level)
        output = io.StringIO()
        api.ir_to_stream(module, arch, TextOutputStream(f=output, printer=arch.asm_printer),
                         packetize=True)
        asm = output.getvalue()
        image, _ = builder.compile_prepacked_asm(asm)
        image_path = tmp_path / "test.in"
        image_path.write_text(image)
        mem = simulator.Memory(str(image_path))
        mem.write_data(0x1300, 0x40000000)  # FP32 2.0, matching scalar-register ABI.
        arrays = [np.arange(32, dtype=np.float32) / 8 + offset for offset in (1, 2, 20)]
        for base, values in zip((0x1000, 0x1100, 0x1200), arrays):
            for lane, value in enumerate(values):
                mem.write_bf16_le(base + 2 * lane, int(value.view(np.uint32)) >> 16)
        simulator.run(mem, simulator.ScalarRegisterFile(), simulator.mask_register_file(),
                      simulator.VectorRegisterFile(), simulator.Scratchpad(slots_per_bank=32),
                      simulator.Scratchpad(slots_per_bank=32),
                      simulator.ExecuteUnit(), 0, 4,
                      *[str(tmp_path / (name + ".out")) for name in
                        ("mem", "sregs", "vregs", "mregs", "sp0", "sp1", "perf")])

        def read(base=0x1800):
            bits = np.array([mem.read_bf16_le(base + 2 * i) << 16 for i in range(32)],
                            dtype=np.uint32)
            return bits.view(np.float32)
        return asm, read, arrays
    return run


LOADS = """
    vec a = vector_load(0x1000, 1, 31, 1);
    vec b = vector_load(0x1100, 1, 31, 1);
    vec merge = vector_load(0x1200, 1, 31, 1);
    float scalar = *(volatile float *)0x1300;
"""


@pytest.mark.parametrize("level", [0, 2])
@pytest.mark.parametrize("mask", [0, 0x55555555, -1])
@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("op, scalar", [(op, scalar) for op in ("+", "-", "*")
                                      for scalar in (False, True)])
def test_masked_lanes(execute, level, mask, explicit, op, scalar):
    import numpy as np
    from functional_sim.src.components.gemm import to_bf16

    rhs = "scalar" if scalar else "b"
    merge = ", merge" if explicit else ""
    source = f"""int main() {{ {LOADS}
        vec result = vec_op_masked("{op}", a, {rhs}, {mask}{merge});
        vector_store(result, 0x1800, 1, 31, 1);
        vector_store(a, 0x1900, 1, 31, 1);
        atalla_halt(); return 0;
    }}"""
    _, read, (a, b, preserved) = execute(source, level)
    expected = (preserved if explicit else a).copy()
    active = np.array([(mask >> i) & 1 for i in range(32)], dtype=bool)
    operation = {"+": np.add, "-": np.subtract, "*": np.multiply}[op]
    expected[active] = to_bf16(operation(a, 2.0 if scalar else b))[active]
    np.testing.assert_array_equal(read(), expected)
    np.testing.assert_array_equal(read(0x1900), a)  # Source must not be clobbered.


@pytest.mark.parametrize("level", [0, 2])
@pytest.mark.parametrize("op", ["RSUM", "RMIN", "RMAX"])
def test_reductions_broadcast_to_every_lane(execute, level, op):
    import numpy as np
    source = f"""int main() {{ {LOADS}
        vec result = vec_op_masked("{op}", a, 0.0, 5);
        vector_store(result, 0x1800, 1, 31, 1);
        atalla_halt(); return 0;
    }}"""
    asm, read, (a, _, _) = execute(source, level)
    expected = {"RSUM": np.sum, "RMIN": np.min, "RMAX": np.max}[op](a[[0, 2]])
    np.testing.assert_array_equal(read(), np.full(32, expected, dtype=np.float32))
    assert ", 64," in asm


@pytest.mark.parametrize("level", [0, 2])
def test_repeated_masked_updates_keep_previous_lanes(execute, level):
    import numpy as np
    source = f"""int main() {{ {LOADS}
        vec acc = merge;
        int i = 0;
        while (i < 4) {{
            acc = vec_op_masked("+", a, b, 1 << i, acc);
            i = i + 1;
        }}
        vector_store(acc, 0x1800, 1, 31, 1);
        vector_store(merge, 0x1900, 1, 31, 1);
        atalla_halt(); return 0;
    }}"""
    _, read, (a, b, preserved) = execute(source, level)
    expected = preserved.copy()
    expected[:4] = (a + b)[:4]
    np.testing.assert_array_equal(read(), expected)
    np.testing.assert_array_equal(read(0x1900), preserved)


@pytest.mark.parametrize("level", [0, 2])
@pytest.mark.parametrize("explicit", [False, True])
def test_masked_exp_preserves_inactive_lanes(execute, level, explicit):
    import numpy as np
    from functional_sim.src.components.gemm import to_bf16
    merge = ", merge" if explicit else ""
    source = f"""int main() {{ {LOADS}
        vec result = vec_op_masked("EXP", a, 0.0, 5{merge});
        vector_store(result, 0x1800, 1, 31, 1);
        atalla_halt(); return 0;
    }}"""
    _, read, (a, _, preserved) = execute(source, level)
    expected = (preserved if explicit else a).copy()
    expected[[0, 2]] = to_bf16(np.exp(a))[[0, 2]]
    np.testing.assert_array_equal(read(), expected)


@pytest.mark.parametrize("call", [
    'vec_op_masked("+", a, b, 1, 3)',
    'vec_op_masked("RSUM", a, 1.0, 1)',
    'vec_op_masked("RMAX", a, 0.0, 1, a)',
])
def test_invalid_merge_and_reduction_arguments_are_rejected(call):
    from ppci.common import CompilerError
    with pytest.raises(CompilerError):
        api.atalla_c_to_ir(io.StringIO(f"int main() {{ {LOADS} vec r = {call}; return 0; }}"),
                          api.get_arch("atalla"))


def test_optimizer_keeps_all_pooling_pairs():
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / "test_validation_kernels" / "maxpool_2x2.c"
    with path.open() as source:
        module = api.atalla_c_to_ir(source, api.get_arch("atalla"))
    api.optimize(module, level=2)
    reductions = [ins for fun in module.functions for block in fun for ins in block
                  if isinstance(ins, ir.VecOpMasked) and ins.op == "RMAX"]
    assert len(reductions) == 4


def test_masked_merge_survives_register_spills(execute):
    import numpy as np
    loads = "\n".join(f"vec a{i} = vector_load({0x1000 + i * 64}, 1, 31, 1);"
                      for i in range(12))
    stores = "\n".join(f"vector_store(a{i}, {0x2000 + i * 64}, 1, 31, 1);"
                       for i in range(12))
    source = f"""int main() {{ {loads}
        vec result = vec_op_masked("+", a0, a4, 5, a8);
        vector_store(result, 0x1800, 1, 31, 1);
        {stores}
        atalla_halt(); return 0;
    }}"""
    asm, read, (a, b, preserved) = execute(source, vector_registers=8)
    assert any("vreg_st" in line and line.rstrip().endswith(", 3")
               for line in asm.splitlines())
    expected = preserved.copy()
    expected[[0, 2]] = (a + b)[[0, 2]]
    np.testing.assert_array_equal(read(), expected)


@pytest.mark.parametrize("level", [0, 2])
@pytest.mark.parametrize("op", ["+", "-", "*"])
def test_unmasked_vector_binary_operations(execute, level, op):
    import numpy as np
    from functional_sim.src.components.gemm import to_bf16
    source = f"""int main() {{ {LOADS}
        vec result = a {op} b;
        vector_store(result, 0x1800, 1, 31, 1);
        atalla_halt(); return 0;
    }}"""
    _, read, (a, b, _) = execute(source, level)
    operation = {"+": np.add, "-": np.subtract, "*": np.multiply}[op]
    np.testing.assert_array_equal(read(), to_bf16(operation(a, b)))
