// radar_pkg: every system parameter, mirrored from model/params.py.
// PLAN.md section 2 is the specification. Any change here must update
// model/params.py and docs/PLAN.md in the same commit.
package radar_pkg;
  // Parameter-only package: entries are defined ahead of the modules that
  // will consume them, so standalone lint must not flag them as unused.
  /* verilator lint_off UNUSEDPARAM */

  // Sampling and frame geometry
  localparam int unsigned NS             = 256;  // samples per chirp = range FFT size
  localparam int unsigned NC             = 64;   // chirps per frame  = Doppler FFT size
  localparam int unsigned N_RANGE_BINS   = NS / 2;  // keep positive-beat half: 0..127
  localparam int unsigned DOPPLER_ZERO   = NC / 2;  // bin 32 = zero speed

  // ADC
  localparam int unsigned ADC_BITS       = 12;
  localparam int unsigned ADC_MID        = 2048;    // offset-binary midpoint

  // Clocks (Hz)
  localparam int unsigned FCLK_HZ        = 60_000_000;
  localparam int unsigned PIXEL_CLK_HZ   = 25_200_000;
  localparam int unsigned ADC_SPI_HZ     = FCLK_HZ / 3;  // 20 MHz

  // Timing in system-clock cycles (1 us = 60 cycles at 60 MHz)
  localparam int unsigned CYC_PER_US     = FCLK_HZ / 1_000_000;
  localparam int unsigned RAMP_US        = 256;   // Tc
  localparam int unsigned FLYBACK_US     = 24;    // Tr - Tc
  localparam int unsigned FRAME_PERIOD_US_DEFAULT = 50_000;  // 20 fps

  // Fixed-point widths (PLAN.md section 4). Frozen at M2.
  localparam int unsigned W_ADC          = 12;  // s12 after mid subtraction
  localparam int unsigned W_DC           = 13;  // s13 after DC removal
  localparam int unsigned W_WIN          = 16;  // s16 after windowing
  localparam int unsigned W_FFT          = 18;  // s18 FFT datapath
  localparam int unsigned W_FRAME        = 16;  // s16 frame-buffer cell per component
  localparam int unsigned W_POWER        = 37;  // u37 = I^2 + Q^2
  localparam int unsigned W_LOG          = 16;  // u16 log power
  localparam int unsigned W_COEF         = 16;  // u16 window coefficients
  localparam int unsigned W_TWIDDLE      = 18;  // s18 Q1.17 twiddles

  // CFAR defaults
  localparam int unsigned CFAR_TRAIN_DEFAULT  = 8;
  localparam int unsigned CFAR_GUARD_DEFAULT  = 2;
  localparam int unsigned CFAR_OFFSET_DEFAULT = 1021;  // log units, ~12 dB
  localparam int unsigned MAX_TARGETS         = 32;

  // UART
  localparam int unsigned UART_BAUD_DEFAULT = 921_600;

  // Register addresses (PLAN.md section 6)
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
