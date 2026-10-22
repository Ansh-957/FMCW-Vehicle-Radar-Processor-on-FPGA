//single cycle pulse crossing via a toggle flop, pulses must be spaced
//several destination clocks apart
module pulse_sync (
    input  logic sclk,
    input  logic srst,
    input  logic pulse_i,
    input  logic dclk,
    input  logic drst,
    output logic pulse_o
);

  logic       toggle;
  logic [2:0] sync;

  always_ff @(posedge sclk) begin
    if (srst) begin
      toggle <= 1'b0;
    end else begin
      toggle <= toggle ^ pulse_i;
    end
  end

  always_ff @(posedge dclk) begin
    if (drst) begin
      sync <= 3'b000;
    end else begin
      sync <= {sync[1:0], toggle};
    end
  end

  assign pulse_o = sync[2] ^ sync[1];

endmodule : pulse_sync
