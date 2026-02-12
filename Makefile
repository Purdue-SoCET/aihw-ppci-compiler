COMPILER=atalla_cc
ARCH=atalla
PPCI=python3 -m ppci
INPUT=instructtest.c

# need to specify input file
atalla-o2-to-asm:
	${PPCI} ${COMPILER} $(INPUT) -m ${ARCH} -S -O2 -g

atalla-compile-o2-no-link:
	${PPCI} ${COMPILER} $(INPUT) -m ${ARCH} -c -O2 -g

help:
	$(PPCI) $(COMPILER) -h
# 	${PPCI} ${COMPILER} $(INPUT) -m ${ARCH} -S -O2
	${PPCI} ${COMPILER} $(INPUT) -m ${ARCH} -O2 --super-verbose -g
# Because -g does stuff with debug and some item is not json serializable so just not doing -g
# Wait that is fixed now!!!
# 	${PPCI} ${COMPILER} $(INPUT) -m ${ARCH} -O2 --super-verbose
# 	${PPCI} ${COMPILER} $(INPUT) -m ${ARCH} -O2 -g -c




# COMPILER=atalla_cc
# ARCH=atalla
# PPCI=python3 -m ppci

# SRC1=instructtest2.c
# SRC2=helper.c

# OBJ1=instructtest2.o
# OBJ2=helper.o

# ELF=output.elf


# # -------------------------
# # Single-file compile (old)
# # -------------------------
# atalla-compile-o2-no-link:
# 	${PPCI} ${COMPILER} $(SRC1) -m ${ARCH} -O2 --super-verbose


# # -------------------------
# # Compile BOTH files to .o
# # -------------------------
# atalla-compile-objects:
# 	${PPCI} ${COMPILER} $(SRC1) -m ${ARCH} -O2 -c -o $(OBJ1)
# 	${PPCI} ${COMPILER} $(SRC2) -m ${ARCH} -O2 -c -o $(OBJ2)


# # -------------------------
# # Link them (FORCES relocation)
# # -------------------------
# atalla-link:
# 	${PPCI} ld $(OBJ1) $(OBJ2) -o $(ELF)


# # -------------------------
# # One command: build + link
# # -------------------------
# atalla-test-reloc: atalla-compile-objects atalla-link
# 	@echo "Relocation test build complete."


# # -------------------------
# # Clean
# # -------------------------
# clean:
# 	rm -f *.o *.elf

