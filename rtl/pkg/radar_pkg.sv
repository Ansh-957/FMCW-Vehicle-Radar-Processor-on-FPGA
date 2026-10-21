//system parameters, mirrored from model/params.py
package radar_pkg;
  //parameter only package, nothing uses it yet
  /* verilator lint_off UNUSEDPARAM */

  localparam int unsigned NS             = 256;
  localparam int unsigned NC             = 64;
  localparam int unsigned N_RANGE_BINS   = NS / 2;
  localparam int unsigned DOPPLER_ZERO   = NC / 2;

  localparam int unsigned ADC_BITS       = 12;
  localparam int unsigned ADC_MID        = 2048;

  localparam int unsigned FCLK_HZ        = 60_000_000;
  localparam int unsigned PIXEL_CLK_HZ   = 25_200_000;
  localparam int unsigned ADC_SPI_HZ     = FCLK_HZ / 3;

  localparam int unsigned CYC_PER_US     = FCLK_HZ / 1_000_000;
  localparam int unsigned RAMP_US        = 256;
  localparam int unsigned FLYBACK_US     = 24;
  localparam int unsigned FRAME_PERIOD_US_DEFAULT = 50_000;

  localparam int unsigned W_ADC          = 12;
  localparam int unsigned W_DC           = 13;
  localparam int unsigned W_WIN          = 16;
  localparam int unsigned W_FFT          = 18;
  localparam int unsigned W_FRAME        = 16;
  localparam int unsigned W_POWER        = 37;
  localparam int unsigned W_LOG          = 16;
  localparam int unsigned W_COEF         = 16;
  localparam int unsigned W_TWIDDLE      = 18;

  localparam int unsigned WIN_SHIFT_RANGE   = 13;
  localparam int unsigned WIN_SHIFT_DOPPLER = 16;
  localparam int unsigned FB_SHIFT_DEFAULT  = 0;
  localparam int unsigned LOG_MANT_BITS     = 8;
  //per stage halving enables, bit 0 is the first stage
  localparam logic [7:0] FFT_SCALE_RANGE_DEFAULT   = 8'hFF;
  localparam logic [5:0] FFT_SCALE_DOPPLER_DEFAULT = 6'b001111;

  localparam int unsigned CFAR_TRAIN_DEFAULT  = 8;
  localparam int unsigned CFAR_GUARD_DEFAULT  = 2;
  localparam int unsigned CFAR_OFFSET_DEFAULT = 1021;
  localparam int unsigned MAX_TARGETS         = 32;

  localparam int unsigned UART_BAUD_DEFAULT = 921_600;

  localparam logic [11:0] ADDR_ID           = 12'h000;
  localparam logic [11:0] ADDR_STATUS       = 12'h004;
  localparam logic [11:0] ADDR_CONTROL      = 12'h008;
  localparam logic [11:0] ADDR_FRAME_PERIOD = 12'h00C;
  localparam logic [11:0] ADDR_CFAR_CFG     = 12'h010;
  localparam logic [11:0] ADDR_CFAR_OFFSET  = 12'h014;
  localparam logic [11:0] ADDR_FFT_SCALE    = 12'h018;
  localparam logic [11:0] ADDR_FB_SHIFT     = 12'h01C;
  localparam logic [11:0] ADDR_DISPLAY      = 12'h020;
  localparam logic [11:0] ADDR_TONE0        = 12'h040;
  localparam logic [11:0] ADDR_RAMP_LUT     = 12'h100;

  /* verilator lint_on UNUSEDPARAM */
endpackage : radar_pkg
