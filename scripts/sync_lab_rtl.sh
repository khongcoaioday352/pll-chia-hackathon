#!/usr/bin/env bash
# Copy current lab RTL into the CHIA project; never write to the hardware repo.
set -euo pipefail
src="${1:-$HOME/stdcell-pll}"
project="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="$project/rtl_gf180_snapshot"
test -f "$src/src/rtl/gf180/digital_pll.v" || { echo 'Missing lab GF180 RTL' >&2; exit 1; }
test -f "$src/src/rtl/gf180/ring_osc2x13.v" || { echo 'Missing lab ring oscillator RTL' >&2; exit 1; }
test -f "$src/src/rtl/digital_pll_controller.v" || { echo 'Missing lab controller RTL' >&2; exit 1; }
mkdir -p "$target"
cp "$src/src/rtl/gf180/digital_pll.v" "$target/digital_pll.v"
cp "$src/src/rtl/gf180/ring_osc2x13.v" "$target/ring_osc2x13.v"
cp "$src/src/rtl/digital_pll_controller.v" "$target/digital_pll_controller.v"
test -s "$target/clockbuf_shim.v" || { echo 'Missing simulator clockbuf_shim.v' >&2; exit 1; }
sha256sum "$target/digital_pll.v" "$target/ring_osc2x13.v" "$target/digital_pll_controller.v"
echo 'Lab RTL copied into rtl_gf180_snapshot; original repository unchanged.'
