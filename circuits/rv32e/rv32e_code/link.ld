/*
 * The memory map of rv32e_demo.circuit (see rv32e.circuit): code, read-only data and the
 * load image of .data in the ROM at address 0, the data and the stack in the RAM at
 * 0x10000000. Both have 2^14 words of 32 bits, 64 KiB. The registers of the peripherals
 * are symbols, which the programs declare as extern variables.
 */
OUTPUT_ARCH(riscv)
ENTRY(_start)

/* The timer, a 32-bit counter of the clock cycles (read only) */
TIMER = 0xe0000000;
/* The GPIO register, 32 bits (write only, also a byte or a halfword at a time) */
GPIO = 0xf0000000;

MEMORY
{
    ROM (rx) : ORIGIN = 0x00000000, LENGTH = 64K
    RAM (rw) : ORIGIN = 0x10000000, LENGTH = 64K
}
SECTIONS
{
    .text : { KEEP(*(.text.start)) *(.text .text.*) } > ROM
    .rodata : { *(.rodata .rodata.* .srodata .srodata.*) } > ROM
    /* In the RAM, copied from the ROM by crt0.S */
    .data : ALIGN(4) {
        __data_start = .;
        *(.data .data.* .sdata .sdata.*)
        . = ALIGN(4);
        __data_end = .;
    } > RAM AT > ROM
    __data_load = LOADADDR(.data);
    .bss (NOLOAD) : ALIGN(4) {
        __bss_start = .;
        *(.bss .bss.* .sbss .sbss.* COMMON)
        . = ALIGN(4);
        __bss_end = .;
    } > RAM
    __stack_top = ORIGIN(RAM) + LENGTH(RAM);
    /DISCARD/ : { *(.comment) *(.riscv.attributes) }
}
