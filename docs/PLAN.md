# FMCW Car Radar on FPGA — Implementation Plan

Oct 18, 2026 · @Ansh

## 1. Overview

This project builds the signal-processing chip of a car radar. The design is written in SystemVerilog and runs on a Tang Primer 20K FPGA. It turns raw 24 GHz radar echoes into a live distance-versus-speed map on a monitor, plus a list of detected cars sent to a laptop.

**In plain words.** The radar module sends out a radio chirp whose frequency rises steadily. Echoes come back slightly late, so mixing them with the outgoing chirp produces a tone whose pitch encodes distance. Over many chirps, a moving object's echo shifts a little each time, which encodes speed. The FPGA turns these tones into a distance × speed map, separates real objects from noise, and reports them.

**Goals**

1. Real-time processing at 20 frames per second: 0.75 m range resolution out to about 96 m, and 0.35 m/s speed resolution.
2. Industry-style verification:
   - a bit-exact Python golden model
   - cocotb unit tests
   - a UVM environment with constrained-random scenes
   - functional coverage and SVA assertions
3. Measured, documented results: FPGA utilization, Fmax, processing latency, detection accuracy against the model, and coverage numbers.
4. A unit that runs in a car from 12 V and logs every detected vehicle.

**Phases**

| Phase | What gets built | Hardware needed | Done when |
| --- | --- | --- | --- |
| 1. Simulation | Python model, all RTL, cocotb and UVM testbenches, synthesis reports | Laptop only | Full chain matches the model bit-exact; design fits the FPGA and meets timing |
| 1.5. Board bring-up | Same design on the board, fed by the built-in test-tone generator | Tang Primer 20K | Synthetic targets appear on HDMI and arrive at the laptop |
| 2. Real sensor, indoors | Analog front-end, ADC and DAC drivers, calibration | Pmod AD1, K-LC6, HB100, front-end parts | A walking person is detected; measured range within one bin of a tape measure |
| 3. Car | Tracker, speed unfolding, logging, enclosure, 12 V power | Enclosure, car power cables | Drive logs show cars ahead and oncoming with plausible range and speed |

**Out of scope for v1:** angle or lane measurement (needs a second receiver), using the board's DDR3, and an ASIC tapeout. Section 12 lists these as stretch goals.

## 2. System parameters

The default profile uses 200 MHz chirps of 256 µs, samples I and Q at 1 MSPS, and collects 64 chirps per frame. That gives 0.75 m range bins out to 96 m and 0.35 m/s speed bins up to ±11.1 m/s. Every value lives in `model/params.py` and `rtl/pkg/radar_pkg.sv`, and nowhere else.

| Parameter | Symbol | Value | Reason |
| --- | --- | --- | --- |
| Carrier frequency | f0 | 24.125 GHz | Centre of the K-LC6 and K-LC5 band |
| Wavelength | λ | 12.43 mm | c / f0 |
| Chirp bandwidth | B | 200 MHz | Stays inside 24.05–24.25 GHz |
| Chirp ramp time | Tc | 256 µs | Exactly 256 samples at fs |
| Chirp repetition interval | Tr | 280 µs | Tc plus 24 µs for ramp reset and settling |
| ADC sample rate, per channel | fs | 1 MSPS | Pmod AD1 maximum |
| Samples per chirp | Ns | 256 | Range FFT size |
| Chirps per frame | Nc | 64 | Doppler FFT size |
| Frame acquisition time | – | 17.9 ms | Nc × Tr |
| Frame period | – | 50 ms (20 fps) | Leaves over 30 ms for processing and output |
| System clock | fclk | 60 MHz | ADC SPI clock = fclk / 3 = 20 MHz; 60 clocks per sample |

**Derived limits**

