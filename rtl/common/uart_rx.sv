//uart receiver, 8n1, lsb first, mid bit sampling with start bit verify
module uart_rx #(
    parameter int unsigned CLKS_PER_BIT = 65
) (
    input  logic       clk,
    input  logic       rst,
    input  logic       rx_i,
    output logic       valid_o,
    output logic [7:0] data_o
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
  logic rx_q, rx_qq;  //input synchronizer

  always_ff @(posedge clk) begin
    if (rst) begin
      rx_q  <= 1'b1;
      rx_qq <= 1'b1;
    end else begin
      rx_q  <= rx_i;
      rx_qq <= rx_q;
    end
  end

  always_ff @(posedge clk) begin
    if (rst) begin
      state    <= IDLE;
      valid_o  <= 1'b0;
      baud_cnt <= '0;
      bit_idx  <= '0;
    end else begin
      valid_o <= 1'b0;
      case (state)
        IDLE: begin
          if (!rx_qq) begin
            state    <= START;
            baud_cnt <= '0;
          end
        end
        START: begin
          //verify the start bit is still low at mid bit
          if (baud_cnt == $clog2(CLKS_PER_BIT)'(CLKS_PER_BIT / 2)) begin
            if (!rx_qq) begin
              state    <= DATA;
              baud_cnt <= '0;
              bit_idx  <= '0;
            end else begin
              state <= IDLE;  //glitch, not a real start bit
            end
          end else begin
            baud_cnt <= baud_cnt + 1'b1;
          end
        end
        DATA: begin
          if (baud_cnt == $clog2(CLKS_PER_BIT)'(CLKS_PER_BIT - 1)) begin
            baud_cnt <= '0;
            shift    <= {rx_qq, shift[7:1]};
            if (bit_idx == 3'd7) begin
              state <= STOP;
            end else begin
              bit_idx <= bit_idx + 1'b1;
            end
          end else begin
            baud_cnt <= baud_cnt + 1'b1;
          end
        end
        STOP: begin
          if (baud_cnt == $clog2(CLKS_PER_BIT)'(CLKS_PER_BIT - 1)) begin
            baud_cnt <= '0;
            state    <= IDLE;
            if (rx_qq) begin
              valid_o <= 1'b1;
              data_o  <= shift;
            end
          end else begin
            baud_cnt <= baud_cnt + 1'b1;
          end
        end
        default: state <= IDLE;
      endcase
    end
  end

endmodule : uart_rx
