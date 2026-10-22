//synchronous fifo, first word fall through, depth must be a power of two
module sync_fifo #(
    parameter int unsigned WIDTH = 16,
    parameter int unsigned DEPTH = 16,
    parameter int unsigned AW = $clog2(DEPTH)
) (
    input  logic             clk,
    input  logic             rst,
    input  logic             wvalid_i,
    output logic             wready_o,
    input  logic [WIDTH-1:0] wdata_i,
    output logic             rvalid_o,
    input  logic             rready_i,
    output logic [WIDTH-1:0] rdata_o
);

  logic [WIDTH-1:0] mem[DEPTH];
  logic [AW:0] wptr;
  logic [AW:0] rptr;

  assign wready_o = (wptr - rptr) != (AW + 1)'(DEPTH);
  assign rvalid_o = wptr != rptr;
  assign rdata_o  = mem[rptr[AW-1:0]];

  always_ff @(posedge clk) begin
    if (rst) begin
      wptr <= '0;
      rptr <= '0;
    end else begin
      if (wvalid_i && wready_o) begin
        mem[wptr[AW-1:0]] <= wdata_i;
        wptr <= wptr + (AW + 1)'(1);
      end
      if (rvalid_o && rready_i) begin
        rptr <= rptr + (AW + 1)'(1);
      end
    end
  end

endmodule : sync_fifo
