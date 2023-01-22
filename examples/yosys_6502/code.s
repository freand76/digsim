; ---------------------------------------------------------------------------
; crt0.s
; ---------------------------------------------------------------------------
;
; Startup code for cc65 (Single Board Computer version)

.export   _init, _stop

.export   __STARTUP__ : absolute = 1        ; Mark as startup

; ---------------------------------------------------------------------------
; Place the startup code in a special segment

.segment  "STARTUP"

hello_data:   
	.byte	$48,$65,$6C,$6C,$6F,$20,$57,$6F,$72,$6C,$64,$0A,$00

hello_data_addr:
        .addr hello_data
; ---------------------------------------------------------------------------
; A little light 6502 housekeeping

_init:
        ldx     #$FF                 ; Initialize stack pointer to $01FF
        txs
        cld                          ; Clear decimal mode

; ---------------------------------------------------------------------------
; Set cc65 argument stack pointer

        ldx hello_data_addr
        ldy hello_data_addr+1
        stx $80        ; Store the low byte of the source address in ZP
        sty $81        ; Store the high byte of the source in ZP
        ldy #0         ; zero the index
loop:
        lda ($80),y    ; Get a byte from the source
        tax
        cpx #0         ; Run until 0
        beq done       ; Go round again if not
        sta $8000      ; Store it at the destination
        iny
        jmp loop

_stop:
done:   
        jmp done
        
