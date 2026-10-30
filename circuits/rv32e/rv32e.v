// A single-cycle RV32E processor, written from "The RISC-V Instruction Set Manual,
// Volume I: Unprivileged ISA" (RV32E, Zifencei): the RV32I instructions with 16
// registers, x0 to x15. No M, no C, no floating point, no CSRs.
//
// Every clock cycle executes one instruction, unless a memory stalls it. The memories are
// read combinationally (imem_rdata and dmem_rdata follow the addresses in the same cycle)
// and written on the rising clock edge, with byte strobes. A memory that is busy (another
// master has its port) holds its ready low: the processor keeps its request on the port
// and does nothing in that cycle, it goes on in the first cycle the memories it needs
// are ready (imem_ready, and dmem_ready for a load or store). A store is written at the
// edge of the cycle with dmem_ready.
//
// The instructions are fetched from the instruction local memory (ILM), at address 0 with
// ILM_ADDR_WIDTH address bits. The data port reaches the whole address space: the memory
// system decodes it (in the test bench: the ILM, for read-only data, the data local
// memory and the console).
//
// Traps (there are no CSRs and no trap handler): the processor stops (halted = 1) at the
// instruction that traps, with the machine mode exception code in trap_cause:
//   0 instruction address misaligned, 1 instruction access fault (the pc is outside the
//   ILM), 2 illegal instruction, 3 breakpoint (EBREAK), 4 load address misaligned,
//   6 store address misaligned, 11 ECALL.
// Misaligned loads and stores trap (the spec allows that). An instruction that names
// x16 to x31 in a register it uses is illegal (RV32E reserves those encodings).
//
// The write-back port (wb_*) and retire show what every instruction did, so a test bench
// can compare the processor with a reference model.

