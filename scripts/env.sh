# Source this from the repo root to set up the toolchain:  source scripts/env.sh
# All tools are user-space installs (no sudo on this machine):
#   ~/opt/oss-cad-suite    Verilator 5.x, Icarus, GTKWave, Surfer, yosys, cocotb-config
#   ~/opt/mamba/envs/build make, gcc, g++ (conda-forge, needed by Verilator builds)
#   ~/.local/bin           uv, verible-verilog-lint / -format
#   .venv                  Python 3.12: numpy, scipy, matplotlib, pytest, cocotb, pyserial

export PATH="$HOME/opt/mamba/envs/build/bin:$HOME/opt/oss-cad-suite/bin:$HOME/.local/bin:$PATH"

_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$_repo_root/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$_repo_root/.venv/bin/activate"
fi
unset _repo_root
