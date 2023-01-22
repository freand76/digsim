ca65 code.s
ca65 vectors.s
ca65 interrupt.s
ld65 -vm -C sbc.cfg -o code.bin -m code.map code.o vectors.o interrupt.o
