COMPILER=atalla_cc
ARCH=atalla
PPCI=python3 -m ppci

# need to specify input file
atalla-o2-to-asm:
	${PPCI} ${COMPILER} $(INPUT) -m ${ARCH} -S -O2 -g

atalla-compile-o2-no-link:
	${PPCI} ${COMPILER} $(INPUT) -m ${ARCH} -c -O2 -g

help:
	$(PPCI) $(COMPILER) -h

