# STATUS батарей v3.10.1 (CODEQL HYGIENE)

Прибор: battery_harness.py-семейство (rev2-харнесы, трёхзначная эпистемология).
Вердикты: REPRODUCED (дефект жив, 1 бит), CLOSED (только при W1+W2+W3),
INAPPLICABLE (преусловие не материализовалось / вакуум / затмение, причина названа),
ERROR (сбой прибора).

## Exit-конвенции

| exit | значение |
|---|---|
| 0 | zero-flip против матрицы: ни одного переключения вердикта |
| 1 | ПЕРЕКЛЮЧЕНИЕ вердикта против исторической матрицы |
| 2 | ветка вне матрицы / сценарий не собрался (zero-flip не проверялся) |

## Прогоны против polymath_agent_v3.10.1.py (cb5e6c55…)

| батарея | итог |
|---|---|
| proof_v300_harness | ═══ REPRODUCED=0 CLOSED=4 INAPPLICABLE=1 ERROR=0 ═══ |
| proof_v310_harness | ═══ REPRODUCED=0 CLOSED=2 INAPPLICABLE=0 ERROR=0 ═══ |
| proof_v330_harness | ═══ REPRODUCED=0 CLOSED=7 INAPPLICABLE=1 ERROR=0 ═══ |
| proof_v340_harness | ═══ REPRODUCED=0 CLOSED=6 INAPPLICABLE=0 ERROR=0 ═══ |
| proof_v360_harness | ═══ REPRODUCED=0 CLOSED=4 INAPPLICABLE=0 ERROR=0 ═══ |
| proof_v360_rt_harness | ═══ REPRODUCED=0 CLOSED=4 INAPPLICABLE=0 ERROR=0 ═══ |

Контроль: те же харнесы на v3.10.0 (ef73a158…) — вердикты бит-в-бит
идентичны (логи в artifacts/*__v3100.txt). REPRODUCED=0 и ERROR=0 на обеих ветках.
