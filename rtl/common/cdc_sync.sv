//two flop synchronizer, for single bits or quasi static buses only
module cdc_sync #(
    parameter int unsigned WIDTH = 1
) (
    input  logic             clk,
    input  logic [WIDTH-1:0] d_i,
    output logic [WIDTH-1:0] q_o
);

  logic [WIDTH-1:0] meta;

  always_ff @(posedge clk) begin
    meta <= d_i;
    q_o  <= meta;
  end

endmodule : cdc_sync
