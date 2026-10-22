//inferred simple dual port ram, sync write and sync read
module ram_sdp #(
    parameter int unsigned WIDTH = 16,
    parameter int unsigned DEPTH = 256,
    parameter INIT_FILE = "",
    parameter int unsigned AW = $clog2(DEPTH)
) (
    input  logic             clk,
    input  logic             we_i,
    input  logic [AW-1:0]    waddr_i,
    input  logic [WIDTH-1:0] wdata_i,
    input  logic             re_i,
    input  logic [AW-1:0]    raddr_i,
    output logic [WIDTH-1:0] rdata_o
);

  logic [WIDTH-1:0] mem[DEPTH];

  generate
    if (INIT_FILE != "") begin : gen_init
      initial $readmemh(INIT_FILE, mem);
    end
  endgenerate

  always_ff @(posedge clk) begin
    if (we_i) begin
      mem[waddr_i] <= wdata_i;
    end
    if (re_i) begin
      rdata_o <= mem[raddr_i];
    end
  end

endmodule : ram_sdp
