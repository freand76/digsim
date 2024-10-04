module alu(op,A,B,O);

   parameter ALU_OP_ADD = 0;
   parameter ALU_OP_SUB = 1;
   parameter ALU_OP_AND = 2;
   parameter ALU_OP_OR = 3;
   parameter ALU_OP_XOR = 4;
   parameter ALU_OP_LOGIC_LSHIFT = 5;
   parameter ALU_OP_LOGIC_RSHIFT = 6;
   parameter ALU_OP_ARITH_RSHIFT = 7;

   input [2:0] op;

   input [7:0] A;
   input [7:0] B;
   output reg [7:0] O;

   reg [7:0]   lshift;
   reg [7:0]   rshift;

   wire        aritmetic_shift_bit;
   assign aritmetic_shift_bit = A[7] && (op == ALU_OP_ARITH_RSHIFT);

   always @ (A, B)
     begin
        case(B)
          default : lshift <= 8'b00000000;
          1 : lshift <= {A[6:0],{1{1'b0}}};
          2 : lshift <= {A[5:0],{2{1'b0}}};
          3 : lshift <= {A[4:0],{3{1'b0}}};
          4 : lshift <= {A[3:0],{4{1'b0}}};
          5 : lshift <= {A[2:0],{5{1'b0}}};
          6 : lshift <= {A[1:0],{6{1'b0}}};
          7 : lshift <= {A[0:0],{7{1'b0}}};
        endcase // case (B)
     end

   always @ (A, B, aritmetic_shift_bit)
     begin
        case(B)
          default : rshift <= 8'b00000000;
          1 : rshift <= {{1{aritmetic_shift_bit}}, A[7:1]};
          2 : rshift <= {{2{aritmetic_shift_bit}}, A[7:2]};
          3 : rshift <= {{3{aritmetic_shift_bit}}, A[7:3]};
          4 : rshift <= {{4{aritmetic_shift_bit}}, A[7:4]};
          5 : rshift <= {{5{aritmetic_shift_bit}}, A[7:5]};
          6 : rshift <= {{6{aritmetic_shift_bit}}, A[7:6]};
          7 : rshift <= {{7{aritmetic_shift_bit}}, A[7:7]};
        endcase // case (B)
     end

   always @ (A, B, op, lshift, rshift)
     begin
       case(op)
         ALU_OP_ADD : O <= A + B;  // ADD A + B
         ALU_OP_SUB : O <= A - B;  // SUB A - B
         ALU_OP_AND : O <= A & B;  // AND A & B
         ALU_OP_OR : O <= A | B;  // OR  A | B
         ALU_OP_XOR : O <= A ^ B;  // XOR A ^ B
         ALU_OP_LOGIC_LSHIFT : O <= lshift; // Logic left Shift A with B bits
         ALU_OP_LOGIC_RSHIFT : O <= rshift; // Logic right shift A with B bits
         ALU_OP_ARITH_RSHIFT : O <= rshift; // Arithmetic right shift A with B bits
       endcase // case (op)
     end

endmodule // alu
