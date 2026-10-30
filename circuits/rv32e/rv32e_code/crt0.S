# The startup of the programs of rv32e_demo.circuit (the processor resets the registers
# to 0): set the stack pointer to the top of the RAM, copy .data from its load image in
# the ROM, clear .bss and call main. If main returns, the processor halts on EBREAK.
    .section .text.start
    .globl _start
_start:
    la      sp, __stack_top
    la      t0, __data_load
    la      t1, __data_start
    la      t2, __data_end
1:  bgeu    t1, t2, 2f
    lw      a0, 0(t0)
    sw      a0, 0(t1)
    addi    t0, t0, 4
    addi    t1, t1, 4
    j       1b
2:  la      t0, __bss_start
    la      t1, __bss_end
3:  bgeu    t0, t1, 4f
    sw      zero, 0(t0)
    addi    t0, t0, 4
    j       3b
4:  call    main
    ebreak
