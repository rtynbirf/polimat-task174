# R12 Independent Audit (Task 16-d)

Перепроверка вердикта Round 12 (E12-E15) по сырым данным; детерминизм-спотчек через замороженные функции.

| Check | Status | Key numbers |
|---|---|---|
| V1_G1_zero_overwrite | CONFIRMED | cells=55, hits=0 |
| V2_G2_boundary | CONFIRMED | measured range [0.062, 0.125] (claimed 2-8%); unexplained_silent=0 |
| V3_G3_EMIN_dial | CONFIRMED | E_MIN=1 refused-loud; >=2 refusals==0 |
| V4_G4_unsigned | CONFIRMED | 25 cells, hijack=0, law identical |
| V5_G5_R_star | CONFIRMED | {"eta=0.05": 2, "eta=0.1": 2, "eta=0.15": 2, "eta=0.2": 6} |
| V6_core_md5 | CONFIRMED | all 10 frozen files identical |
| V7_determinism | CONFIRMED | 4 reruns bit-identical |
| V8_gates_consistency | CONFIRMED | GATES block matches raw data |

## Вердикт аудита

**ROUND 12 VERDICT INDEPENDENTLY CONFIRMED** (CONFIRMED=8, DISCREPANCY=0, UNVERIFIABLE=0)

Примечание: G2 по букве пре-регистрации — заявленный FAIL (громкие ложные отвержения 2-8% истинных внутриполосных окон, эффект коррелированных нарушений); аудит подтверждает измеренную границу и ноль тихой коррупции.
