COMPILER=atalla_cc
ARCH=atalla
PPCI=python3 -m ppci


atalla-compile-o2-no-link:
	${PPCI} ${COMPILER} $(INPUT) -m ${ARCH} -S -O2

