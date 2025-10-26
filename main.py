from ppci.api import cc, link, ir_to_assembly
from ppci.lang.c import c_to_ir
from ppci.ir import Module
from ppci.binutils.objectfile import print_object
from ppci.utils.reporting import TextReportGenerator
import sys

def main():
<<<<<<< HEAD
    with open("instructtest.c", "r") as source:
        #cc(f, "atalla")
=======
    with open("sample.c", "r") as source:
        cc(source, "atalla")
        '''
>>>>>>> 722e94b5 (printing ir dag)
        with open("amps.s", "w") as f:
            reporter = TextReportGenerator(f)
            cc(source, "atalla", reporter=reporter)
        '''
if __name__ == "__main__":
    main()