```latex
\begin{aligned}
\Delta R &= \frac{c}{2B} = 0.75\ \text{m} \\
f_b &= \frac{2BR}{c\,T_c} + \frac{2v}{\lambda} \quad (5.21\ \text{kHz per metre}) \\
R_{max} &= \frac{f_s/2}{2B/(c\,T_c)} \approx 96\ \text{m} \\
\Delta v &= \frac{\lambda}{2 N_c T_r} = 0.347\ \text{m/s} \\
v_{max} &= \pm\frac{\lambda}{4 T_r} = \pm 11.1\ \text{m/s}
\end{aligned}
```

- **Range bins.** Complex I/Q sampling gives 256 FFT bins covering −500 to +500 kHz. Targets appear in the positive half, so only bins 0–127 are kept, covering 0 to 96 m.
- **Doppler bins.** There are 64 bins after the FFT shift. Bin 32 is zero speed, and each bin is 0.347 m/s (1.25 km/h).
- **Range–Doppler coupling.** A target at 11 m/s shifts its beat tone by 1.8 kHz, which is under half a range bin (3.9 kHz). v1 ignores it.
- **Speed aliasing.** Anything faster than ±11.1 m/s relative wraps around. That includes oncoming traffic and roadside objects at highway speed. Phase 3 unfolds it using the tracker's range rate (section 12).

**Speed-only profile (HB100 / CDM324).** These modules have no chirp input and one output, so they measure speed but not distance or direction.

| Setting | HB100 (10.525 GHz) | CDM324 (24.125 GHz) |
| --- | --- | --- |
| Sampling | I channel, 1 MSPS, decimated ÷128 to 7.8125 kSPS | Same |
| FFT | 256 points, 30.5 Hz per bin | Same |
| Speed per bin | 0.43 m/s | 0.19 m/s |
| Maximum speed | 55.7 m/s | 24.3 m/s |

## 3. Architecture

Samples enter at the ADC and leave as an HDMI heat map and UART packets. The top row runs once per chirp, the middle rows once per frame, and the bottom row holds outputs and control.

- **Per chirp:** 256 I/Q samples arrive at 1 MSPS. The range FFT finishes in about 17 µs and writes bins 0–127 into the frame buffer as one column.
- **Per frame:** after 64 chirps, the Doppler pass reads each range bin as a row. It windows, transforms and takes log power, building the 128 × 64 map that CFAR scans.
- **Off-chip:** the chirp controller drives the MCP4822 DAC, which sets the radar's VCO through the front-end. The radar's I/Q outputs pass through the front-end amplifiers to the Pmod AD1.
- **Clock domains:** everything runs at 60 MHz except HDMI. The display buffer is the only data crossing between domains.

## 4. Fixed-point specification

Every stage's word width and rounding is defined here and implemented identically in `model/fixed/` and in the RTL. Milestone M2 confirms these widths lose less than 1 dB of SNR against floating point, then freezes them.

| Stage | Input | Output | Rounding and overflow | Notes |
| --- | --- | --- | --- | --- |
| ADC capture | 12-bit unsigned (offset binary) | s12 | – | Subtract 2048 |
| DC removal | s12 | s13 | Exact | Subtract the **current** chirp's mean per channel (sum of 256 samples >> 8, rounded). The mean is accumulated while the chirp fills the FFT input bank; a ~256-cycle pre-pass over the bank then subtracts it (and applies the window) before the transform starts. No "previous mean" edge case; model and RTL match exactly |
| Range window | s13 × u16 Hann | s16 | Round half up, saturate | Coefficient ROM: 256 × u16 |
| Range FFT, 256 points | s16 complex | s18 complex | Round half up each stage; ÷2 per stage by default (configurable schedule) | Twiddles s18 (Q1.17); 18-bit datapath matches the 18×18 multipliers |
| Frame buffer | s18 | s16 | Round, saturate, configurable shift | 32 bits per cell (I and Q) |
| Doppler window | s16 × u16 Hann | s16 | Round half up, saturate | Coefficient ROM: 64 × u16 |
| Doppler FFT, 64 points | s16 complex | s18 complex | Same as range FFT | Same engine |
| Power | s18 complex | u37 | Exact | I² + Q² |
| Log power | u37 | u16 | Piecewise-linear log2: leading-one position + 8 mantissa bits | L = 256 · log2(P); 256 units = 3.01 dB |
| CFAR | u16 | 1-bit detect | – | Threshold = mean of training cells + offset T (same units) |
| Display | u16 | u8 | (L − black level) >> contrast, clamp | 256 × 24-bit colour map ROM |

