#!/bin/bash
# v3.10.0 C5 GATE ANTI-VACUUM — selftest-регрессия ВСЕЙ лестницы (16 веток).
# Каждая ветка обязана повторить своё известное число (аудит REV1, a2_selftests).
# Любое отклонение = переключение = FAIL релиза.
set -u
WS=/tmp/poly_ws_v3100
OUT=/home/z/my-project/scripts/v3100_ladder
mkdir -p "$OUT"
CHAIN=/home/z/my-project/scripts/handoff_rev5_build/02_version_chain
EXT=/home/z/my-project/scripts/handoff_rev5_build/06_external_branches
declare -A B=(
  [v124_restored]=/home/z/my-project/download/polymath/polymath_agent.py
  [v1_5_1]="$EXT/polymath_agent_v1.5.1.py"
  [v2_1_0]="$EXT/polymath_agent_v2.1.0.py"
  [v2_2_0]="$CHAIN/polymath_agent_v2.2.0.py"
  [v2_9_0]="$CHAIN/polymath_agent_v2.9.0.py"
  [v3_2_0]="$CHAIN/polymath_agent_v3.2.0.py"
  [v330_J3_3_0]=/home/z/my-project/scripts/rev3_ws/t_v330_J3_3_0.py
  [v331_restored]=/home/z/my-project/scripts/rev3_ws/t_v331_restored.py
  [v330_J3_3_2]=/home/z/my-project/scripts/rev3_ws/t_v330_J3_3_2.py
  [v330_J3_3_3]=/home/z/my-project/scripts/rev3_ws/t_v330_J3_3_3.py
  [v340_restored]=/home/z/my-project/scripts/rev3_ws/t_v340_restored.py
  [v360_TD]=/home/z/my-project/scripts/rev3_ws/t_v360_TD.py
  [v360_RT]=/home/z/my-project/scripts/rev3_ws/t_v360_RT.py
  [v370_restored]=/home/z/my-project/scripts/rev3_ws/t_v370_restored.py
  [v380]=/home/z/my-project/scripts/rev3_ws/t_v380.py
  [v390]=/home/z/my-project/scripts/rev3_ws/t_v390.py
)
declare -A KNOWN=(
  [v124_restored]=19 [v1_5_1]=29 [v2_1_0]=43 [v2_2_0]=52 [v2_9_0]=57 [v3_2_0]=66
  [v330_J3_3_0]=69 [v331_restored]=78 [v330_J3_3_2]=72 [v330_J3_3_3]=74
  [v340_restored]=88 [v360_TD]=98 [v360_RT]=98 [v370_restored]=114 [v380]=130 [v390]=133
)
cd "$WS"
flips=0
for key in v124_restored v1_5_1 v2_1_0 v2_2_0 v2_9_0 v3_2_0 v330_J3_3_0 v331_restored v330_J3_3_2 v330_J3_3_3 v340_restored v360_TD v360_RT v370_restored v380 v390; do
  f="${B[$key]}"
  LOG="$OUT/$key.txt"
  python3 "$f" --selftest > "$LOG" 2>&1
  rc=$?
  got=$(rg -o 'Итого: ([0-9]+)/' -r '$1' "$LOG" | tail -1)
  exp="${KNOWN[$key]}"
  if [ "$got" = "$exp" ] && [ "$rc" = "0" ]; then
    echo "ZERO-FLIP OK  $key  $got/$exp  (exit=$rc)"
  else
    echo "FLIP!!        $key  got=$got exp=$exp exit=$rc"
    flips=$((flips+1))
  fi
done
echo "=== лестница 16 веток: переключений $flips ==="
exit $((flips>0))
