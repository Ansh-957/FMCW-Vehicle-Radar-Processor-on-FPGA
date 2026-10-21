//smoke test module for the cocotb and synthesis flow
module counter #(
    parameter int unsigned WIDTH = 8
) (
    input  logic             clk,
    input  logic             rst,
    input  logic             en_i,
    output logic [WIDTH-1:0] count_o
);

  always_ff @(posedge clk) begin
    if (rst) begin
      count_o <= '0;
    end else if (en_i) begin
      count_o <= count_o + WIDTH'(1);
    end
  end

endmodule : counter