**Rules**

- **Round half up** means add 1 << (shift − 1), then shift right arithmetically. The Python model uses integer operations only, never floats.
- **Every narrowing step saturates.** Each stage sets a sticky overflow flag in the status register. Testbenches fail on any overflow unless the test expects it.
- **One source for ROM contents.** `scripts/gen_rom.py` writes the twiddle, window, log and colour-map tables to `.mem` files. The RTL loads them with `$readmemh` and the model loads the same files.

## 5. RTL module specifications

The design is about 25 modules in five folders. Only `rtl/top/top_primer20k.sv` and `fpga/gowin/` may use Gowin primitives; everything else is vendor-neutral, so it simulates in Verilator and in Vivado's simulator.

| Module | Folder | Job |
| --- | --- | --- |
| `ram_sdp`, `rom` | common | Inferred simple dual-port RAM and ROM, loaded from `.mem` files |
| `sync_fifo`, `async_fifo` | common | Buffers; the async FIFO uses Gray-code pointers for clock crossing |
| `cdc_sync`, `pulse_sync`, `skid_buffer` | common | Two-flop synchronizer, pulse crossing, valid/ready register slice |
| `uart_tx`, `uart_rx` | common | 8N1 serial at a configurable baud rate |
| `adc_pmod_ad1` | frontend | SPI master for the two AD7476A chips: 20 MHz clock, one chip-select, two data lines; emits an I/Q pair every 1 µs |
| `dac_mcp4822` | frontend | Writes one 12-bit ramp code per µs to the MCP4822 over SPI |
| `chirp_ctrl` | frontend | Frame and chirp timing; reads the 256-entry ramp table that linearizes the VCO |
| `test_tone_gen` | frontend | Up to 4 synthetic targets plus LFSR noise, so the full chain runs with no radar attached |
| `cw_decimator` | frontend | ÷128 decimating filter for speed-only modules |
| `source_mux` | frontend | Selects ADC, test tones, or speed-only path |
| `dc_remove` | dsp | Subtracts the current chirp's per-channel mean (accumulated during capture, applied in a ~256-cycle pre-pass over the FFT bank), which cancels transmit leakage |
| `window_mult` | dsp | Multiplies I and Q by a ROM window (256-point and 64-point instances) |
| `fft_engine` | dsp | Memory-based radix-2 FFT, size 64, 128 or 256 chosen at run time |
| `fft_sched` | dsp | Runs one range FFT per chirp, then 128 Doppler FFTs per frame |
| `frame_buffer` | dsp | The corner turn: writes one chirp as a column, reads one range bin as a row |
| `power_log` | dsp | I² + Q², then the log2 approximation |
| `cfar_ca` | dsp | Cell-averaging CFAR along range for each Doppler column, CA, GO and SO modes |
| `peak_detect` | dsp | Keeps a detection only if it beats all 8 neighbours in a 3 × 3 window |
| `target_list` | dsp | Stores up to 32 targets per frame, keeping the strongest |
| `reg_file` | io | Register map written and read over UART |
| `packetizer` | io | Frames targets, maps, raw captures and status with a sync word and CRC-16 |
| `video_timing`, `tmds_encoder` | io | 640 × 480 at 60 Hz, TMDS encoding |
| `rd_renderer` | io | Draws the map as a heat map, marks targets, prints the target list from a font ROM |
| `radar_core` | top | Everything above except pins, PLLs and serializers |
| `top_primer20k` | top | PLLs, pin mapping, Gowin serializer primitives for HDMI |

### FFT engine: why memory-based

The throughput requirement is low, so one butterfly is enough.

