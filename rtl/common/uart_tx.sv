//uart transmitter, 8n1, lsb first
module uart_tx #(
    parameter int unsigned CLKS_PER_BIT = 65
) (
    input  logic       clk,
    input  logic       rst,
    input  logic       valid_i,
    output logic       ready_o,
    input  logic [7:0] data_i,
    output logic       tx_o
);

  typedef enum logic [1:0] {
    IDLE,
    START,
    DATA,
    STOP
  } state_e;

  state_e state;
  logic [$clog2(CLKS_PER_BIT)-1:0] baud_cnt;
  logic [2:0] bit_idx;
  logic [7:0] shift;

  assign ready_o = state == IDLE;

  logic bit_done;
  assign bit_done = baud_cnt == $clog2(CLKS_PER_BIT)'(CLKS_PER_BIT - 1);

  always_ff @(posedge clk) begin
    if (rst) begin
      state    <= IDLE;
      tx_o     <= 1'b1;
      baud_cnt <= '0;
      bit_idx  <= '0;
    end else begin
      case (state)
        IDLE: begin
          tx_o <= 1'b1;
          if (valid_i) begin
            state    <= START;
            shift    <= data_i;
            tx_o     <= 1'b0;
            baud_cnt <= '0;
          end
        end
        START: begin
          if (bit_done) begin
            state    <= DATA;
            tx_o     <= shift[0];
            shift    <= shift >> 1;
            bit_idx  <= '0;
            baud_cnt <= '0;
          end else begin
            baud_cnt <= baud_cnt + 1'b1;
          end
        end
        DATA: begin
          if (bit_done) begin
            baud_cnt <= '0;
            if (bit_idx == 3'd7) begin
              state <= STOP;
              tx_o  <= 1'b1;
            end else begin
              bit_idx <= bit_idx + 1'b1;
              tx_o    <= shift[0];
              shift   <= shift >> 1;
            end
          end else begin
            baud_cnt <= baud_cnt + 1'b1;
          end
        end
        STOP: begin
          if (bit_done) begin
            state    <= IDLE;
            baud_cnt <= '0;
          end else begin
            baud_cnt <= baud_cnt + 1'b1;
          end
        end
        default: state <= IDLE;
      endcase
    end
  end

endmodule : uart_tx
