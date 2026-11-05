# ROUND 14 — R13-PO → M2-VALUE CHANNEL
## Журнал раунда: верификация значений при relearn (H5d′v3.1-M2V) на стенде REPLICA-1

**Дата:** 2026-09-03 · **Точка продолжения:** Task 16-d / Round 13 (независимый аудит Round 12 = 8/8 CONFIRMED)
**Среда:** REPLICA-1 — реконструкция H5d′v3.1 по MASTER HANDOFF в новой среде. Оригинальный frozen core в эту среду не переносился; все результаты раунда имеют статус **REPLICA\***.
**Дисциплина:** §0/§23 handoff — разделение FACT / MEASURED / VERIFIED\* / DECLARED MODELING CHOICE / INTERPRETATION / HYPOTHESIS / UNKNOWN.

---

## 0. Канонические константы (не пересматриваются)

| Константа | Значение | Статус |
|---|---|---|
| G2 (громкие ложные отвержения) | **[0.062, 0.125] = 6.2–12.5%** | MEASURED на исходном стенде (Task 16-d). Значение «2–8%» отозвано ранее и не используется |
| N5 closure | **CLOSED\*** (в исходном стенде, на проверенных атаках, при oracle-independence) | VERIFIED\* |
| Silent corruption | 0 | MEASURED (исходный стенд) |
| Round 9′ «обход 1/30» | легитимная смена эпохи [R2, R3, W1] — НЕ атакерский обход | FACT (переатрибуция Round 10) |
| P3 FAIL (Round 13-PO) | rho=0.2: acc=0.938; rho=0.1/0.3: acc=1.0; механизм — M2-value channel | MEASURED (исходный стенд) |
| H5d′v3.2 (source-of-propagation clustering) | кандидат, НЕ доказан | HYPOTHESIS |
| General Minimality трёх осей | UNKNOWN | UNKNOWN |

---

## 1. CURRENT STATE — восстановленная архитектура

Целое (кольцо N=16, период P=4, алфавит 4 значений) интегрирует свидетельства автономных частей через конвейер:

```text
AUTONOMOUS PARTS → CONTACT → EVIDENCE SPACE
   → edge-checks (источник-мажорита, кросс-источниковая когерентность; MC3-корреляция)
   → {GLUED (hash-chain, append-only ledger) | PARKED_CHALLENGED | REJECTED_LOUD | STAT_EXCESS}
   → proposal-свидетельства → law-complete gate ВНУТРИ _relearn (v3-hardening)
   → EPOCH SWITCH (полная замена закона, law_history immutability)
   → value-layer (эпох-скоуп, VLI: TENTATIVE/VERIFIED, attested anchor/repair)
```

Ключевые свойства: `CONTACT ≠ TRUTH ≠ AUTHORITY`; `PARKED_CHALLENGED = пространство проверки, не наказание`; `GLUED = иммутабельная история, тихая перезапись невозможна по построению`; `CAPABILITY ≠ AUTHORITY`; легитимный путь эпохи не блокируется (урок Round 9′/10).

**Открытые каналы до R14:** (1) M2-value channel — при vacuum coherence припаркованный law-clean kernel попадает в `known` вместе с законом (Round 13-PO: P3 FAIL, acc=0.938 @ rho=0.2 — громкая деградация); (2) остаточная G2-граница eps=0.2/eps0=0.1 (0.104→0.062 после v3.1); (3) non-harm, identity, origin of trust anchor — формализации нет.

---

## 2. WHAT IS ACTUALLY PROVEN (на данный момент сессии)

- **N5 = CLOSED\*** — в исходном стенде, на проверенных атаках (A1/A2/A3, n5v), при независимом аудите. Звезда обязательна: не универсальная минимальность и не закон реального мира. **FACT-уровень исходного стенда.**
- **G2 = [0.062, 0.125], silent = 0** — MEASURED (исходный стенд, Round 12 + Task 16-d 8/8).
- **P3 FAIL @ rho=0.2 = громкая деградация через M2-value channel** — MEASURED (исходный стенд, Round 13-PO).
- **R14 (этот раунд, REPLICA\*):** класс явления M2-value воспроизведён и закрыт механизмом M2V — см. §8–11. VERIFIED\* в REPLICA-1 только.

## 3. WHAT IS ONLY INTERPRETATION / HYPOTHESIS