- **Range FFT:** 256 points is 1,024 butterflies. At one per clock that is about 17 µs at 60 MHz, against a 280 µs chirp, or 6% busy.
- **Doppler FFTs:** 128 FFTs of 64 points is 24,576 butterflies, about 0.41 ms per frame.
- **Cost comparison:** a fully pipelined streaming FFT would use roughly ten times the multipliers for throughput the design does not need.

**Design details**

- **Butterfly:** decimation in frequency, X = A + B and Y = (A − B) × W, with ÷2 scaling on both outputs. It is pipelined over about 5 cycles and uses 4 multipliers.
- **Memory:** two banks of 256 × 36 bits in ping-pong. While the engine transforms chirp k in one bank, chirp k + 1 fills the other.
- **Stage hazards:** between stages the engine waits for the butterfly pipeline to drain, about 48 idle cycles per 256-point FFT, which is negligible.
- **Output order:** results come out bit-reversed, and the read-out address generator reverses them.
- **Twiddles:** one ROM of 128 entries. Smaller FFT sizes step through it with a stride.
- **Upgrade path:** a radix-4 butterfly or two parallel butterflies if a future profile needs more throughput.

### Frame sequence

1. **Acquire, 17.9 ms.** `chirp_ctrl` runs 64 chirps. After each chirp, `fft_sched` runs the range FFT and writes bins 0–127 into `frame_buffer` as column k.
2. **Doppler, about 0.41 ms.** For each range bin, read its 64 values, window, FFT, compute log power, write to the range-Doppler map RAM.
3. **Detect, about 0.3 ms.** `cfar_ca` scans each Doppler column. `peak_detect` uses two line buffers for the 3 × 3 check. `target_list` collects the results.
4. **Output.** The packetizer sends targets every frame and the map every fourth frame. The map is copied to the display buffer, which the HDMI clock domain reads.
5. **Idle** until the 50 ms frame tick. The frame buffer is single-buffered because Doppler processing ends before the next frame starts.

### Chirp controller timing

- **States:** IDLE, then RAMP (256 µs), then FLYBACK (24 µs), repeated 64 times, then PROCESS, then wait for the frame tick.
- **DAC updates:** one per µs, aligned to the ADC sample strobe, so sample n is taken during ramp step n.
- **SPI timing:** an MCP4822 write is 16 bits at 20 MHz, which is 0.8 µs and fits in the 1 µs slot. DAC A drives the VCO; DAC B is spare, for example as a test output.
- **Module voltages:** the 12-bit ramp codes are the same for all modules. The K-LC5's 0–3.3 V range or the K-LC6's 1–10 V range is set by the analog front-end jumper.

### CFAR and target list

- **Window:** 2 guard cells and 8 training cells on each side of the cell under test; at the array edges, only the side that exists is used.
- **Modes:** CA averages both sides. GO takes the greater side, which reduces false alarms at clutter edges. SO takes the smaller side.
- **Threshold offset:** defaults to 1,021 units, about 12 dB, and is set by register.
- **Indoor option:** a register can exclude Doppler bin 32, ignoring everything that isn't moving.
- **Units:** targets are reported as range bin, Doppler bin and log power. The host converts to metres and m/s; the HDMI renderer does the same conversion with fixed-point constants.

## 6. Interfaces and protocols

There are three interfaces: valid/ready streams between DSP blocks, a register map for configuration, and a framed UART protocol to the laptop.

### Internal sample stream

Every DSP block passes samples on the same stream. Most blocks never apply backpressure, but they all use the stream so the UVM agents are uniform.

| Signal | Width | Meaning |
| --- | --- | --- |
| `valid` | 1 | Data is present |
| `ready` | 1 | Receiver accepts it; a transfer happens when valid and ready are both high |
| `i`, `q` | Per stage (section 4) | Signed sample |
| `sof` | 1 | First sample of a frame |
| `eoc` | 1 | Last sample of a chirp, or of an FFT row |
| `idx` | 8 | Sample or bin index inside the chirp or row |

