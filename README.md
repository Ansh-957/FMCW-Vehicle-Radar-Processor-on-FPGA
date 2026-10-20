# FMCW Vehicle Radar Processor on FPGA

An FMCW (frequency-modulated continuous wave) automotive radar signal processor written in
SystemVerilog for the Sipeed Tang Primer 20K (Gowin GW2A-18). Raw 24 GHz radar echoes become
a live range-Doppler heat map on HDMI and a target list streamed to a laptop over UART.

Full specification: [docs/PLAN.md](docs/PLAN.md)

## Status

| Milestone | Description | Status |
| --- | --- | --- |
| M0 | Environment and skeleton | In progress |
| M1 | Floating-point golden model | In progress |
| M2–M10 | Fixed-point model, RTL, UVM, synthesis | Planned |
| M11–M16 | Board bring-up, real sensor, in-car | Planned |

## Key numbers (default profile)

- 24.125 GHz carrier, 200 MHz chirps of 256 µs, 64 chirps per frame, 20 fps
- 0.75 m range resolution out to ~96 m; 0.35 m/s speed resolution up to ±11.1 m/s
- 256-point range FFT + 64-point Doppler FFT on a shared memory-based radix-2 engine

## Repository layout

```text
model/      Python golden model (params.py, scene.py, chain_float.py, fixed/, tests/)
scripts/    gen_rom.py — twiddle, window, log and colour-map .mem files
rtl/        SystemVerilog: pkg/ common/ frontend/ dsp/ io/ top/
tb/         cocotb unit + integration tests, UVM env, DPI-C model, SVA
fpga/gowin/ Gowin project, pin (.cst) and timing (.sdc) constraints
host/       live viewer, logger, tracker (laptop side)
```

## How to run

```bash
# set up PATH (Verilator, make/g++, Verible) and activate the venv
source scripts/env.sh

# golden-model tests
pytest model/tests -v

# cocotb unit tests (needs Verilator 5.x)
make -C tb/cocotb/counter
```

## Results

Utilization, Fmax, latency, coverage and detection accuracy will be published here at M10+.
