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