**Rules, each enforced by an SVA assertion:** valid never waits for ready. Once valid is high, data and valid hold until the transfer happens. Exactly Ns samples arrive between `eoc` pulses.

### Register map

32-bit registers, accessed with UART command packets.

| Address | Name | Fields | Default |
| --- | --- | --- | --- |
| 0x000 | ID (read only) | ASCII "RDR1" + build date | – |
| 0x004 | STATUS (read only) | Overflow flags per stage, frame counter | – |
| 0x008 | CONTROL | [0] run · [2:1] source: 0 FMCW, 1 test tones, 2 speed only, 3 reserved · [3] exclude zero speed · [4] arm raw capture | 0x1 |
| 0x00C | FRAME_PERIOD_US | Frame period in µs | 50,000 |
| 0x010 | CFAR_CFG | [1:0] mode CA/GO/SO · [5:2] training cells · [8:6] guard cells | CA, 8, 2 |
| 0x014 | CFAR_OFFSET | Threshold offset in log units | 1,021 |
| 0x018 | FFT_SCALE | Per-stage ÷2 enable, one bit per stage | All ones |
| 0x01C | FB_SHIFT | Frame-buffer narrowing shift | 2 |
| 0x020 | DISPLAY | [15:0] black level · [19:16] contrast shift | – |
| 0x040–0x06C | TONE0–TONE3 | Per tone: frequency word, phase step per chirp, amplitude | Off |
| 0x100–0x4FC | RAMP_LUT | 256 × 12-bit VCO ramp codes | Linear ramp |

### Laptop protocol (UART)

- **Link:** 921,600 baud 8N1 to start. Raise it if the Dock's USB-serial chip allows (open question, section 12).
- **Packet:** `0xA5 0x5A` · type (1 byte) · length (2, little-endian) · sequence (2) · payload · CRC-16/CCITT over type to payload.

| Type | Direction | Payload | Rate |
| --- | --- | --- | --- |
| 0x01 TARGETS | FPGA → laptop | Frame id (4), count (1), then per target: range bin (1), Doppler bin (1), log power (2), SNR estimate (2) | Every frame, about 200 bytes |
| 0x02 RD_MAP | FPGA → laptop | Frame id (4), 128 × 64 u8 map | Every 4th frame, 8 KB |
| 0x03 RAW_CHUNK | FPGA → laptop | Raw ADC samples from 8 chirps, in 1 KB chunks | On request |
| 0x04 STATUS | FPGA → laptop | Copy of STATUS register | 1 Hz |
| 0x05 REG_VALUE | FPGA → laptop | Address (2), value (4) | Reply to 0x82 |
| 0x81 REG_WRITE | Laptop → FPGA | Address (2), value (4) | On demand |
| 0x82 REG_READ | Laptop → FPGA | Address (2) | On demand |

At 921,600 baud the link carries about 92 KB/s. Targets use about 4 KB/s and maps about 40 KB/s, leaving headroom.

## 7. Repository layout and coding conventions

One Git repository holds the model, RTL, tests, board files and laptop tools. Each RTL module has a matching cocotb test folder.

```text
radar-fpga/
  README.md                  results, demo video, how to run
  AGENTS.md                  AI rules (section 13)
  docs/PLAN.md               this plan, exported to Markdown
  model/                     Python golden model
    params.py                every parameter from section 2
    scene.py                 synthetic targets, noise, leakage, I/Q imbalance
    chain_float.py           floating-point reference chain
    fixed/                   bit-exact integer model, one file per block
    tests/                   pytest
  scripts/gen_rom.py         twiddle, window, log, colour-map .mem files
  rtl/
    pkg/radar_pkg.sv         parameters and types
    common/  frontend/  dsp/  io/  top/
  tb/
    cocotb/<module>/         unit tests, one folder per module
    cocotb/radar_core/       integration test
    uvm/                     env, agents, sequences, scoreboard, coverage
    dpi/                     C reference model for UVM
    sva/                     assertion modules, bound to the RTL
  fpga/gowin/                project, pin constraints (.cst), timing (.sdc)
  host/                      live viewer, logger, tracker
  .github/workflows/ci.yml   pytest + lint + cocotb on every push
```

