//inferred rom loaded from a .mem file, sync read
module rom #(
    parameter int unsigned WIDTH = 16,
    parameter int unsigned DEPTH = 256,
    parameter INIT_FILE = "",
    parameter int unsigned AW = $clog2(DEPTH)
) (
    input  logic             clk,
    input  logic [AW-1:0]    addr_i,
    output logic [WIDTH-1:0] data_o
);

  logic [WIDTH-1:0] mem[DEPTH];

  initial $readmemh(INIT_FILE, mem);

  always_ff @(posedge clk) begin
    data_o <= mem[addr_i];
  end

endmodule : rom
