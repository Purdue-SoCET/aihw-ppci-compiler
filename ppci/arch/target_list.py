"""Contains a list of instantiated targets."""

from functools import lru_cache

from .arm import ArmArch
from .avr import AvrArch
from .example import ExampleArch
from .m68k import M68kArch
from .mcs6500 import Mcs6500Arch
from .microblaze import MicroBlazeArch
from .mips import MipsArch
from .msp430 import Msp430Arch
from .or1k import Or1kArch
from .riscv import RiscvArch
from .stm8 import Stm8Arch
from .x86_64 import X86_64Arch
from .xtensa import XtensaArch
from .atalla import AtallaArch

target_classes = [
    AtallaArch,
    ArmArch,
    AvrArch,
    ExampleArch,
    M68kArch,
    Mcs6500Arch,
    MicroBlazeArch,
    MipsArch,
    Msp430Arch,
    Or1kArch,
    RiscvArch,
    Stm8Arch,
    X86_64Arch,
    XtensaArch,
]

print(target_classes[0])


target_class_map = {t.name: t for t in target_classes}
target_names = tuple(sorted(target_class_map.keys()))


@lru_cache(maxsize=30)
def create_arch(name, options=None):
    """Get a target architecture by its name. Possibly arch options can be
    given.
    """
    # Create the instance!
    target = target_class_map[name](options=options)
    return target
