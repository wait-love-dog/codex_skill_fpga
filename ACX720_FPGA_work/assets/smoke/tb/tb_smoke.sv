`timescale 1ns/1ps
module tb_smoke;
    reg clk=0, reset_n=1;
    reg [2:0] sw=3'b111;
    wire [7:0] led;
    always #10 clk=~clk;
    acx720_smoke dut(clk,reset_n,sw,led);
    integer changes=0;
    always @(posedge led[0]) changes=changes+1;
    initial begin
        #50;
        if(dut.rom[0]!==32'hAC72005A) $fatal(1,"FAIL memory file not loaded");
        #550;
        if(dut.run_sync!==2'b11 || changes<2) $fatal(1,"FAIL default-high startup");
        sw[0]=0;
        #80;
        if(led!==0) $fatal(1,"FAIL active-low switch reset");
        sw[0]=1;
        #100;
        if(dut.run_sync!==2'b11) $fatal(1,"FAIL reset release");
        $display("PASS ACX720_WORKFLOW_SMOKE memory/reset/clock/production-top");
        $finish;
    end
    initial begin #2000; $fatal(1,"FAIL timeout"); end
endmodule