**SystemVerilog conventions**

- **Language:** the SystemVerilog-2012 synthesizable subset. Code must pass `verilator --lint-only -Wall` and synthesize in Gowin EDA. Check which SV features Gowin accepts in M3 before relying on structs or interfaces in synthesizable code.
- **Registers and logic:** `always_ff` with non-blocking `<=` for registers, `always_comb` with blocking `=` for logic, no latches.
- **Clock and reset:** clock is `clk`, reset is synchronous active-high `rst`. One clock per module except the CDC primitives in `common/`.
- **Port names:** inputs end in `_i`, outputs in `_o`, active-low signals in `_n`.
- **Parameters:** all from `radar_pkg`; no magic numbers.
- **Memories:** inferred through `ram_sdp` and `rom`; vendor primitives only in the top-level board file.
- **Signed maths:** declare `signed` explicitly, widen before multiplying or adding, and comment every truncation.

**Python conventions**

- `model/fixed/` uses integer arithmetic only, so it matches the RTL bit for bit.
- Each fixed-point block has a matching float block and a test that measures the SNR difference.
- Plots go to `out/`, which is not committed to Git.

## 8. Toolchain setup

Work on Linux: every tool here runs on Linux, and cocotb and Verilator are far easier there than on Windows. Everything is free.

| Tool | Used for | Install |
| --- | --- | --- |
| Python 3.11+ in a venv | Model, cocotb, laptop tools | `python3 -m venv .venv`, then `pip install numpy scipy matplotlib pytest cocotb pyserial pyqtgraph PyQt6` |
| Verilator 5.x | Lint, fast simulation under cocotb | Ubuntu package if recent enough, otherwise build from source; match the minimum version in cocotb's docs |
| GTKWave or Surfer | Viewing waveforms | `sudo apt install gtkwave` |
| Verible | SystemVerilog formatter and linter | Prebuilt release from the chipsalliance/verible GitHub page |
| Vivado ML Standard | Its simulator, xsim, runs UVM | Free AMD account download; install the simulator only, no device support needed |
| Gowin EDA | Synthesis, place and route, bitstream for the GW2A-18 | Linux build from Gowin; check Sipeed's Tang Primer 20K guide for the right edition and license |
| openFPGALoader | Loading the bitstream over USB | `sudo apt install openfpgaloader` |

## 9. Verification strategy

The Python fixed-point model is the single source of truth, and every RTL block must match it bit for bit before it is merged. Verification runs in four layers.

| Layer | Tool | What it checks | Runs |
| --- | --- | --- | --- |
| 1. Model | pytest | Fixed model vs float model (SNR loss under 1 dB); known answers | Every push (CI) |
| 2. Unit | cocotb + Verilator | Each module against its `model/fixed/` block | Every push (CI) |
| 3. Integration | cocotb + Verilator | `radar_core` fed scenes from `scene.py`; bit-exact | Every push (CI) |
| 4. UVM | Vivado xsim | Constrained-random scenes, scoreboard, coverage, assertions | Locally; reports committed |

See the original plan for unit-test essentials, the UVM environment, and the coverage plan.

## 10. Milestones

### Phase 1: simulation (laptop only)

- **M0. Environment and skeleton** — repo, folders, CI (pytest + lint + one cocotb test); counter synthesizes in Gowin EDA.
- **M1. Floating-point model** — `scene.py`, `chain_float.py`; injected targets within ±1 bin.
- **M2. Fixed-point model** — integer blocks per stage; `.mem` files; SNR loss < 1 dB; widths frozen.
- **M3. Common library** — RAM/ROM, FIFOs, synchronizers, skid buffer, UART; Gowin SV feature check.
- **M4. Front of the chain** — `dc_remove`, `window_mult`, `test_tone_gen` bit-exact.
- **M5. FFT engine** — bit-exact at 64/128/256; `fft_sched` with ping-pong banks.
- **M6. Corner turn and Doppler** — `frame_buffer` verified; full map bit-exact.
- **M7. Detection** — `cfar_ca`, `peak_detect`, `target_list` bit-exact.
- **M8. Core integration** — `radar_core`: 20 random scenes bit-exact.
- **M9. UVM environment** — coverage 100%, zero assertion failures.
- **M10. Synthesis and timing** — full design meets 60 MHz system / 25.2 MHz pixel.