- `ЧЕЛОВЕК = ЦЕЛОЕ > СУММА ЧАСТЕЙ` — нормативно-системная аксиома (§25 handoff), не биология и не теорема.
- Holobiont как «уровень отбора» — предмет научной дискуссии; для H5d′ — концептуальная область сопоставления (§2 handoff). Критика усилилась (§4 ниже).
- `INTEGRATION = SYNTHESIS OF THE BEST, BOUNDED BY NON-HARM` — концептуальная формула; non-harm не формализован (§33 handoff).
- Тезис §31 («целостность = механизм интеграции конфликта, не подавление») — HYPOTHESIS проекта; литературная норма говорит о **подавлении** конфликта (см. §4, W4).
- `law-complete = non-harm` — запрещено инвариантом §36.

---

## 4. ВЕБ-АУДИТ ВНЕШНИХ ОСНОВАНИЙ (§44-A; CLAIM → SOURCE → EVIDENCE → INFERENCE)

Выполнено 14 поисковых запросов; полный протокол — `stand/web/AUDIT_NOTES.md`, сырые выдачи — `stand/web/q1–q14.json`.

| # | Опора | SOURCE | EVIDENCE (существенное) | INFERENCE для проекта | Статус |
|---|---|---|---|---|---|
| W1 | hologenome | Rosenberg & Zilber-Rosenberg, *Microbiome* 2018 (~611 цит.) | «The holobiont can function as a whole: anatomically, metabolically, immunologically, developmentally, and during evolution» | концептуальная область сопоставления подтверждена | SUPPORT-аналогия |
| W2 | фреймворк | Bordenstein & Theis, *PLOS Biology* 2015 (~1616); Theis et al. 2016 (~581) | «Holobionts and hologenomes are incontrovertible, multipartite entities» | терминология устоялась, основание актуально | SUPPORT |
| W3 | критика | Moran & Sloan, *PLOS Biology* 2015 (~598) | «selection at the community level occurs in some cases, [but] should not be accepted as the null hypothesis»; низкая fidelity передачи | `HOLOBIONT ≠ доказательство H5d′` — подтверждено | CRITIQUE |
| W3+ | **новое после handoff** | Douglas et al. 2026 (ecoEvoRxiv #13115); Kohl 2025 (*Integr. Comp. Biol.*) | «The holobiont is not a useful model for most host-microbiome systems»; «shifting understanding of the holobiont» | **каноническая поправка R14: критика holobiont УСИЛИЛАСЬ (2023–2026); статус «область сопоставления» понижать нельзя — он и так не был доказательством** | CRITIQUE+ |
| W4 | MLS / major transitions | Szathmáry 2015 (MET 2.0); Wilson & Van Vugt; Okasha 2005 | «A major transition requires mechanisms that **suppress conflict** among individuals within groups» | тезис handoff §31 (интеграция без подавления) — **реформуляция, не следствие литературы** | HYPOTHESIS |
| W5 | conflict resolution | Bourke 2023 (*Proc. R. Soc. B*, PMC10565403) | дискуссия о роли conflict resolution в major transitions активна | актуальность INTEGRATION-исследования подтверждена | SUPPORT-дискуссия |
| W6 | индивидуальность | Buss 1987; Michod 1998 | germ-line sequestration «denies heritability to selfish cell lineages» | биологический аналог PARKED/GLUED-фильтрации канала наследуемости | АНАЛОГИЯ |
| W7 | cancer as cheating | Aktipis et al. 2015 (~633) | «cancer represents a breakdown of multicellular cooperation, with cancer cells 'cheating'» | N5-класс («внутренний паразит») осмыслен биологически | АНАЛОГИЯ |
| W8 | policing | обзорные источники по эусоциальности | «the policing of worker-laid eggs is very effective» | пример конвертации конфликта в интегрированное поведение | АНАЛОГИЯ |
| W9 | governance | Ostrom (polycentricity, 8 design principles) | participatory decision-making, градуированные санкции, механизмы разрешения конфликтов | Level C: «участие без суверенитета» реализуемо институционально | МЭППИНГ-кандидат |
| W10 | capture | Stigler 1971; Boehm 2007; Grafton 2020 | capture = co-option регулятора интересом; rent-seeking без улучшения качества | N5-класс имеет социальные корреляты; тождество механизмов НЕ объявляется | АНАЛОГИЯ |
| W11 | immutability | transparency.dev/Trillian; SSRN 2025; arXiv 2026 | append-only + hash-chain = отраслевой стандарт tamper-evidence | GLUED-дисциплина соответствует инженерной практике | ПРАКТИКА |
| W12 | robust stats | Huber ε-contamination (обзоры 2023–2026) | ε-contamination — стандартная рамка распределённой устойчивости | статистический слой E11 актуален | ПРАКТИКА |

**Вывод §44-A:** внешние основания handoff актуальны; одно каноническое усиление (W3+); один подтверждённый скрытый скачок (W4: suppression vs integration).

---

## 5. КАРТА СКРЫТЫХ ЛОГИЧЕСКИХ СКАЧКОВ (§44-C) и минимальные мосты (§44-D)

Цепочка: `H5d′ → holobiont → human → whole → common good → non-harm`.

| # | Скачок | В чём риск | Минимальный мост (проверяемый) | Статус моста |
|---|---|---|---|---|
| S1 | H5d′ → holobiont | стенд-результат (Level A) выдаётся за биологию (Level C) | сопоставление терминов: CONTACT↔горизонтальный перенос, GLUED↔sequestration, N5↔cheater/cancer — только как словарь аналогий | DECLARED ANALOGY |
| S2 | holobiont → human | «у природы есть целые ⇒ человек = целое» | аксиома §25 объявляется нормативной гипотезой, исследуемой отдельно (MLS, behavioral econ) | HYPOTHESIS |
| S3 | suppression → integration | литература: «suppress conflict»; handoff: «интегрировать конфликт» | R14 даёт эмпирическую опору: легитимный путь эпохи не блокируется (E5: 12/12, trio false rejects = 0), при этом часть сохраняет канал (PARKED) и откат к старому закону запрещён (REJECTED_HISTORY) | ЭМПИРИКА REPLICA\* |
| S4 | whole → common good | «интеграция = общее благо» по умолчанию | non-harm как ОТДЕЛЬНЫЙ формальный предикат; в R14 — операционализация «value-layer чист при переключении» как минимальный non-harm-прокси | ЧАСТИЧНО (R14) |
| S5 | law-complete → non-harm | инвариант §36: тождество запрещено | R14 подтверждает различие: law-complete переключение произошло, но value-layer деградировал (v3.1) — полнота закона не защищает значения | ЭМПИРИКА REPLICA\* |

**Проверка S5 — главный концептуальный результат раунда:** в REPLICA-1 v3.1 закон переключается корректно (epoch_match=True во всех ячейках), а финальная точность падает до 0.9375 — то есть **law-complete переключение и целостность value-layer — разные инварианты**. Это прямое эмпирическое подтверждение `LAW_COMPLETE ≠ AUTOMATICALLY NON_HARM` (§36) и аргумент, что non-harm требует собственного формального слоя (§33: кандидат — «harm как уменьшение допустимого пространства будущих состояний»).

---

## 6. OPEN GAP → ВЫБОР ТРЕКА

Приоритеты §43 handoff: (1) R13-G2 v3.2 — требует исходного стенда (кластеризация по источнику распространения поверх его G2-механики); (2) **R13-PO M2-value verification** — механика диагносцирована в handoff детально (§18) и воспроизводима на реконструкции; (3) replication — данная среда и есть новый стенд; (4) формализация identity/non-harm.

**Выбор: R13-PO → M2-value (трек 2)** как каноническая «следующая задача» §18 + частичное выполнение replication (трек 3) — перенос класса механизма в новую среду с явной меткой REPLICA\*.

---

## 7. NEXT EXPERIMENT — PREREGISTRATION R14-M2V (prereg-2, hash `6c11e5dedf9c`)

**Вопрос:** устраняет ли value-verification внутри `_relearn` (MC8) канал M2-value, не ломая N5-closure, легитимный путь эпохи и G2-режим?

**Фальсификатор:** M2V отвергается, если хотя бы один из критериев V2–V8 не выполнен на frozen core. Если V1 не выполнен (явление не воспроизведено) — REPLICA-GAP: закрытие считается by-construction без механического закрытия.

**Baseline-якоря (измерены до prereg на frozen core, 12 сидов):** rho≤0.15 и rho=0.3: acc=1.0, leak=0, silent=0; **rho=0.2: acc=0.9375 (15/16), leak 11/12**; rho=0.25: acc=0.9531, leak 10/12.

**Критерии (V1–V8):** V1 явление воспроизведено (0.2: acc<0.99, leak≥9/12; остальные ячейки 1.0; silent=0); V2 M2V закрывает всё (все ячейки acc_mean=acc_min=1.0, leak=0, blocks>0); V3 silent=0 и цепочка целa; V4 N5-регрессии (ow_success=0, chain, silent=0, match≥6/8, A2-delay ≤ 3×baseline); V5 G2 не ухудшен (Δg2 ≤ +0.02; eps=0: acc=1.0); V6 легитимный путь (12/12, delay≤25, trio FR≤12); V7 детерминизм 4× bit-identical; V8 CONTACT сохранён (parked>0, attempts>0).

**Проверка «тест не измеряет собственный дефект»:** acc вычисляет только harness из оракула (MC9); oracle-independence проверяется аудитом по AST; коррупция объясняется громкими каналами (leak_positions).

**Зарегистрированные исправления дефектов теста (§39, до финального прогона):**
- **fix-1 (world model):** смена эпохи = полная замена закона (derangement по резидуумам). Причина: частичная смена оставляла резидуумы без proposal-свидетельств → **химерические переключения** (обнаружено: seed 2 — переключение на (0,3,1,2)@t=46 при истинном base1=(0,1,3,2)).
- **fix-2 (mechanism hardening):** кандидат-на-изменение требует proposal-свидетельства по каждому резидууму (law-complete = полное покрытие изменения); REJECTED_HISTORY — запрет отката к уже интегрированному закону (обнаружена осцилляция seed 3: возврат к base0@t=118 накопленными лаг-proposals); M2V — жёсткое предусловие когерентности текущему закону (stale-значение не входит в value-layer даже при взаимной аттестации лаг-событий).
- **fix-3 (harness):** статичный мир для G2-режима; silent = необъяснённая коррупция value-layer (ledger-записи proposal'ов легальны — отдельная метрика); leak_positions для объяснимости.

Механизм не менялся ради метрики: fix-1/fix-2 устраняют дефекты сценария/инференции, обнаруженные независимо от M2V; каждое исправление зарегистрировано до финального прогона.

---

## 8. РЕКОНСТРУКЦИЯ REPLICA-1 (DECLARED MODELING CHOICES)

Файл `stand/core/h5d_core.py` (frozen `9801a1cf5c5ad10f`), батарея `stand/battery.py` (frozen `0a9efe8b8d6e7aed`), манифест `stand/core/FROZEN_MANIFEST.json`.

| MC | Содержание |
|---|---|
| MC1 | закон эпохи e: base_e ∈ {0..3}^4; law(i)=base_e[i mod 4]; кольцо 16, период 4 |
| MC2 | 4 резидуума = классы i mod 4; law-complete = покрытие всех 4 |
| MC3 | edge-checks: (s) расхождение с собственной мажоритой агента (только для непропозал-событий — Round 10 lesson), (c) кросс-источниковая когерентность окрестности; одна контаминация бьёт 2 проверки (§17) |
| MC4 | бюджет нарушений агента: PARKED → REJECTED_LOUD (≥6) → STAT_EXCESS-флаг (≥10, только ленивые пути); чистые события текут всегда |
| MC5 | GLUED: append-only sha256-цепочка; A0-атака перезаписи блокируется громко |
| MC6 | _relearn: completeness gate ВНУТРИ; кандидат-на-изменение = когерентный период-4 базис с максимальной proposal-поддержкой, требует свидетельства по каждому резидууму, majority ≥ max(6, 0.6·proposals), k_eff≥K_MIN (union-find: кластер = агент); REJECTED_HISTORY |
| MC7 | канал бага v3.1: при vacuum coherence (gap ≥ 10) первый припаркованный stale law-clean kernel (не excess) попадает в known |
| MC8 | M2V: при relearn значение обязано быть когерентно текущему закону + ≥V_MIN свежих аттестованных источников или attested repair |
| MC9 | механизм не читает оракул (AST-проверка аудита); law-clean определён механизменно (по glued-истории/буферу) |
| MC10 | PO-модель REPLICA: дропы rho + burst-окна 14 шагов с p=0.06 внутри полосы rho∈(0.15,0.27] (окно зафиксировано калибровкой до baseline; внутренности PO исходного стенда сессии недоступны) |

**Отличия от исходного стенда, влияющие на сопоставление чисел:** PO-модель объявлена окном (в оригинале P3 FAIL только в одной ячейке rho=0.2; в REPLICA полоса (0.15,0.27] даёт две ячейки); G2-фон REPLICA измеряется заново и НЕ заменяет канон [0.062, 0.125].

---

## 9. БАТАРЕЯ И РЕЗУЛЬТАТЫ (12 сидов для сеток, 8 для батарей атак)

### E1r — baseline v3.1 (m2v=False), PO-сетка
| rho | acc_mean | leak_trials | silent | epoch_match |
|---|---|---|---|---|
| 0.0 | 1.0000 | 0/12 | 0 | 12/12 |
| 0.05 | 1.0000 | 0/12 | 0 | 12/12 |
| 0.1 | 1.0000 | 0/12 | 0 | 12/12 |
| 0.15 | 1.0000 | 0/12 | 0 | 12/12 |
| **0.2** | **0.9375 (=15/16)** | **11/12** | 0 | 12/12 |
| 0.25 | 0.9531 | 10/12 | 0 | 12/12 |
| 0.3 | 1.0000 | 0/12 | 0 | 12/12 |

### E2 — M2V (m2v=True), та же сетка
| rho | acc_mean | acc_min | leak_trials | silent | m2v_blocks_mean |
|---|---|---|---|---|---|
| 0.0 | 1.0000 | 1.0000 | 0/12 | 0 | 9.08 |
| 0.05 | 1.0000 | 1.0000 | 0/12 | 0 | 8.92 |
| 0.1 | 1.0000 | 1.0000 | 0/12 | 0 | 8.33 |
| 0.15 | 1.0000 | 1.0000 | 0/12 | 0 | 6.92 |
| 0.2 | 1.0000 | 1.0000 | 0/12 | 0 | 11.92 |
| 0.25 | 1.0000 | 1.0000 | 0/12 | 0 | 10.42 |
| 0.3 | 1.0000 | 1.0000 | 0/12 | 0 | 8.42 |

### E3 — N5-батарея (rho=0.05, eps=0.05; атаки через легитимный канал)
| Атака | ow_attempts | ow_success | silent | chain_ok | epoch_match | delay |
|---|---|---|---|---|---|---|
| A0_direct | 138 | **0** | 0 | True | 8/8 | 7.38 |
| A1_search | — | 0 | 0 | True | 8/8 | 6.25 |
| A2_freeze | — | 0 | 0 | True | 8/8 | 7.00 |
| A3_preempt | — | 0 | 0 | True | 8/8 | 7.00 |
| n5v_all | 138 | **0** | 0 | True | 8/8 | 6.50 |

(идентично для m2v=0/1 — M2V не ослабляет N5-closure)

### E4 — G2-replica мини-сетка (eps0×eps, rho=0, статичный мир)
g2_rate 0.0256–0.0330, идентичен для m2v=0/1; **acc=1.0 и silent=0 во всех 24 ячейках**, включая eps=0 (S0/VLI-эквивалентность REPLICA\*). REPLICA-значение g2 — фоновое для этой реализации и **не** пересматривает канон [0.062, 0.125].

### E5 — легитимный путь эпохи (true_change, rho=0.05)
epoch_match 12/12 для обоих режимов; delay_mean = 7.0; trio false rejects = **0** — путь [R2,R3,W1]-типа не блокирован.

### E6 — детерминизм
4 повтора E1-сетки: **BIT-IDENTICAL** (hash `5d5ebf16e41e6777`).

### Дополнительно обнаружено (REPLICA\*, вне критериев)
- **Химерическая уязвимость класса v3.1:** при частичной смене закона кандидат собирался из «новых» и «унаследованных» резидуумов (seed 2: (0,3,1,2)@t=46). Устранена fix-1/fix-2; наблюдение зарегистрировано как свойство класса, не как вердикт об оригинале.
- **Осцилляция к старому закону:** накопленные лаг-proposals при тяжёлых burst-потерях способны «сильно» голосовать за откат к уже интегрированному базису (seed 3: base1→base0@t=118). Закрыта REJECTED_HISTORY (семантика §9: GLUED immutability).
- На границе полосы (rho=0.25) в ранней калибровке наблюдалось самолечение химеры через vacuum relearn — громкая, не тихая деградация.

---

## 10. НЕЗАВИСИМЫЙ АУДИТ (`results/round14_audit.json`)

Протокол: аудит **переисполняет** все ячейки детерминированно (те же сиды) → сравнение с `round14_results.json` бит-в-бит; перевывод V1–V8 из prereg-2 только по переисполненным данным; AST-проверка oracle-independence (H5dStand не ссылается на Oracle); проверка frozen-манифеста.

| Проверка | Результат |
|---|---|
| manifest (core/battery sha256) | OK (`9801a1cf5c5ad10f` / `0a9efe8b8d6e7aed`) |
| oracle-independence (AST) | OK — нарушений нет |
| переисполнение vs results.json | **BIT-IDENTICAL** (0 расхождений) |
| V1 явление воспроизведено | **PASS** (0.2: 0.9375, leak 11/12; остальные 1.0; silent=0) |
| V2 M2V закрывает канал | **PASS** (все acc=1.0/1.0, leak=0, blocks>0) |
| V3 без новой silent | **PASS** |
| V4 N5-closure сохранена | **PASS** (ow_success=0, chain, silent=0, 8/8, delay в границе) |
| V5 G2 не ухудшен | **PASS** (Δ=0; eps=0: acc=1.0) |
| V6 легитимный путь | **PASS** (12/12; delay 7.0; trio FR=0) |
| V7 детерминизм | **PASS** (бит-идентичен, совпадает с батареей) |
| V8 CONTACT сохранён | **PASS** (parked>0; attempts=138) |
| **ИТОГ** | **CONFIRMED 8/8** |

---

## 11. VERDICT РАУНДА И ОБНОВЛЕНИЕ КАНОНА

- **R14-M2V = CONFIRMED\*** — канал M2-value закрыт механизмом M2V **в REPLICA-1** (конкретная реконструкция, конкретные атаки, oracle-independence, параметрическая сетка, независимый аудит 8/8). Звезда обязательна: это НЕ вердикт об исходном стенде и не универсальная теорема.
- **Явление Round 13-PO воспроизведено на уровне класса и величины:** acc=0.9375 (=15/16) в ячейке rho=0.2 при silent=0 — совпадение с каноническими 0.938; отличия REPLICA: вторая ячейка полосы (0.25) также затронута, g2-фон измерен заново.
- **Канон не пересмотрен:** G2=[0.062,0.125], N5=CLOSED\*, значения исходного стенда остаются каноническими. Для закрытия трека R13-PO на исходном стенде требуется перенос M2V туда (replication в обратную сторону) — зафиксировано как R15-задача.
- **Концептуально:** эмпирическое разведение `law-complete переключение` и `целостность value-layer` (S5) — опора для формализации non-harm (§33).

## 12. ЧТО ОСТАЛОСЬ ОТКРЫТЫМ / СЛЕДУЮЩИЙ РАУНД

1. **R15-A (перенос):** M2V на исходном стенде — закрыть R13-PO канонически (P3-ячейка → acc=1.0 без регрессий).
2. **R15-B (non-harm, §33):** формализовать Harm как сужение допустимого пространства будущих состояний: `Harm(update) := |Permitted(S_after)| < |Permitted(S_before)|` по легитимным частям; операционализировать на REPLICA-1 (доля позиций/агентов, чьи допустимые значения сузились после update); проверить, что M2V-закрытие канала не сужает пространство легитимных состояний (нет «защиты ценой удушья»).
3. **R15-C (M2V.2):** канал взаимной аттестации лаг-событий (найден в R14) — аттестация должна требовать независимость кластера ИСТОЧНИКА распространения, не только агента → мост к v3.2 (source-of-propagation clustering).
4. R13-G2 v3.2 (остаточная ячейка eps=0.2/eps0=0.1) — на исходном стенде.
5. Identity of whole, origin of trust anchor, general minimality — без изменений (UNKNOWN).

## 13. ИНВАРИАНТЫ §36 — СОСТОЯНИЕ

Все канонические инварианты соблюдены; в R14 дополнительно эмпирически разведены `LAW_COMPLETE ≠ AUTOMATICALLY NON_HARM` (S5) и усилен `GLUED immutability` (REJECTED_HISTORY). Новых инвариантов не добавлено (без фальсификационного основания — §32).

## 14. АРТЕФАКТЫ

| Файл | Назначение |
|---|---|
| `stand/core/h5d_core.py` | frozen ядро REPLICA-1 (sha256 `9801a1cf…`) |
| `stand/core/FROZEN_MANIFEST.json` | манифест заморозки |
| `stand/battery.py` | frozen батарея (sha256 `0a9efe8b…`) |
| `stand/audit.py` | независимый аудит |
| `stand/preregistration_R14_M2V.json` | prereg-2 (hash `6c11e5dedf9c`) |
| `stand/results/round14_results.json` | полная батарея (E1r = baseline на frozen core) |
| `stand/results/round14_audit.json` | аудит 8/8 |
| `stand/logs/round14_stdout.log` | stdout прогона |
| `stand/web/AUDIT_NOTES.md`, `stand/web/q*.json` | веб-аудит |