module rv32 #(
    parameter RESET_PC = 32'h0000_0000,
    // The ILM's address bits (its size is 2^ILM_ADDR_WIDTH bytes), 3 to 32
    parameter ILM_ADDR_WIDTH = 16
) (
    input clk,
    input rst,

    // Instruction memory (ILM): the 32 bits at imem_addr (32-bit aligned)
    output [ILM_ADDR_WIDTH-1:0] imem_addr,
    input  [              31:0] imem_rdata,
    input                       imem_ready,

    // Data memory: dmem_rdata is the aligned word at dmem_addr
    output [31:0] dmem_addr,
    output        dmem_re,
    output [31:0] dmem_wdata,
    output [ 3:0] dmem_wstrb,
    input  [31:0] dmem_rdata,
    input         dmem_ready,

    // What the instruction of this cycle does, and its pc (all 32 bits)
    output [31:0] pc_out,
    output        retire,
    output        wb_we,
    output [ 3:0] wb_rd,
    output [31:0] wb_data,

    output        halted,
    output [ 3:0] trap_cause
);

    // ---------------------------------------------------------------------------------
    // State
    // ---------------------------------------------------------------------------------

    // The pc is 32-bit aligned (JALR clears bit 0, a jump to bit 1 traps): only bits 31:2
    // are stored, in one register, so its bits change together at the clock edge
    reg  [ 31:2] pc_word;
    wire [ 31:0] pc = {pc_word, 2'b00};
    // x1..x15, x0 is the 32 bits at the bottom, never written
    reg  [511:0] regfile;
    reg          halt;
    reg  [  3:0] cause;

    wire         active = !rst && !halt;

    assign imem_addr  = pc[ILM_ADDR_WIDTH-1:0];
    assign pc_out     = pc;
    assign halted     = halt;
    assign trap_cause = cause;

    // ---------------------------------------------------------------------------------
    // Decode
    // ---------------------------------------------------------------------------------

    localparam OP_LOAD = 7'b0000011, OP_MISC_MEM = 7'b0001111, OP_IMM = 7'b0010011;
    localparam OP_AUIPC = 7'b0010111, OP_STORE = 7'b0100011, OP_OP = 7'b0110011;
    localparam OP_LUI = 7'b0110111, OP_BRANCH = 7'b1100011, OP_JALR = 7'b1100111;
    localparam OP_JAL = 7'b1101111, OP_SYSTEM = 7'b1110011;

    wire [31:0] insn = imem_rdata;

    wire [ 6:0] opcode = insn[6:0];
    wire [ 4:0] rd_field = insn[11:7];
    wire [ 2:0] funct3 = insn[14:12];
    wire [ 4:0] rs1_field = insn[19:15];
    wire [ 4:0] rs2_field = insn[24:20];
    wire [ 6:0] funct7 = insn[31:25];

    // The registers, x0..x15 (the fifth bit of a field must be 0, see legal below)
    wire [ 3:0] rd = rd_field[3:0];
    wire [ 3:0] rs1 = rs1_field[3:0];
    wire [ 3:0] rs2 = rs2_field[3:0];

    wire [31:0] imm_i = {{20{insn[31]}}, insn[31:20]};
    wire [31:0] imm_s = {{20{insn[31]}}, insn[31:25], insn[11:7]};
    wire [31:0] imm_b = {{19{insn[31]}}, insn[31], insn[7], insn[30:25], insn[11:8], 1'b0};
    wire [31:0] imm_u = {insn[31:12], 12'd0};
    wire [31:0] imm_j = {{11{insn[31]}}, insn[31], insn[19:12], insn[20], insn[30:21], 1'b0};

    wire is_lui = opcode == OP_LUI;
    wire is_auipc = opcode == OP_AUIPC;
    wire is_jal = opcode == OP_JAL;
    wire is_jalr = opcode == OP_JALR && funct3 == 3'b000;
    wire is_branch = opcode == OP_BRANCH && funct3 != 3'b010 && funct3 != 3'b011;
    wire is_load = opcode == OP_LOAD && (funct3 == 3'b000 || funct3 == 3'b001 ||
                                         funct3 == 3'b010 || funct3 == 3'b100 ||
                                         funct3 == 3'b101);
    wire is_store = opcode == OP_STORE && (funct3 == 3'b000 || funct3 == 3'b001 ||
                                           funct3 == 3'b010);
    // The shifts have a 5-bit shift amount, the bits above it must be 0 (or 0100000 for SRAI)
    wire is_op_imm = opcode == OP_IMM && (
        (funct3 == 3'b001) ? funct7 == 7'b0000000 :
        (funct3 == 3'b101) ? (funct7 == 7'b0000000 || funct7 == 7'b0100000) : 1'b1);
    wire is_alu_op = opcode == OP_OP && (
        funct7 == 7'b0000000 ||
        (funct7 == 7'b0100000 && (funct3 == 3'b000 || funct3 == 3'b101)));
    // FENCE, and FENCE.I (Zifencei): there are no caches, so they do nothing
    wire is_fence = opcode == OP_MISC_MEM && (funct3 == 3'b000 || funct3 == 3'b001);
    wire is_ecall = insn == 32'h0000_0073;
    wire is_ebreak = insn == 32'h0010_0073;

    // The register fields of each format: rd (R, I, U, J), rs1 (R, I, S, B), rs2 (R, S, B)
    wire uses_rd = is_lui || is_auipc || is_jal || is_jalr || is_load || is_op_imm ||
                   is_alu_op;
    wire uses_rs1 = is_jalr || is_branch || is_load || is_store || is_op_imm || is_alu_op;
    wire uses_rs2 = is_branch || is_store || is_alu_op;
    // RV32E: x16..x31 are reserved
    wire high_register = (uses_rd && rd_field[4]) || (uses_rs1 && rs1_field[4]) ||
                         (uses_rs2 && rs2_field[4]);

    wire legal = (is_lui || is_auipc || is_jal || is_jalr || is_branch || is_load ||
                  is_store || is_op_imm || is_alu_op || is_fence || is_ecall || is_ebreak) &&
                 !high_register;

    // ---------------------------------------------------------------------------------
    // Registers
    // ---------------------------------------------------------------------------------

    wire [31:0] rs1_value = regfile[rs1*32+:32];
    wire [31:0] rs2_value = regfile[rs2*32+:32];

    // ---------------------------------------------------------------------------------
    // ALU (OP and OP-IMM)
    // ---------------------------------------------------------------------------------

    // Operand isolation: the ALU only sees the operands of OP and OP-IMM
    wire        is_alu = is_op_imm || is_alu_op;
    wire [31:0] alu_a = is_alu ? rs1_value : 32'd0;
    wire [31:0] alu_b = !is_alu ? 32'd0 : opcode == OP_OP ? rs2_value : imm_i;
    wire        alu_sub = opcode == OP_OP && funct7[5];
    // Operand isolation: the shifter only sees the operands of a shift, it is the largest
    // part of the ALU in gates
    wire        is_shift = is_alu && funct3[1:0] == 2'b01;
    wire [31:0] shift_a = is_shift ? alu_a : 32'd0;
    wire [ 4:0] shamt = is_shift ? alu_b[4:0] : 5'd0;

    // On its own: in a ?: with an unsigned operand, >>> would be a logical shift
    wire signed [31:0] sra_result = $signed(shift_a) >>> shamt;

    reg  [31:0] alu_result;
    always @(*) begin
        case (funct3)
            3'b000:  alu_result = alu_sub ? alu_a - alu_b : alu_a + alu_b;
            3'b001:  alu_result = shift_a << shamt;
            3'b010:  alu_result = {31'd0, $signed(alu_a) < $signed(alu_b)};
            3'b011:  alu_result = {31'd0, alu_a < alu_b};
            3'b100:  alu_result = alu_a ^ alu_b;
            3'b101:  alu_result = funct7[5] ? sra_result : shift_a >> shamt;
            3'b110:  alu_result = alu_a | alu_b;
            default: alu_result = alu_a & alu_b;
        endcase
    end

    // ---------------------------------------------------------------------------------
    // Branches and jumps
    // ---------------------------------------------------------------------------------

    // Operand isolation: the comparators only see the operands of a branch
    wire [31:0] cmp_a = is_branch ? rs1_value : 32'd0;
    wire [31:0] cmp_b = is_branch ? rs2_value : 32'd0;

    reg branch_taken;
    always @(*) begin
        case (funct3)
            3'b000:  branch_taken = cmp_a == cmp_b;  // BEQ
            3'b001:  branch_taken = cmp_a != cmp_b;  // BNE
            3'b100:  branch_taken = $signed(cmp_a) < $signed(cmp_b);  // BLT
            3'b101:  branch_taken = $signed(cmp_a) >= $signed(cmp_b);  // BGE
            3'b110:  branch_taken = cmp_a < cmp_b;  // BLTU
            default: branch_taken = cmp_a >= cmp_b;  // BGEU
        endcase
    end

    wire [31:0] pc_next_seq = pc + 32'd4;
    // Operand isolation: the target adders only see the operands of a jump or branch
    wire [31:0] jalr_target = ((is_jalr ? rs1_value : 32'd0) + (is_jalr ? imm_i : 32'd0)) &
                              ~32'd1;
    wire [31:0] jump_offset = is_jal ? imm_j : is_branch ? imm_b : 32'd0;
    wire [31:0] jump_target = is_jalr ? jalr_target : pc + jump_offset;
    wire        jump = is_jal || is_jalr || (is_branch && branch_taken);
    // Instructions are 32-bit aligned: a jump to a 16-bit boundary traps
    wire        jump_misaligned = jump && jump_target[1];
    wire [31:0] pc_next = jump ? jump_target : pc_next_seq;

    // ---------------------------------------------------------------------------------
    // Loads and stores
    // ---------------------------------------------------------------------------------

    // Operand isolation: the address adder only sees the operands of a load or store
    wire        is_mem = is_load || is_store;
    wire [31:0] mem_addr = (is_mem ? rs1_value : 32'd0) +
                           (is_store ? imm_s : is_load ? imm_i : 32'd0);
    wire [ 1:0] byte_offset = mem_addr[1:0];
    // LW/SW must be 32-bit aligned, LH/LHU/SH 16-bit aligned
    wire        mem_misaligned = funct3[1:0] == 2'b10 ? byte_offset != 2'b00 :
                                 funct3[1:0] == 2'b01 ? byte_offset[0] : 1'b0;
    wire        load_misaligned = is_load && mem_misaligned;
    wire        store_misaligned = is_store && mem_misaligned;

    wire [31:0] load_word = dmem_rdata >> {byte_offset, 3'b000};
    reg  [31:0] load_value;
    always @(*) begin
        case (funct3)
            3'b000:  load_value = {{24{load_word[7]}}, load_word[7:0]};  // LB
            3'b001:  load_value = {{16{load_word[15]}}, load_word[15:0]};  // LH
            3'b100:  load_value = {24'd0, load_word[7:0]};  // LBU
            3'b101:  load_value = {16'd0, load_word[15:0]};  // LHU
            default: load_value = load_word;  // LW
        endcase
    end

    reg [31:0] store_data;
    reg [ 3:0] store_strobe;
    always @(*) begin
        case (funct3)
            3'b000: begin  // SB
                store_data   = {4{rs2_value[7:0]}};
                store_strobe = 4'b0001 << byte_offset;
            end
            3'b001: begin  // SH
                store_data   = {2{rs2_value[15:0]}};
                store_strobe = 4'b0011 << byte_offset;
            end
            default: begin  // SW
                store_data   = rs2_value;
                store_strobe = 4'b1111;
            end
        endcase
    end

    // ---------------------------------------------------------------------------------
    // Traps, write-back and the next state
    // ---------------------------------------------------------------------------------

    // The pc is outside the ILM: nothing is fetched
    wire fetch_fault = ILM_ADDR_WIDTH < 32 && (pc >> ILM_ADDR_WIDTH) != 0;

    reg [3:0] trap_code;
    always @(*) begin
        if (fetch_fault) trap_code = 4'd1;
        else if (!legal) trap_code = 4'd2;
        else if (is_ecall) trap_code = 4'd11;
        else if (is_ebreak) trap_code = 4'd3;
        else if (jump_misaligned) trap_code = 4'd0;
        else if (load_misaligned) trap_code = 4'd4;
        else trap_code = 4'd6;
    end
    wire trap = fetch_fault || !legal || is_ecall || is_ebreak || jump_misaligned ||
                load_misaligned || store_misaligned;
    // The instruction is fetched, and its load or store goes to the data port
    wire fetched = active && !fetch_fault && imem_ready;
    wire mem_request = fetched && !trap && (is_load || is_store);
    // The cycle counts: what it needs is ready (a fetch fault needs nothing)
    wire ready = fetch_fault || (imem_ready && (!mem_request || dmem_ready));
    wire execute = active && ready && !trap;

    // Operand isolation: the data port only changes for a load or store, the other
    // instructions don't make the memories (or their glitches) switch
    assign dmem_addr  = mem_request ? mem_addr : 32'd0;
    assign dmem_re    = mem_request && is_load;
    assign dmem_wdata = (mem_request && is_store) ? store_data : 32'd0;
    assign dmem_wstrb = (mem_request && is_store) ? store_strobe : 4'b0000;

    reg [31:0] rd_value;
    always @(*) begin
        if (is_lui) rd_value = imm_u;
        else if (is_auipc) rd_value = pc + imm_u;
        else if (is_jal || is_jalr) rd_value = pc_next_seq;
        else if (is_load) rd_value = load_value;
        else rd_value = alu_result;
    end

    assign retire  = execute;
    assign wb_we   = execute && uses_rd && rd != 4'd0;
    assign wb_rd   = rd;
    assign wb_data = rd_value;

    always @(posedge clk) begin
        if (rst) begin
            pc_word <= RESET_PC[31:2];
            regfile <= 512'd0;
            halt    <= 1'b0;
            cause   <= 4'd0;
        end else if (active && ready) begin
            if (trap) begin
                halt  <= 1'b1;
                cause <= trap_code;
            end else begin
                pc_word <= pc_next[31:2];
                if (wb_we) regfile[rd*32+:32] <= rd_value;
            end
        end
    end

endmodule
