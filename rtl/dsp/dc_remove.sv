//subtract the current chirp mean per channel, s12 in s13 out
//own 256x24 ram is for unit test only, the core uses the fft bank instead
module dc_remove
  import radar_pkg::*;
(
    input  logic                     clk,
    input  logic                     rst,
    input  logic                     s_valid_i,
    output logic                     s_ready_o,
    input  logic signed [W_ADC-1:0]  s_i_i,
    input  logic signed [W_ADC-1:0]  s_q_i,
    input  logic                     s_sof_i,
    input  logic                     s_eoc_i,
    input  logic [7:0]               s_idx_i,
    output logic                     m_valid_o,
    input  logic                     m_ready_i,
    output logic signed [W_DC-1:0]   m_i_o,
    output logic signed [W_DC-1:0]   m_q_o,
    output logic                     m_sof_o,
    output logic                     m_eoc_o,
    output logic [7:0]               m_idx_o
);

  localparam int unsigned ACC_W = W_ADC + $clog2(NS) + 1;
  localparam int unsigned RAM_W = 2 * W_ADC;

  typedef enum logic [1:0] {
    FILL,
    WAIT_RD,
    DRAIN
  } state_e;

  state_e state;
  logic [7:0] wr_ptr;
  logic [7:0] out_idx;
  logic signed [ACC_W-1:0] acc_i, acc_q;
  logic signed [W_DC-1:0] mean_i, mean_q;
  logic sof_held;

  logic we;
  logic re;
  logic [7:0] waddr, raddr;
  logic [RAM_W-1:0] wdata, rdata;

  ram_sdp #(
      .WIDTH(RAM_W),
      .DEPTH(NS)
  ) u_buf (
      .clk    (clk),
      .we_i   (we),
      .waddr_i(waddr),
      .wdata_i(wdata),
      .re_i   (re),
      .raddr_i(raddr),
      .rdata_o(rdata)
  );

  logic signed [W_ADC-1:0] rd_i, rd_q;
  assign rd_i = rdata[RAM_W-1:W_ADC];
  assign rd_q = rdata[W_ADC-1:0];

  logic take_in;
  assign take_in   = s_valid_i && s_ready_o;
  assign s_ready_o = state == FILL;

  logic signed [ACC_W-1:0] acc_i_next, acc_q_next;
  always_comb begin
    acc_i_next = acc_i;
    acc_q_next = acc_q;
    if (take_in) begin
      acc_i_next = acc_i + ACC_W'(s_i_i);
      acc_q_next = acc_q + ACC_W'(s_q_i);
    end
  end

  always_comb begin
    we    = 1'b0;
    re    = 1'b0;
    waddr = wr_ptr;
    raddr = '0;
    wdata = {s_i_i, s_q_i};
    unique case (state)
      FILL: begin
        we    = take_in;
        waddr = s_idx_i;
      end
      WAIT_RD: begin
        re    = 1'b1;
        raddr = '0;
      end
      DRAIN: begin
        if (m_valid_o && m_ready_i && out_idx != 8'(NS - 1)) begin
          re    = 1'b1;
          raddr = out_idx + 8'd1;
        end
      end
      default: ;
    endcase
  end

  assign m_valid_o = state == DRAIN;
  assign m_i_o     = W_DC'(rd_i) - mean_i;
  assign m_q_o     = W_DC'(rd_q) - mean_q;
  assign m_idx_o   = out_idx;
  assign m_sof_o   = (out_idx == 8'd0) && sof_held;
  assign m_eoc_o   = out_idx == 8'(NS - 1);

  always_ff @(posedge clk) begin
    if (rst) begin
      state   <= FILL;
      wr_ptr  <= '0;
      out_idx <= '0;
      acc_i   <= '0;
      acc_q   <= '0;
      mean_i  <= '0;
      mean_q  <= '0;
      sof_held <= 1'b0;
    end else begin
      unique case (state)
        FILL: begin
          if (take_in) begin
            if (wr_ptr == 8'd0) begin
              sof_held <= s_sof_i;
            end
            wr_ptr <= wr_ptr + 8'd1;
            acc_i  <= acc_i_next;
            acc_q  <= acc_q_next;
            if (s_eoc_i) begin
              //mean = (sum + 128) >>> 8
              mean_i <= W_DC'((acc_i_next + ACC_W'(1 << 7)) >>> 8);
              mean_q <= W_DC'((acc_q_next + ACC_W'(1 << 7)) >>> 8);
              wr_ptr <= '0;
              acc_i  <= '0;
              acc_q  <= '0;
              state  <= WAIT_RD;
            end
          end
        end
        WAIT_RD: begin
          out_idx <= '0;
          state   <= DRAIN;
        end
        DRAIN: begin
          if (m_valid_o && m_ready_i) begin
            if (out_idx == 8'(NS - 1)) begin
              state   <= FILL;
              out_idx <= '0;
            end else begin
              out_idx <= out_idx + 8'd1;
            end
          end
        end
        default: state <= FILL;
      endcase
    end
  end

endmodule : dc_remove
