#source this from the repo root, source scripts/env.sh
#user space tool installs, no sudo on this machine
#  ~/opt/oss-cad-suite    verilator, icarus, gtkwave, surfer, yosys
#  ~/opt/mamba/envs/build make, gcc, g++ for verilator sim builds
#  ~/.local/bin           uv and verible
#  .venv                  python with numpy, scipy, matplotlib, pytest, cocotb

export PATH="$HOME/opt/mamba/envs/build/bin:$HOME/opt/oss-cad-suite/bin:$HOME/.local/bin:$PATH"

_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$_repo_root/.venv/bin/activate" ]; then
    #shellcheck disable=SC1091
    source "$_repo_root/.venv/bin/activate"
fi
unset _repo_root
