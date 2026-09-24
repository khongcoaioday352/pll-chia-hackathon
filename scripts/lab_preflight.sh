#!/usr/bin/env bash
# Read-only checks. Run from any directory on the lab server.
set -u
printf 'Hardware repository: '
if test -d "$HOME/stdcell-pll/src/rtl/gf180"; then printf 'OK\n'; else printf 'MISSING\n'; fi
if git -C "$HOME/stdcell-pll" rev-parse HEAD >/dev/null 2>&1; then printf 'Lab PLL commit: %s\n' "$(git -C "$HOME/stdcell-pll" rev-parse HEAD)"; fi
for app in git python3 npm node iverilog vvp verilator g++ make openroad sta; do
  if command -v "$app" >/dev/null 2>&1; then printf '%-11s %s\n' "$app" "$(command -v "$app")"; else printf '%-11s MISSING\n' "$app"; fi
done
if command -v python3 >/dev/null 2>&1; then
  python3 --version
  python3 -m pip --version 2>&1 || true
fi
if command -v node >/dev/null 2>&1; then node --version; fi
if command -v df >/dev/null 2>&1; then df -h "$HOME" /tmp | tail -n 2; fi
if command -v free >/dev/null 2>&1; then free -h | head -n 2; fi
for app in opencode vsim; do
  if command -v "$app" >/dev/null 2>&1; then printf '%-11s %s\n' "$app" "$(command -v "$app")"; else printf '%-11s MISSING ON PATH\n' "$app"; fi
done
if test -x /home/tools/mentor/questasim/2024.2/questasim/bin/vsim; then printf 'Questa executable: OK\n'; fi
for f in "$HOME/stdcell-pll/openroad/results/gf180/pll/base/6_final.v" "$HOME/stdcell-pll/openroad/results/gf180/pll/base/6_final.spef"; do
  if test -s "$f"; then printf 'FOUND %s\n' "$f"; else printf 'MISSING %s\n' "$f"; fi
done
for c in BC TC WC; do
  f="$HOME/stdcell-pll/openroad/results/gf180/pll/$c/digital_pll.sdf"
  if test -s "$f"; then printf '%s SDF OK\n' "$c"; else printf '%s SDF MISSING\n' "$c"; fi
done
