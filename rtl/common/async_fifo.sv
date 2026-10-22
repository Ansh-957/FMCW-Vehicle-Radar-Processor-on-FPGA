//asynchronous fifo with gray coded pointers, depth must be a power of two
module async_fifo #(
    parameter int unsigned WIDTH = 16,
    parameter int unsigned DEPTH = 16,
    parameter int unsigned AW = $clog2(DEPTH)
) (
    input  logic             wclk,
    input  logic             wrst,
    input  logic             wvalid_i,
    output logic             wready_o,
    input  logic [WIDTH-1:0] wdata_i,
    input  logic             rclk,
    input  logic             rrst,
    output logic             rvalid_o,
    input  logic             rready_i,
    output logic [WIDTH-1:0] rdata_o
);

  logic [WIDTH-1:0] mem[DEPTH];
  logic [AW:0] wptr_bin, wptr_gray;
  logic [AW:0] rptr_bin, rptr_gray;
  logic [AW:0] rptr_gray_w;  //read pointer seen in the write domain
  logic [AW:0] wptr_gray_r;  //write pointer seen in the read domain

  cdc_sync #(.WIDTH(AW + 1)) u_sync_rptr (
      .clk(wclk),
      .d_i(rptr_gray),
      .q_o(rptr_gray_w)
  );

  cdc_sync #(.WIDTH(AW + 1)) u_sync_wptr (
      .clk(rclk),
      .d_i(wptr_gray),
      .q_o(wptr_gray_r)
  );

  //full when the gray pointers differ only in the top two bits
  assign wready_o = wptr_gray != {~rptr_gray_w[AW:AW-1], rptr_gray_w[AW-2:0]};
  assign rvalid_o = rptr_gray != wptr_gray_r;
  assign rdata_o  = mem[rptr_bin[AW-1:0]];

  logic [AW:0] wptr_bin_next;
  logic [AW:0] rptr_bin_next;
  assign wptr_bin_next = wptr_bin + (AW + 1)'(wvalid_i && wready_o);
  assign rptr_bin_next = rptr_bin + (AW + 1)'(rvalid_o && rready_i);

  always_ff @(posedge wclk) begin
    if (wrst) begin
      wptr_bin  <= '0;
      wptr_gray <= '0;
    end else begin
      if (wvalid_i && wready_o) begin
        mem[wptr_bin[AW-1:0]] <= wdata_i;
      end
      wptr_bin  <= wptr_bin_next;
      wptr_gray <= (wptr_bin_next >> 1) ^ wptr_bin_next;
    end
  end

  always_ff @(posedge rclk) begin
    if (rrst) begin
      rptr_bin  <= '0;
      rptr_gray <= '0;
    end else begin
      rptr_bin  <= rptr_bin_next;
      rptr_gray <= (rptr_bin_next >> 1) ^ rptr_bin_next;
    end
  end

endmodule : async_fifo
