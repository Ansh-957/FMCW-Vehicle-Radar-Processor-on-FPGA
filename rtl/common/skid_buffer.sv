//valid ready register slice, full throughput, registered outputs
module skid_buffer #(
    parameter int unsigned WIDTH = 16
) (
    input  logic             clk,
    input  logic             rst,
    input  logic             s_valid_i,
    output logic             s_ready_o,
    input  logic [WIDTH-1:0] s_data_i,
    output logic             m_valid_o,
    input  logic             m_ready_i,
    output logic [WIDTH-1:0] m_data_o
);

  logic [WIDTH-1:0] skid_data;
  logic             skid_full;

  assign s_ready_o = !skid_full;

  always_ff @(posedge clk) begin
    if (rst) begin
      m_valid_o <= 1'b0;
      skid_full <= 1'b0;
    end else begin
      if (s_valid_i && s_ready_o) begin
        if (m_valid_o && !m_ready_i) begin
          //output stalled, park the incoming beat
          skid_full <= 1'b1;
          skid_data <= s_data_i;
        end else begin
          m_valid_o <= 1'b1;
          m_data_o  <= s_data_i;
        end
      end
      if (m_valid_o && m_ready_i) begin
        if (skid_full) begin
          skid_full <= 1'b0;
          m_valid_o <= 1'b1;
          m_data_o  <= skid_data;
        end else if (!(s_valid_i && s_ready_o)) begin
          m_valid_o <= 1'b0;
        end
      end
    end
  end

endmodule : skid_buffer
