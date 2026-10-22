//multiply i and q by a hann rom, round half up, saturate s16
//idle: accept a beat, wait: rom data lands, hold: present until ready
module window_mult
  import radar_pkg::*;
#(
    parameter int unsigned N     = NS,
    parameter int unsigned W_IN  = W_DC,
    parameter int unsigned SHIFT = WIN_SHIFT_RANGE,
    parameter              INIT_FILE = ""
) (
    input  logic                    clk,
    input  logic                    rst,
    input  logic                    s_valid_i,
    output logic                    s_ready_o,
    input  logic signed [W_IN-1:0]  s_i_i,
    input  logic signed [W_IN-1:0]  s_q_i,
    input  logic                    s_sof_i,
    input  logic                    s_eoc_i,
    input  logic [7:0]              s_idx_i,
    output logic                    m_valid_o,
    input  logic                    m_ready_i,
    output logic signed [W_WIN-1:0] m_i_o,
    output logic signed [W_WIN-1:0] m_q_o,
    output logic                    m_sof_o,
    output logic                    m_eoc_o,
    output logic [7:0]              m_idx_o,
    output logic                    ovf_o
);

  localparam int unsigned AW  = $clog2(N);
  localparam int unsigned P_W = W_IN + W_COEF + 1;

  typedef enum logic [1:0] {
    IDLE,
    WAIT_ROM,
    HOLD
  } state_e;

  state_e state;
  logic signed [W_IN-1:0] buf_i, buf_q;
  logic buf_sof, buf_eoc;
  logic [7:0] buf_idx;
  logic [W_COEF-1:0] coeff;
  logic [AW-1:0] rom_addr;

  rom #(
      .WIDTH(W_COEF),
      .DEPTH(N),
      .INIT_FILE(INIT_FILE)
  ) u_win (
      .clk   (clk),
      .addr_i(rom_addr),
      .data_o(coeff)
  );

  assign s_ready_o = state == IDLE;
  assign rom_addr  = (state == IDLE) ? s_idx_i[AW-1:0] : buf_idx[AW-1:0];

  logic signed [W_COEF:0] w_s;
  assign w_s = $signed({1'b0, coeff});

  logic signed [P_W-1:0] prod_i, prod_q, rnd_i, rnd_q;
  always_comb begin
    prod_i = $signed(buf_i) * w_s;
    prod_q = $signed(buf_q) * w_s;
    rnd_i  = (prod_i + P_W'(1 << (SHIFT - 1))) >>> SHIFT;
    rnd_q  = (prod_q + P_W'(1 << (SHIFT - 1))) >>> SHIFT;
  end

  logic signed [W_WIN-1:0] sat_i, sat_q;
  logic clip_i, clip_q;
  always_comb begin
    clip_i = 1'b0;
    clip_q = 1'b0;
    if (rnd_i > P_W'(16'sh7fff)) begin
      sat_i  = 16'sh7fff;
      clip_i = 1'b1;
    end else if (rnd_i < P_W'(16'sh8000)) begin
      sat_i  = 16'sh8000;
      clip_i = 1'b1;
    end else begin
      sat_i = W_WIN'(rnd_i);
    end
    if (rnd_q > P_W'(16'sh7fff)) begin
      sat_q  = 16'sh7fff;
      clip_q = 1'b1;
    end else if (rnd_q < P_W'(16'sh8000)) begin
      sat_q  = 16'sh8000;
      clip_q = 1'b1;
    end else begin
      sat_q = W_WIN'(rnd_q);
    end
  end

  assign m_valid_o = state == HOLD;

  always_ff @(posedge clk) begin
    if (rst) begin
      state <= IDLE;
      ovf_o <= 1'b0;
    end else begin
      unique case (state)
        IDLE: begin
          if (s_valid_i) begin
            buf_i   <= s_i_i;
            buf_q   <= s_q_i;
            buf_sof <= s_sof_i;
            buf_eoc <= s_eoc_i;
            buf_idx <= s_idx_i;
            state   <= WAIT_ROM;
          end
        end
        WAIT_ROM: begin
          m_i_o   <= sat_i;
          m_q_o   <= sat_q;
          m_sof_o <= buf_sof;
          m_eoc_o <= buf_eoc;
          m_idx_o <= buf_idx;
          ovf_o   <= ovf_o | clip_i | clip_q;
          state   <= HOLD;
        end
        HOLD: begin
          if (m_ready_i) begin
            state <= IDLE;
          end
        end
        default: state <= IDLE;
      endcase
    end
  end

endmodule : window_mult
