# COMPILER=atalla_cc
# ARCH=atalla
# PPCI=python3 -m ppci
# INPUT=instructtest.c


# atalla-compile-o2-no-link:
# # 	${PPCI} ${COMPILER} $(INPUT) -m ${ARCH} -S -O2
# 	${PPCI} ${COMPILER} $(INPUT) -m ${ARCH} -O2 --super-verbose -g
# # Because -g does stuff with debug and some item is not json serializable so just not doing -g
# # Wait that is fixed now!!!
# # 	${PPCI} ${COMPILER} $(INPUT) -m ${ARCH} -O2 --super-verbose
# # 	${PPCI} ${COMPILER} $(INPUT) -m ${ARCH} -O2 -g -c




# COMPILER=atalla_cc
# ARCH=atalla
# PPCI=python3 -m ppci
# INPUT=instructtest.c


# atalla-compile-o2-no-link:
# # 	${PPCI} ${COMPILER} $(INPUT) -m ${ARCH} -S -O2
# # 	${PPCI} ${COMPILER} $(INPUT) -m ${ARCH} -S -O2 --super-verbose -g
# 	python3 -m ppci atalla_cc instructtest2.c -m atalla -S -o instructtest2.s
# # Because -g does stuff with debug and some item is not json serializable so just not doing -g
# # Wait that is fixed now!!!
# # 	${PPCI} ${COMPILER} $(INPUT) -m ${ARCH} -O2 --super-verbose
# # 	${PPCI} ${COMPILER} $(INPUT) -m ${ARCH} -O2 -g -c


COMPILER=atalla_cc
ARCH=atalla
PPCI=python3 -m ppci

SRC1=instructtest2.c
SRC2=helper.c

OBJ1=instructtest2.o
OBJ2=helper.o

OBJ3=instructtest2.s
OBJ4=helper.s

ELF=output.elf


# -------------------------
# Single-file compile (old)
# -------------------------
atalla-compile-o2-no-link:
	${PPCI} ${COMPILER} $(SRC1) -m ${ARCH} -O2 --super-verbose


# -------------------------
# Compile BOTH files to .o
# -------------------------
atalla-compile-objects:
	${PPCI} ${COMPILER} $(SRC1) -m ${ARCH} -O2 -c -o $(OBJ1)
	${PPCI} ${COMPILER} $(SRC2) -m ${ARCH} -O2 -c -o $(OBJ2)

# ------------------------------------------------------------
# Generates Assembly Files for Comparison for the disassembler
# ------------------------------------------------------------
atalla-gen-asmfiles:
	${PPCI} ${COMPILER} $(SRC1) -m ${ARCH} -O2 -S -o $(OBJ3)
	${PPCI} ${COMPILER} $(SRC2) -m ${ARCH} -O2 -S -o $(OBJ4)

# -------------------------
# Link them (FORCES relocation)
# -------------------------
atalla-link:
	${PPCI} ld $(OBJ1) $(OBJ2) -o $(ELF)

# -------------------------
# One command: build + link
# -------------------------
atalla-test-reloc: atalla-compile-objects atalla-link
	@echo "Relocation test build complete."

# -------------------------
# Clean
# -------------------------
clean:
	rm -f *.o *.elf *.s f.txt disassembly.txt 

