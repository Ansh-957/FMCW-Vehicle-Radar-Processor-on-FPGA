//gowin sv feature probe, synthesize this standalone for the GW2A-18 and
//record which constructs survive, each feature is tagged below
//single self contained file on purpose
/* verilator lint_off DECLFILENAME */
package feat_pkg;
  localparam int unsigned WIDTH = 8;

  //feature: typedef packed struct
  typedef struct packed {
    logic [7:0] data;
    logic       flag;
  } beat_t;

  //feature: enum with explicit encoding
  typedef enum logic [1:0] {
    S_IDLE = 2'd0,
    S_RUN  = 2'd1,
    S_DONE = 2'd2
  } state_e;
endpackage : feat_pkg

//feature: interface with modports
interface stream_if;
  logic valid;
  logic ready;
  logic [7:0] data;
  modport src(output valid, output data, input ready);
  modport dst(input valid, input data, output ready);
endinterface : stream_if

module sv_feature_test (
    input  logic       clk,
    input  logic       rst,
    input  logic [7:0] din_i,
    input  logic       den_i,
    output logic [7:0] dout_o,
    output logic       busy_o
);
  //feature: package import
  import feat_pkg::*;

  state_e state;
  beat_t beat;

  stream_if s ();

  //feature: size cast and $clog2
  localparam int unsigned CNT_W = $clog2(WIDTH) + 1;
  logic [CNT_W-1:0] cnt;

  assign s.valid = den_i;
  assign s.data  = din_i;

  always_ff @(posedge clk) begin
    if (rst) begin
      state <= S_IDLE;
      cnt   <= '0;
      beat  <= '0;
    end else begin
      case (state)
        S_IDLE: begin
          if (s.valid && s.ready) begin
            beat.data <= s.data;
            beat.flag <= 1'b1;
            state     <= S_RUN;
            cnt       <= '0;
          end
        end
        S_RUN: begin
          cnt <= cnt + CNT_W'(1);
          if (cnt == CNT_W'(WIDTH - 1)) begin
            state <= S_DONE;
          end
        end
        S_DONE: begin
          beat.flag <= 1'b0;
          state     <= S_IDLE;
        end
        default: state <= S_IDLE;
      endcase
    end
  end

  always_comb begin
    s.ready = state == S_IDLE;
    busy_o  = state != S_IDLE;
    dout_o  = beat.flag ? beat.data : ~beat.data;
  end

  //feature: generate for
  logic [3:0] parity;
  generate
    for (genvar g = 0; g < 4; g++) begin : gen_parity
      always_ff @(posedge clk) begin
        if (rst) begin
          parity[g] <= 1'b0;
        end else begin
          parity[g] <= parity[g] ^ din_i[2*g] ^ din_i[2*g+1];
        end
      end
    end
  endgenerate
  //keep parity alive so synthesis cannot strip it
  /* verilator lint_off UNUSEDSIGNAL */
  logic parity_any;
  /* verilator lint_on UNUSEDSIGNAL */
  always_ff @(posedge clk) parity_any <= |parity;

endmodule : sv_feature_test
