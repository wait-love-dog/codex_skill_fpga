`timescale 1ns/1ps
`include "config.vh"
module acx720_smoke(input wire clk, input wire reset_n, input wire [2:0] sw,
                    output wire [7:0] led);
    reg [31:0] rom [0:`ROM_WORDS-1];
    initial $readmemh("rom/values.hex",rom);
    reg [3:0] por = 0;
    always @(posedge clk) if (!por[3]) por <= por+1'b1;
    wire request = !por[3] || !reset_n || !sw[0];
    (* ASYNC_REG="TRUE" *) reg [1:0] run_sync=0;
    always @(posedge clk or posedge request)
        if(request) run_sync<=0; else run_sync<={run_sync[0],1'b1};
    reg [7:0] tick=0;
    always @(posedge clk) if(!run_sync[1]) tick<=0; else tick<=tick+1'b1;
    assign led = run_sync[1] ? {rom[0][6:0],tick[2]} : 8'd0;
endmodule
