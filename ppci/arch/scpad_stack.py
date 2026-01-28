from stack import *


class ScpadStackLocation(StackLocation):
    def __init__(self, offset, size):
        super().__init__(offset, size)

    def __repr__(self):
        return f"ScpadStack[{self.size} bytes at {self.offset}]"
    
def generate_scpad_temps():
    n = 0
    while True:
        yield f"scpad_vreg{n}"
        n = n + 1

class ScpadFrame(Frame):
    def __init__(self, name, debug_db=None, fp_location=FramePointerLocation.TOP):
        self.name = name
        self.debug_db = debug_db  # Eventual debug information
        self.fp_location = fp_location
        self.instructions = []
        self.used_regs = set()
        self.is_leaf = False  # TODO: detect leaf functions
        self.out_calls = []
        self.temps = generate_scpad_temps()

        # Local stack:
        self.stacksize = 0
        self.alignment = 1

        # Literal pool:
        self.constants = []
        self.literal_number = 0

    def __repr__(self):
        return f"Scpad Frame {self.name}"
    
    def alloc(self, size, alignment):
        """Allocate space on the stack frame and return a stacklocation"""
        # determine alignment of whole stack frame as maximum alignment
        self.alignment = max(self.alignment, alignment)

        # Calling alloc with 0 indicates a problem somewhere.
        if size == 0:
            raise ValueError("Trying to allocate 0 bytes")

        # grow down or up?
        if self.fp_location == FramePointerLocation.TOP:
            # Create a negative offset from framepointer:
            self.stacksize += size
            misalign = self.stacksize % alignment
            if misalign:
                self.stacksize = self.stacksize - misalign + alignment
            # When frame pointer is located at top of the stackframe,
            # the offset is negative:
            offset = -self.stacksize
        else:
            misalign = self.stacksize % alignment
            if misalign:
                self.stacksize += size - misalign
            offset = self.stacksize
            self.stacksize += size
        location = ScpadStackLocation(offset, size)
        return location