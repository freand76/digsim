# Build the LCD test program into lcd.bin, the contents of the ROM of rv32e_demo.circuit,
# with the RISC-V GCC (riscv64-unknown-elf-gcc). Also lcd.lst, its disassembly.
#
#   make          build lcd.bin and lcd.lst
#   make clean    remove what make builds

CROSS ?= riscv64-unknown-elf-
CC = $(CROSS)gcc
OBJCOPY = $(CROSS)objcopy
OBJDUMP = $(CROSS)objdump
PYTHON ?= python3

CFLAGS = -march=rv32e -mabi=ilp32e -Os -ffreestanding -nostdlib -nostartfiles -Wall
LDFLAGS = -T link.ld -Wl,--no-warn-rwx-segments

all: lcd.bin lcd.lst

lcd.elf: crt0.S lcd.c link.ld
	$(CC) $(CFLAGS) $(LDFLAGS) crt0.S lcd.c -lgcc -o $@

lcd.bin: lcd.elf
	$(OBJCOPY) -O binary $< $@

lcd.lst: lcd.elf
	$(OBJDUMP) -d -M numeric $< > $@

clean:
	rm -f lcd.elf lcd.bin lcd.lst

.PHONY: all clean
