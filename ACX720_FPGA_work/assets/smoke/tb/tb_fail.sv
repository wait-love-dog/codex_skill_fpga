`timescale 1ns/1ps
module tb_fail;
    initial begin #100; $fatal(1,"FAIL EXPECTED_NEGATIVE_TEST"); end
endmodule