### Phase 1.5: board bring-up

- **M11.** LED/UART/HDMI bring-up; test tones through the full chain; host viewer live.

### Phase 2: real sensor, indoors

- **M12.** Front-end built; raw ADC capture; DAC-to-ADC loopback.
- **M13.** HB100 speed mode; K-LC6 FMCW mode; ramp table calibrated.
- **M14.** Range within ±1 bin of tape measure at 3, 5 and 10 m; demo video.

### Phase 3: car

- **M15.** Host tracker, speed unfolding, CSV logs.
- **M16.** 12 V power, enclosure, drive logs in README.

## 11. Resource and timing budget

The design should use about half the logic but about 40 of the 46 block RAMs, so memory is the constraint to watch. These are planning estimates; M10 replaces them with real numbers.

| Memory | Size | 18 Kbit blocks |
| --- | --- | --- |
| Frame buffer, 128 × 64 × 32 bits | 256 Kbit | 16 |
| Range-Doppler log map, 128 × 64 × 16 bits | 128 Kbit | 8 |
| Display buffer, 128 × 64 × 8 bits | 64 Kbit | 4 |
| Raw capture, 8 chirps × 256 × 24 bits | 48 Kbit | 3 |
| FFT ping-pong banks, 2 × 256 × 36 bits | 18 Kbit | 2 |
| Window ROMs, twiddle ROM | – | 3 |
| CFAR line buffers, ramp table, font ROM, colour map | – | 4 |
| **Total** |  | **about 40 of 46** |

**Clocks:** system 60 MHz (aim 75), pixel 25.2 MHz, TMDS serial 126 MHz.

**Frame latency:** about 21 ms from the first chirp to targets on the laptop.

**If block RAM runs out:** shrink raw capture to 4 chirps, pack the frame buffer at 24 bits per cell, DDR3 as last resort.

## 12. Risks, open questions and stretch goals

| Risk | Effect | Mitigation |
| --- | --- | --- |
| VCO frequency is not linear in voltage | Range peaks smear across bins | Calibrate the ramp table against a corner reflector (M13) |
| MCP4822 ramp too coarse or slow | Spurious peaks | Measure with DAC-to-ADC loopback (M12); fall back to resistor ladder |
| Block RAM runs out | Design doesn't fit | Shrink raw capture, pack frame buffer, then DDR3 |
| Transmit leakage saturates amplifier or ADC | Clipped samples, false targets | DC removal, high-pass coupling, lower gain |
| Oncoming cars exceed ±11.1 m/s | Wrong speed | Unfold with tracker range rate; staggered Tr |
| Gowin rejects some SV features | RTL won't synthesize | Test structs/packages/interfaces in M3 |
| AI-written RTL has subtle bugs | Silent wrong results | Nothing merges without bit-exact tests |

**Open questions:** Dock USB-serial max baud; Gowin EDA edition/license for GW2A-18; exact 18×18 multiplier count; K-LC6 V2 availability.

**Stretch goals:** RTL tracker, sub-bin interpolation, staggered chirps, Tiny Tapeout CFAR tile, Ethernet output, angle measurement, ultrasonic sonar mode, blind-corner unit.

## 13. Working with AI assistants

See `AGENTS.md` in the repository root. Order of work for every block: model block → test → RTL → passing test → merge.

## 14. Glossary

See the original plan document for the full glossary (FMCW, chirp, beat frequency, I/Q, range bin, Doppler, CFAR, corner turn, twiddle, TMDS, etc.).
