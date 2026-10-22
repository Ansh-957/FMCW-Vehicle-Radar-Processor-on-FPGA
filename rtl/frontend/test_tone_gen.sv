//up to 4 nco tones plus lfsr noise, s12 i/q stream
module test_tone_gen
  import radar_pkg::*;
#(
    parameter INIT_FILE = ""
) (
    input  logic                    clk,
    input  logic                    rst,
    input  logic                    run_i,
    input  logic [N_TONES-1:0]      tone_en_i,
    input  logic [N_TONES*16-1:0]   tone_amp_i,
    input  logic [N_TONES*32-1:0]   tone_fw_i,
    input  logic [N_TONES*32-1:0]   tone_dphi_i,
    input  logic [15:0]             noise_gain_i,
    output logic                    m_valid_o,
    input  logic                    m_ready_i,
    output logic signed [W_ADC-1:0] m_i_o,
    output logic signed [W_ADC-1:0] m_q_o,
    output logic                    m_sof_o,
    output logic                    m_eoc_o,
    output logic [7:0]              m_idx_o,
    output logic                    ovf_o
);

  typedef enum logic {
    LOAD,
    EMIT
  } state_e;

  state_e state;
  logic [7:0] idx;
  logic [$clog2(NC)-1:0] chirp;
  logic [PHASE_W-1:0] phase    [N_TONES];
  logic [PHASE_W-1:0] chirp_ph [N_TONES];
  logic [15:0] lfsr;
  logic sof_next;

  logic [NCO_IDX_BITS-1:0] rom_addr [N_TONES];
  logic [NCO_WIDTH-1:0]    rom_data [N_TONES];
  logic signed [16:0] tone_i_sc [N_TONES];
  logic signed [16:0] tone_q_sc [N_TONES];

  genvar g;
  generate
    for (g = 0; g < int'(N_TONES); g++) begin : gen_nco
      assign rom_addr[g] = phase[g][PHASE_W-1 -: NCO_IDX_BITS];
      rom #(
          .WIDTH(NCO_WIDTH),
          .DEPTH(NCO_DEPTH),
          .INIT_FILE(INIT_FILE)
      ) u_nco (
          .clk   (clk),
          .addr_i(rom_addr[g]),
          .data_o(rom_data[g])
      );

      logic signed [17:0] cos_w;
      logic signed [17:0] sin_w;
      logic signed [33:0] prod_i;
      logic signed [33:0] prod_q;
      assign cos_w  = $signed(rom_data[g][NCO_WIDTH-1:18]);
      assign sin_w  = $signed(rom_data[g][17:0]);
      logic signed [15:0] amp_g;
      assign amp_g  = $signed(tone_amp_i[g*16 +: 16]);
      assign prod_i = cos_w * amp_g;
      assign prod_q = sin_w * amp_g;
      assign tone_i_sc[g] = tone_en_i[g] ? 17'((prod_i + 34'sd65536) >>> 17) : 17'sd0;
      assign tone_q_sc[g] = tone_en_i[g] ? 17'((prod_q + 34'sd65536) >>> 17) : 17'sd0;
    end
  endgenerate

  function automatic logic [15:0] lfsr_step(input logic [15:0] s);
    return {s[14:0], s[15] ^ s[14] ^ s[12] ^ s[3]};
  endfunction

  logic [15:0] lfsr_q;
  logic signed [11:0] n_i12, n_q12;
  logic signed [16:0] ng;
  logic signed [28:0] np_i, np_q;
  logic signed [19:0] noise_i, noise_q;
  assign lfsr_q  = lfsr_step(lfsr);
  assign n_i12   = $signed(lfsr[15:4]);
  assign n_q12   = $signed(lfsr_q[15:4]);
  assign ng      = $signed({1'b0, noise_gain_i});
  assign np_i    = 29'(n_i12) * 29'(ng);
  assign np_q    = 29'(n_q12) * 29'(ng);
  assign noise_i = 20'((np_i + 29'(1 << (NOISE_SHIFT - 1))) >>> NOISE_SHIFT);
  assign noise_q = 20'((np_q + 29'(1 << (NOISE_SHIFT - 1))) >>> NOISE_SHIFT);

  logic signed [19:0] acc_i, acc_q;
  assign acc_i = 20'(tone_i_sc[0]) + 20'(tone_i_sc[1])
               + 20'(tone_i_sc[2]) + 20'(tone_i_sc[3]) + noise_i;
  assign acc_q = 20'(tone_q_sc[0]) + 20'(tone_q_sc[1])
               + 20'(tone_q_sc[2]) + 20'(tone_q_sc[3]) + noise_q;

  logic clip_i, clip_q;
  logic signed [W_ADC-1:0] sat_i, sat_q;
  always_comb begin
    clip_i = 1'b0;
    clip_q = 1'b0;
    if (acc_i > 20'sd2047) begin
      sat_i  = 12'sd2047;
      clip_i = 1'b1;
    end else if (acc_i < -20'sd2048) begin
      sat_i  = -12'sd2048;
      clip_i = 1'b1;
    end else begin
      sat_i = W_ADC'(acc_i);
    end
    if (acc_q > 20'sd2047) begin
      sat_q  = 12'sd2047;
      clip_q = 1'b1;
    end else if (acc_q < -20'sd2048) begin
      sat_q  = -12'sd2048;
      clip_q = 1'b1;
    end else begin
      sat_q = W_ADC'(acc_q);
    end
  end

  assign m_valid_o = state == EMIT;
  assign m_i_o     = sat_i;
  assign m_q_o     = sat_q;
  assign m_idx_o   = idx;
  assign m_sof_o   = sof_next && (idx == 8'd0);
  assign m_eoc_o   = idx == 8'(NS - 1);

  integer t;
  always_ff @(posedge clk) begin
    if (rst) begin
      state    <= LOAD;
      idx      <= '0;
      chirp    <= '0;
      lfsr     <= LFSR_SEED;
      sof_next <= 1'b1;
      ovf_o    <= 1'b0;
      for (t = 0; t < int'(N_TONES); t++) begin
        phase[t]    <= '0;
        chirp_ph[t] <= '0;
      end
    end else begin
      unique case (state)
        LOAD: begin
          if (run_i) begin
            state <= EMIT;
          end
        end
        EMIT: begin
          ovf_o <= ovf_o | clip_i | clip_q;
          if (m_ready_i) begin
            lfsr <= lfsr_step(lfsr_q);
            if (idx == 8'(NS - 1)) begin
              idx      <= '0;
              sof_next <= 1'b0;
              if (chirp == $clog2(NC)'(NC - 1)) begin
                chirp    <= '0;
                sof_next <= 1'b1;
                for (t = 0; t < int'(N_TONES); t++) begin
                  chirp_ph[t] <= '0;
                  phase[t]    <= '0;
                end
              end else begin
                chirp <= chirp + 1'b1;
                for (t = 0; t < int'(N_TONES); t++) begin
                  chirp_ph[t] <= chirp_ph[t] + tone_dphi_i[t*32 +: 32];
                  phase[t]    <= chirp_ph[t] + tone_dphi_i[t*32 +: 32];
                end
              end
            end else begin
              idx <= idx + 8'd1;
              for (t = 0; t < int'(N_TONES); t++) begin
                phase[t] <= phase[t] + tone_fw_i[t*32 +: 32];
              end
            end
            state <= LOAD;
          end
        end
        default: state <= LOAD;
      endcase
    end
  end

endmodule : test_tone_gen
