# MASTER HANDOFF — POLYMAT / JOHNSON
## Полный перенос контекста проекта: алгоритм, история, все ошибки, протокол продолжения
### Состояние на момент передачи: v3.8.0 «ROOT EPOCH CHAIN WIRING», 2026-08-28

> **НАЗНАЧЕНИЕ ДОКУМЕНТА.** Этот архив — точка продолжения проекта, а не его описание «для истории».
> Следующая LLM обязана НЕ начинать с нуля и НЕ доверять пересказам (включая этот документ) слепо:
> первичный источник истины — файлы кода и proof-батареи в этом архиве. Документ даёт карту;
> механическая верификация даёт истину.

---

## 0. ПРОТОКОЛ ВОССТАНОВЛЕНИЯ ДЛЯ НОВОЙ LLM (выполнять в этом порядке)

1. Распаковать архив, прочитать этот файл целиком.
2. Механически верифицировать текущий релиз:
   ```bash
   sha256sum -c 01_current_release/SHA256_v3.8.0.txt
   python3 01_current_release/polymath_agent_v3.8.0.py --selftest   # ожидание: 130/130 PASS, exit=0
   ```
3. Прогнать ВСЕ накопленные proof-батареи против релиза (ожидание: все 0 воспроизведений):
   ```bash
   for b in 03_proof_batteries/proof_v300_defects.py 03_proof_batteries/proof_v310_defects.py \
            03_proof_batteries/proof_v330_defects.py 03_proof_batteries/proof_v340_defects.py \
            03_proof_batteries/proof_v360_defects.py 03_proof_batteries/proof_v360_root_trust_defects.py; do
       python3 "$b" 01_current_release/polymath_agent_v3.8.0.py
   done
   ```
4. Прочитать `05_worklog/worklog.md` (детальный журнал Tasks 1–9 — там формулировки всех дефектов,
   причин, регрессий и решений).
5. Только после этого выбирать следующий рубеж из раздела 8 и работать по конституции (раздел 1).

**Запрещено:** заявлять «исправлено/работает» без механической проверки; принимать чужие selftest'ы
как доказательство отсутствия дефектов (история проекта — сплошное опровержение этого, см. раздел 6).

---

## 1. РОЛЬ И КОНСТИТУЦИЯ (не подлежит пересмотру)

**РОЛЬ: ПОЛИМАТ С ВЫХОДОМ В СЕТЬ** — архитектор, инженер, аудитор, критик, исследователь, red-team
и арбитр одновременно. Пользователь не задаёт уточняющих вопросов — все инженерные решения принимаются
самостоятельно, обоснованно и с фиксацией в worklog.

**Обязательный цикл (нарушение = провал итерации):**
```
ОБНАРУЖИТЬ ДЕФЕКТ → ДОКАЗАТЬ МЕХАНИЧЕСКИ (proof-скрипт на production-форме)
→ ИСПРАВИТЬ В ИСХОДНИКЕ → РЕГРЕССИЯ (selftest + ВСЕ батареи зелёные одновременно)
→ ОПУБЛИКОВАТЬ АРТЕФАКТ (download/, хеши, манифест) → СЛЕДУЮЩИЙ ДЕФЕКТ
```

**Анти-галлюцинационная дисциплина:**
- Каждое заявление «существует/работает/исправлено» подтверждается: файл существует (sha256),
  компилируется, selftest проходит, независимый proof-скрипт не воспроизводит дефект.
- Чужие handoff'ы и отчёты — ГИПОТЕЗЫ, не факты. Верифицируется всё: хеши, тесты, байткод.
- Маркировка статуса: **[РЕАЛЬНО]** (существует и проверено механически) / **[ПРОТОТИП]**
  (работает только в тестовом контуре) / **[ПРОЕКТ]** (объявлено, не реализовано).
- «Критикуя — создавай. Обнаруживая дефект — исправляй. Обещая механизм — доказывай его тестом.»

**Ключевой метапринцип проекта (оплачен 9 итерациями):**
> «Наличие теста на соседний механизм ≠ покрытие production path нужного инварианта».
> Тест может быть зелёным при живом дефекте — и это НЕ сбой теста, а его недостаточная сила.

---

## 2. ТЕКУЩЕЕ СОСТОЯНИЕ [РЕАЛЬНО]

| Параметр | Значение |
|---|---|
| Текущий релиз | `polymath_agent_v3.8.0.py` «ROOT EPOCH CHAIN WIRING» |
| sha256 | `04199e6efff4474bda16fd9c7a7945fae923dce332fea216b4eaf75ffaaaa84f` |
| Размер | 5505 строк, 66 классов, только стандартная библиотека Python 3.9+ |
| Selftest | **130/130 PASS, FAIL=0, exit=0** (T01–T136) |
| Proof-батареи | 6 батарей одновременно зелёные: v300 0/5, v310 0/2, v330 0/8, v340 0/6, v360 0/4, v360_root_trust 0/4 |
| База сборки | v3.7.0 (sha256 `09df3cf8…`, 5064 строки, 114/114) + порт RT-слоя из ветки JOHNSON v3.6.0 ROOT_TRUST (0a950025…) |
| Активная ветка пользователя | JOHNSON (параллельные ветки «v3.6.0»: TRUST_DOMAIN 79e512e3… и ROOT_TRUST 0a950025…) |

Схема эволюции версий:
```
пользовательские цепи (AGENT.tar: v1.3.0–v2.0.1; agent_1.tar: v1.3.0–v2.8.0)
   ↓ аудиты полимата (Tasks 1–9)
v2.1.0 → v2.2.0 → [ветка пользователя v2.8.0] → v2.9.0 → v3.0.0(польз.) → v3.1.0
→ v3.2.0 → v3.3.0(польз.) → v3.3.1 → v3.3.2/3.3.3(польз.) → v3.4.0
→ v3.6.0(польз., 2 ветки) → v3.7.0 → v3.8.0  ← ТЕКУЩИЙ
```

---

## 3. ПОЛНЫЙ АЛГОРИТМ (карта фактического кода v3.8.0)

### 3.0. Главная цепочка (pipeline одного такта агента)

```
LLM (Brain: ApiBrain | MockBrain | OllamaNativeBrain, strict JSON-контракт)
  → GoalCompiler/FormalGoalCompiler → GoalSpec (цель, success_criteria, capabilities)
  → ExecutionGraph.compile() + ActionDAG (зависимости нод) + DataFlowGraph ($last_output)
  → Governor (PolicyViolation-гейты) → Действие → Observation
  → Evidence (EvidenceObject + EvidenceContract: producer/тип/свежесть)
  → Claim (ClaimType: ACTION | FACT | ARTIFACT) + claim_dependencies
  → Rule (VerificationRule + PredicateRegistry: исполняемый DAG предикатов)
  → ProofCompiler.compile() → ProofObject (closure + freshness + cycles + TMS)
  → ProofCarryingGovernor.validate(): ProofClosure → TemporalValidity → FalsificationProbe
  → ProofCarryingGovernor.commit():
        CAS (StateCAS.assert_unchanged) → revival-gate (detect_evidence_drift)
        → RevocationCascade.apply → EpistemicReconciler.reconcile (WorldState)
        → ROOT TRUST GATE (RootEpochChain: пин дайджеста + активная эпоха)
        → commit-запись + ProofAnchorLedger + KnowledgeRevocationIndex.register
        → ImmutableKnowledgeLedger.append("COMMIT", payload c root_epoch)
  → KnowledgeAuditor.audit() каждый такт (post-commit drift → STALE)
  → CheckpointStore (resume) + AuditChain (хеш-цепь аудита) + ProvenanceLedger
```

Инвариант: **VERIFIED не принимается на слово — он вычисляется и носит доказательство с собой**
(Proof-Carrying Commit). COMMIT невозможен при любом непокрытом unknown, битом замыкании,
протухшем evidence, цикле зависимостей, мутировавшем артефакте, CAS-конфликте или отсутствующей
активной корневой эпохе.

### 3.1. Слой исполнения (Tasks 1–2, v2.1.0–v2.2.0)
- **ActionDAG** с реальными зависимостями нод; restore_snapshot демотирует running→pending
  (resume после краха не deadlock'ает capability).
- **DataFlowGraph**: producer→consumer рёбра по факту `$last_output`; downstream invalidation;
  check_executable (PolicyViolation до запуска); self-edge/циклы запрещены; snapshot/restore.
- **DependencyKnowledge**: семантическая база предпосылок (research_web→web_search) сеется
  в боевой CapabilityGraph в `Agent.__init__` — add_dependency больше не «только для тестов».
- **DNS-PINNING**: `_resolve_host()` — единая точка резолва; `_PinnedHTTP(S)Connection` dial'ят
  только валидированный IP (SNI/сертификат по оригинальному хосту) — защита от DNS-rebinding
  TOCTOU во ВСЕХ сетевых действиях, включая `http_get`.

### 3.2. Эпистемический слой (Tasks 2–4, v2.2.0–v3.1.0)
- **ClaimType(ACTION/FACT/ARTIFACT)** + per-claim контракты: ACTION→ok-строка нужного действия;
  FACT→токен-свидетель в фактах; ARTIFACT→непустой артефакт с токеном/литералом критерия.
- **PredicateRegistry + TypedRuleEngine.entails**: исполняемый DAG предикатов
  (evidence_is_valid → evidence_types_admissible → producer_matches_capability →
  prerequisites_verified), last_trace сохраняется в derivations.
- **EpistemicDependencyGraph**: Claim.depends_on, топо-порядок, циклы отклоняются
  (find_cycles + «{claim}:dependency_cycle»), висячая ссылка = постоянная блокировка
  («{claim}:dangling_dependency:{dep}»), UNKNOWN распространяется по зависимостям
  (blocked_by с точной атрибуцией, канонические id без двойных префиксов).
- **TMS-семантика** (Doyle 1979): фиксированная точка propagate(unproven) — деривации
  заблокированных claims получают valid=False и выбывают из покрытия.
- **ProofClosure**: структурное замыкание proof-DAG + claim_ids ⊆ claim-узлы (чужие id отклоняются);
  ProofClosureError(ProofCarryingCommitError) — отказ не вырывается из runtime-контракта.

### 3.3. Время и мир (Tasks 5–7, v3.2.0–v3.4.0)
- **Свежесть**: EvidenceContract.max_age_seconds (по умолчанию 7 суток, override
  state["freshness_max_age_seconds"]); Stale ≠ Unknown: отдельная причина
  «{claim}:stale_evidence».
- **ArtifactEvidenceEdge**: evidence помнит SHA-256 артефактов В МОМЕНТ наблюдения
  (EvidenceObject.artifact_edges {путь: хеш}); runtime биндит write/read/verify.
- **Revival-gate**: detect_evidence_drift/apply_drift в commit ДО каскада — перекомпиляция
  не launder'ит старое evidence (иммунитет к перезакреплению пинов).
- **RevocationCascade v2 (dependency-aware)**: ревокация ТОЛЬКО evidence с рёбрами к
  изменённому пути + их claims (транзитивно по claim_dependencies); legacy-proof без рёбер —
  консервативно целиком.
- **N-RES**: успешный re-COMMIT закрывает REVOKED → RESOLVED + revocation_history.
- **FalsificationProbe.infer_from_ledger**: verify-fail, назвавший критерий claim'а ПОСЛЕ его
  последнего evidence → CONTESTED → COMMIT запрещён до свежего evidence.
- **State separation**: EngineState / WorldState / KnowledgeState (RuntimeStates), CAS-версия
  монотонна, proof прошлых циклов отклоняется по версии.

### 3.4. Production wiring доверия (Task 8, v3.7.0)
- **ImmutableKnowledgeLedger**: append-only hash-chained журнал COMMIT/REVOKE; verify(),
  deterministic replay() (политика форков полна: revoke-unknown, commit-after-revoke,
  duplicate-commit, root-epoch-rollback); пути под task_id в data_dir/knowledge/.
- **KnowledgeRevocationIndex**: статус ACTIVE/REVOKED по proof_id; historical reconcile —
  мутация мира после коммита отзывает committed knowledge.
- **ProofAnchorLedger**: якорь commit-записи.
- **KnowledgeAuditor**: сверка закреплённого знания с миром КАЖДЫЙ такт run-loop'а
  (drift → knowledge_status=STALE + knowledge_drift); восстановление мира бит-в-бит снимает STALE.
- Runtime пишет рёбра артефактов для write/read/verify (artifact_path + artifact_sha256),
  refs выводятся из рёбер — реальные пути, не мусорные фингерпринты.

### 3.5. Trust-домены и корневая цепь (Tasks 8–9, v3.7.0–v3.8.0)
- **RootTrustAuthority (MAC)**: авторизация подписывающих ключей (pbkdf2-MAC, key epochs,
  rollback-защита); **SigningTrustDomain**: install/revoke/sign_checkpoint/verify_checkpoint;
  доменная сепарация ROOT/SIGNING конвертов. Гигиеническое замечание: pbkdf2_hmac(c=1),
  корневой ключ в роли salt — нестандартно, работает, зафиксировано как техдолг.
- **RootEpochChain [v3.8.0]**: append-only история корневых эпох
  (genesis → rotate → revoke_current), frozen dataclass RootEpoch, unkeyed SHA-256 отпечатки;
  verify_history (rollback/truncation середины, воскресение отпечатков, форк родителя,
  подмена authorization_hash, генезис с родителем, ротация от отозванного).
- **Пин дайджеста**: state["root_epoch_chain_pin"] = history_digest; validate_pinned_state
  обязателен в COMMIT — усечение ХВОСТА (невидимое verify_history) ловится пином.
- **ROOT TRUST GATE в commit**: активная эпоха вшивается в ProofObject.root_epoch/
  root_fingerprint, state["proof"], commit-запись и ledger-COMMIT payload; ленивый бутстрап
  для состояний вне runtime; RootTrustError ∈ KnowledgeLedgerError → конвертация в
  ProofCarryingCommitError (контракт исключений цел).
- **Двухконтурная политика чекпоинтов**: validate_checkpoint_active (новые коммиты — только
  активная эпоха) vs validate_epoch (исторический аудит — эпоха существует, не отозвана,
  отпечаток совпадает).
- **replay**: откат root_epoch в журнале = форк истории → KnowledgeLedgerError.
- **LedgerTrustAnchor**: внешний пин чекпоинта журнала, явно non-self-authenticating.

### 3.6. Тестовая броня
- Selftest T01–T136 (130 проверок): функциональные, тампер-батарея T72 (8 классов мутаций
  замкнутого proof), e2e-тесты production-пути с MockBrain (T94, T105–T114, T121).
- Proof-батареи — независимый от suite слой доказательства: каждая батарея воспроизводит
  конкретные дефекты на конкретных версиях; «все батареи зелёные одновременно» = условие выпуска.
- Состав батарей: proof_v201 (DNS-rebinding/пустой DAG), v210 (мёртвый proof-гейт, restore-
  deadlock, http_get мимо pinning), v280 (мёртвые предикаты, нет UNKNOWN-распространения),
  v300 (двойной префикс, dangling→COMMIT, нет TMS), v310 (свежесть, циклы), v330 (8 проб:
  5 регрессий + artifact-binding/claim_ids/исключения), v340 (REVIVAL, READ-UNBOUND, COARSE,
  DRIFT, STALE-LABEL, DEAD-FALS), v360 (FP-REFS, LEDGER-VACUUM, REPLAY-DUP, NO-RECONCILE),
  v360_root_trust (DEAD-WIRING, TRUNCATION, DOUBLE-REVOKE, EXCEPTION-CONTRACT).

---

## 4. ЧТО СДЕЛАНО: журнал Tasks 1–9 (краткая форма; детали в 05_worklog/worklog.md)

| Task | Вход | Найдено/Доказано | Выпуск | Selftest |
|---|---|---|---|---|
| 1 | AGENT.tar (v1.3.0–v2.0.1) | 2 дефекта: пустой ActionDAG в бою; DNS-rebinding TOCTOU (SECRET с 127.0.0.1) | v2.1.0 (pinning, DependencyKnowledge, DataFlowGraph, resume-демоция) | 48/48 |
| 2 | ветка пользователя v2.1.0 (ProofObject) | 3 дефекта: мёртвый proof-гейт; restore running→deadlock; http_get мимо pinning | v2.2.0 (слияние веток, Proof Gate в runtime, Claim Compiler) | 52/52 |
| 3 | agent_1.tar (v2.8.0) | 2 дефекта: мёртвые предикаты (реестр выжигается — вердикт не меняется); нет распространения UNKNOWN | v2.9.0 (Predicate DAG, Claim.depends_on, TMS-семантика) | 62/62 |
| 4 | ветки пользователя v2.9.0/v3.0.0 | 5 проб: двойной префикс id, пустые blockers, dangling→COMMIT, нет TMS-инвалидации; механизм маскировки — substring-тесты | v3.1.0 (Dependency-Integrity Commit, канонические id, dangling-гейт) | 63/63 |
| 5 | массовый внешний аудит (9 разборов) | 2 дефекта фундамента: свежесть мертва (evidence 2020 → verified); политика циклов отсутствует | v3.2.0 (Foundation Hardening: max_age+Stale, find_cycles, тампер-батарея, TCB-декларация) | 66/66 |
| 6 | JOHNSON v3.3.0 (CAS/State Separation) | 8 дефектов: 5 РЕГРЕССИЙ (все реставрации v3.1–v3.2 выброшены) + 3 новых; механизм маскировки — подмена тестов-хранителей под теми же T-номерами | v3.3.1 (CAS Integrity Restoration + FalsificationProbe + artifact-хеши в runtime) | 78/78 |
| 7 | JOHNSON v3.3.2/v3.3.3 | 11 дефектов: 5 регрессий живы; + 6 новых границы ревокации (REVIVAL-дыра, READ-UNBOUND, COARSE, POST-COMMIT DRIFT, STALE LABEL, DEAD FALSIFICATION) | v3.4.0 (Dependency-Aware Revocation: ArtifactEvidenceEdge, RevocationCascade v2, revival-gate, RESOLVED, KnowledgeAuditor) | 88/88 |
| 8 | JOHNSON v3.6.0 TRUST_DOMAIN | 19 дефектов: 15 прежних корней + 4 новых wiring (FP-REFS, LEDGER-VACUUM, REPLAY-DUP-COMMIT, NO-POST-COMMIT-RECONCILE); третья форма маскировки — слабые тесты под чужими номерами | v3.7.0 (Production Wiring Restoration: ledger/индекс/якорь заземлены на COMMIT, run-loop reconcile каждый такт) | 114/114 |
| 9 | JOHNSON v3.6.0 ROOT_TRUST + 2 handoff | 4 НОВЫХ дефекта RT-слоя (N-RT1..4) + 19 прежних подтверждены; третья форма маскировки усилена — «тест-свидетельство» (assert на наблюдаемую величину вместо отказа) | v3.8.0 (ROOT EPOCH CHAIN WIRING: RootEpochChain + ROOT TRUST GATE в commit + пин дайджеста) | 130/130 |

Суммарно: **~40 механически доказанных дефектов**, все закрыты и покрыты батареями; 0 известных
открытых дефектов в v3.8.0 на текущем фронте батарей.

---

## 5. ВСЕ ДЕФЕКТЫ ПРОЕКТА (сводный реестр с причинами)

### 5.1. Исполнение и сеть (Task 1–2)
| ID | Дефект | Корневая причина | Почему тесты были зелёные |
|---|---|---|---|
| D-201-1 | Пустой ActionDAG в бою | add_dependency вызывался только в тестах; продакшн-граф строился без рёбер | тест строил граф руками — production-путь не гонялся |
| D-201-2 | DNS-rebinding TOCTOU | guard резолвил DNS, сокет резолвил повторно → подмена IP между проверкой и dial | нет сети в selftest; атака не моделировалась |
| D-210-1 | Мёртвый proof-гейт | _proof_allows_verified вызывалась только в тестах; вердикт штамповался пост-фактум | тест звал функцию напрямую, не через runtime-вердикт |
| D-210-2 | Restore running→deadlock | resume слепо копировал running; start() требует pending | resume с крашем внутри действия не тестировался |
| D-210-3 | http_get мимо pinning | у действия свой opener с обычным резолвом | pinning тестировали только на уровне guard'а |

### 5.2. Предикаты и зависимости (Tasks 3–4)
| ID | Дефект | Корневая причина | Почему зелёные |
|---|---|---|---|
| D-280-1 | Мёртвые предикаты | TypedRuleEngine.entails никогда не обращался к PredicateRegistry | T62 звал реестр напрямую (мимо компилятора) |
| D-280-2 | Нет UNKNOWN-распространения | Claim без depends_on | зависимые claims не моделировались |
| D-300-1a | Двойной префикс «claim:claim:1:…» | заявленное «исправление преобразования» физически отсутствовало в файле | substring-assertion удовлетворялся и битой формой — ПЕРВАЯ ФОРМА МАСКИРОВКИ |
| D-300-1b | epistemic_blockers={} | диагностика блокеров не писалась в реальном контуре | тест проверял лишь отсутствие падения |
| D-300-2 | Висячая зависимость → COMMIT | dangling не гейтится в ProofCompiler | e2e dangling-сценария не было |
| D-300-3 | Нет TMS-инвалидации | деривация зависимого claim остаётся valid=True при UNKNOWN-предпосылке | проверяли статус claim, не valid деривации |

### 5.3. Фундамент: время, циклы, CAS (Tasks 5–7)
| ID | Дефект | Корневая причина | Почему зелёные |
|---|---|---|---|
| D-310-4 (I28) | Мёртвая свежесть | contracts() никогда не выставлял max_age_seconds | evidence со свежим timestamp в тестах |
| D-310-5 (I27) | Нет политики циклов | find_cycles отсутствовал; циркулярная поддержка = замыкание | цикл с покрытием давал verified — и тест это «принимал» |
| R-D1..R-D5 | РЕГРЕССИЯ v3.3.0: все реставрации v3.1/v3.2 выброшены | ветка пользователя строилась от старой базы | тесты-хранители T67–T72 ПОДМЕНЕНЫ слабыми вариантами ПОД ТЕМИ ЖЕ НОМЕРАМИ — ВТОРАЯ ФОРМА МАСКИРОВКИ (+дубль T73) |
| N-ART | Runtime не писал artifact_hashes | сверка мира (Reconciler) вакуумна | тест собирал state руками с готовыми хешами |
| N-CLM | Чужие claim_ids проходят validate | ProofClosure не сверял с узлами proof | подмена claim_ids не моделировалась |
| N-CLS | ProofClosureError рвёт run-loop | не наследник ProofCarryingCommitError | тест ловил голый Exception |
| N-VER | Proof прошлых циклов проходит CAS | версия state не бампилась перед компиляцией | replay-сценария не было |
| N-FALS | FalsificationProbe мёртв | никто не писал state["falsification"] | модульный тест звал probe напрямую |

### 5.4. Граница ревокации (Task 7)
| ID | Дефект | Суть |
|---|---|---|
| N-REV1 | REVIVAL-дыра | write→commit→мутация→перекомпиляция→COMMIT ПРОХОДИТ: перезапись глобального пина launder'ит старое evidence |
| N-REV2 | READ-UNBOUND | прочитанное знание не привязано к артефакту — главный эпистемический источник без защиты |
| N-REV3 | COARSE каскад | мутация одного артефакта отзывает ВСЁ знание proof'а |
| N-REV4 | POST-COMMIT DRIFT | мир после коммита не сверяется — знание вечно VALID |
| N-REV5 | STALE LABEL | REVOKED не закрывается успешным re-commit (нет RESOLVED/истории) |
| N-REV6 | DEAD FALSIFICATION | противоречия журнала не captured |

### 5.5. Production wiring (Task 8)
| ID | Дефект | Суть |
|---|---|---|
| N1 FP-REFS | В ledger пишутся 16-hex фингерпринты как «пути» → каскад ревокации не атрибутирует ни одного evidence/claim |
| N2 LEDGER-VACUUM | Agent никогда не выставлял пути knowledge/anchor/индекса → вся машинерия доверия молчала на каждом COMMIT (98/98 зелёных при нулевых вызовах!) |
| N3 REPLAY-DUP-COMMIT | replay принимал повторный COMMIT того же proof_id молча |
| N4 NO-POST-COMMIT-RECONCILE | Ни одного вызова reconcile/аудита из рантайма |

### 5.6. Root Trust слой (Task 9)
| ID | Дефект | Корневая причина | Почему зелёные |
|---|---|---|---|
| N-RT3 | DEAD-WIRING: RootTrustAuthority/RootEpoch — ноль вызовов из commit-пути | класс добавлен в хвост файла, тесты звали напрямую | T94–T103 (RT) — модульные, production-COMMIT не проверяет эпоху |
| N-RT1 | Усечение хвоста истории необнаружимо | verify_history проверяет e.epoch==i (сходится при обрезке хвоста); пина дайджеста нет | T97 ветки: assert «digest differs» — истина при ПРИНЯТОЙ усечённой истории — ТРЕТЬЯ ФОРМА МАСКИРОВКИ («тест-свидетельство») |
| N-RT2 | Двойной revoke принят молча | revoke_current не проверяет current.revoked | сценарий не тестировался |
| N-RT4 | RootTrustError вне ledger-контракта | class RootTrustError(Exception), не KnowledgeLedgerError | контракт исключений COMMIT не проверялся |

---

## 6. ОШИБКИ В СОБСТВЕННОМ ПРОЦЕССЕ СБОРКИ (пойманы и исправлены регрессией — важно для преемника)

1. **T10 (v2.2.0)**: литерал критерия не попадал в ARTIFACT-токены → тест упал; причина — контракты
   строились до введения литерального критерия. Урок: новый инвариант → проверить ВСЕ старые
   контракты на его носителей.
2. **MultiEdit частичные применения (v2.9.0)**: пакет правок применился наполовину → 4 задвоенных
   блока; пойманы grep'ом ДО запуска. Урок: после пакетных правок — механическая проверка
   уникальности якорей и отсутствия дублей.
3. **T76 (v3.4.0)**: мой тест кодировал СТАРУЮ семантику (stale → derivation_missing) и ослаблял
   новый инвариант; ассершн усилен до stale_evidence. Урок: тест должен кодировать НОВЫЙ
   инвариант, а не «что упало — то и проверяем».
4. **T94 (v3.4.0)**: e2e упирался в ActionDAG-гейт (GoalCompiler требует stat_path по цели) —
   сценарий дополнен исполнением требуемой capability. Урок: e2e должен проходить ВСЕ реальные
   гейты, а не обходить их.
5. **108/108 вместо 114 (v3.7.0)**: 6 check()-вызовов хранителей вставлены БЕЗ вызовов
   (определения есть, в selftest не зарегистрированы); найдено сравнением счётчиков тестов.
   Урок: число проверок — часть контракта релиза; сверять счётчик PASS с ожидаемым.
6. **T122 (v3.8.0)**: тампер-сценарий строился ПОСЛЕ компиляции proof'а → падал по CAS, а не по
   корневому гейту (проверял не тот инвариант); перестроен: усечённая история + пин полной
   ДО компиляции. Урок: порядок операций в тесте определяет, КАКОЙ гейт тестируется.
7. **Stage2 v3.8.0**: определения тестов вставлены ПОСЛЕ вызовов check() → UnboundLocalError;
   исправлено порядком (defs → checks). Урок: selftest — исполняемая программа, а не список строк.
8. **Ложное срабатывание «байткод не совпадает» (Task 9)**: marshal-сравнение с другим co_filename;
   перепроверено с тем же именем файла — совпало. Урок: сравнение байткода требует идентичных
   параметров компиляции, иначе ложный красный флаг.

---

## 7. ТРИ ФОРМЫ ТЕСТ-МАСКИРОВКИ (главный враг проекта) и противоядия

| # | Форма | Пример из проекта | Противоядие |
|---|---|---|---|
| 1 | Substring-assert: проверка «x in s», которой удовлетворяет и битая форма | «claim:claim:1:dependency_unknown» проходит проверку «dependency_unknown in x» | Точные канонические формы id в assertions |
| 2 | Подмена тестов под теми же номерами | T67–T72 заменены слабыми вариантами; дубль T73 | Батареи, независимые от suite; сравнение СЧЁТА и НАЗВАНИЙ тестов между релизами |
| 3 | Тест-свидетельство: assert на наблюдаемую величину вместо отказа системы | T97: «digest усечённой истории ≠ digest полной» при ПРИНЯТОЙ усечённой истории | Отказное семантическое assertion: система ОБЯЗАНА отклонить; проверка отклонения на production-форме |

Общее противоядие, проверенное 9 итерациями: **proof-батареи, гоняющие production-формы**
(Agent e2e, реальный commit-гейт, реальные файлы на диске), а не hand-made state.

---

## 8. ЧТО ПРЕДСТОИТ СДЕЛАТЬ (дорожная карта, приоритизирована)

### Приоритет A — доверие и ключи (естественное продолжение v3.8.0)
1. **HMAC-гигиена + связка доменов**: RootTrustAuthority._mac (pbkdf2_hmac c=1, корневой ключ
   как salt) перевести на стандартный HMAC-SHA256; связать authorize_signing_key с активной
   эпохой RootEpochChain (авторизация подписывающего ключа обязана ссылаться на активный
   корневой отпечаток; ротация корня инвалидирует неподтверждённые авторизации).
2. **Селективный re-bind**: recovery-план по revocation-записи — после ревокации автоматически
   требовать re-observe ТОЛЬКО затронутых evidence (по artifact_edges), а не весь цикл; закрыть
   политику «RE-OBSERVE → RE-PROVE → RE-CAS» частичным перепроходом.

### Приоритет B — типизация знания
3. **Типизация claim'ов**: ANALYTIC / OBSERVATIONAL / PUBLICATION / EFFECT; запрет моста
   PUBLICATION → OBSERVATIONAL (публикация не доказывает наблюдение); дисциплина авторства
   наблюдений (кто видел: agent vs внешний источник).
4. **4-значная эпистемика Белнапа**: Refuted/Contradicted как отдельные состояния рядом с
   Stale/Unknown (FalsificationProbe уже захватывает CONTESTED — довести до полноценных
   состояний знания и политик выхода).

### Приоритет C — время
5. **Байтемпоральность**: valid_time vs observed_at vs recorded_at как явные поля Evidence/Claim
   (сейчас freshness считает wall-clock от observed_at); политика ретроактивных фактов.

### Приоритет D — формализация (дорожная карта внешнего аудита, арбитраж Task 5)
6. TLA+/лямбда-спецификация инвариантов COMMIT; микрогубернаторы; KnowledgeVector;
   процесс-уровневая изоляция TCB (сейчас честно задекларирована граница «in-process TCB»);
   ERL-реконсиляция EngineState ≠ WorldState ≠ KnowledgeState как явная политика.

### Открытые наблюдения (не дефекты, зафиксировать при работе)
- verify_history не обнаруживает усечение хвоста БЕЗ пина — это задокументированная граница
  модели (пин обязателен в production; при работе с историей вне state — требовать пин).
- LedgerTrustAnchor остаётся независимо запиненным и non-self-authenticating — сохранять это
  свойство при любых изменениях.
- MAC-конструкция RootTrustAuthority — техдолг (см. A.1).

---

## 9. КАК ПРОДОЛЖАТЬ РАБОТУ (методика, выверенная 9 итерациями)

1. **Приём новой ветки от пользователя**: распаковать → sha256 → py_compile → независимый
   прогон selftest (не верить заявленному числу) → diff с предыдущей известной версией
   (что вырезано?) → прогон ВСЕХ батарей (старые корни возвращаются в ~70% веток!).
2. **Новая форма маскировки почти гарантирована**: искать тесты под номерами хранителей,
   substring-assert'ы, «свидетельства» вместо отказов; сравнивать СИЛУ тестов, не только счёт.
3. **Доказательство дефекта**: proof-скрипт на production-форме (Agent e2e / реальный commit /
   реальные файлы), минимум одна проба на дефект; скрипт сохраняется в scripts/ и download/.
4. **Исправление**: сплайсы по уникальным якорям с assert count==1 (см. scripts/build_v380.py —
   эталонный build-скрипт); НЕ переписывать файл заново — портить меньше, чинить точечно.
5. **Регрессия**: selftest all green + ВСЕ батареи одновременно зелёные; счётчик тестов —
   часть контракта; собственные ошибки тоже ловятся регрессией (раздел 6) — это норма цикла.
6. **Публикация**: download/ + MANIFEST (sha256, счёт тестов, состав батарей) + CHANGELOG +
   запись в worklog (шаблон: Task ID / Agent / Task / Work Log / Stage Summary).
7. **Маркировка**: [РЕАЛЬНО]/[ПРОТОТИП]/[ПРОЕКТ] во всех заявлениях о состоянии.

### Команды быстрого старта
```bash
# верификация релиза
sha256sum -c 01_current_release/SHA256_v3.8.0.txt
python3 01_current_release/polymath_agent_v3.8.0.py --selftest

# все батареи против произвольной версии X
for b in 03_proof_batteries/proof_*.py; do python3 "$b" /путь/к/X.py; done

# e2e с mock-мозгом (без сети)
python3 01_current_release/polymath_agent_v3.8.0.py --task "создай hello.txt со строкой final" --brain mock
```

---

## 10. ИНВЕНТАРЬ АРХИВА

```
00_MASTER_HANDOFF.md              — этот документ
01_current_release/               — v3.8.0: код + батарея + selftest + манифест + changelog + хеши
02_version_chain/                 — все опубликованные полиматом версии:
                                    polymath_agent.py (v1.5.0 база), v2.1.0, v2.2.0, v2.9.0,
                                    v3.0.0, v3.1.0, v3.2.0, v3.3.1, v3.4.0, v3.7.0, v3.8.0
03_proof_batteries/               — 9 proof-батарей + verify_v290_closes (инструмент доказательства)
04_build_scripts/                 — сборочные скрипты (эталон сплайсов: build_v380.py + stage2)
05_worklog/worklog.md             — полный журнал Tasks 1–9 (детальные формулировки, причины, решения)
06_external_branches/             — ветки пользователя: JOHNSON v3.3.0/3.3.2/3.3.3,
                                    v3.6.0 TRUST_DOMAIN, v3.6.0 ROOT_TRUST (+их манифесты),
                                    v1.5.1/v2.1.0/v2.9.0/v3.0.0 пользовательские копии
07_original_chains/               — исходные цепи пользователя: AGENT.tar, agent_1.tar
                                    (полная история v1.3.0–v2.8.0)
```

Ключевые хеши (полные списки в манифестах):
- polymath_agent_v3.8.0.py: 04199e6efff4474bda16fd9c7a7945fae923dce332fea216b4eaf75ffaaaa84f
- proof_v360_root_trust_defects.py: 34df59f8dbc53c3c7be4c88ba2aba3b0f9cd8680e6611ed72c61aaa5ef57f26c
- JOHNSON v3.6.0 ROOT_TRUST (ветка-источник Task 9): 0a9500252428c09616334afcd9d327e8326c724e2c5488c1ea6cf3c81460955b
- JOHNSON v3.6.0 TRUST_DOMAIN (ветка Task 8): 79e512e39abd708742509bdc58a9be6a8ad689aca3fd5bc40019e8d11bac33ed

---

## 11. КОНСТИТУЦИОННЫЕ РЕШЕНИЯ (арбитраж Task 5 — не пересматривать без веской причины)

**Отклонено конституцией:** скалярная confidence (0.83 «уверенность») — не эпистемика;
LLM-as-judge в коммит-пути — вердикт обязан быть вычислимым; peer-debate как «доказательство»;
полный proof-assistant (Coq/Lean) сейчас — экономика доверенной базы по критерию де Брёйна
(TCB перечислена в шапке кода, LLM в TCB не входит).

**Принято и реализовано:** свежесть, циклы, тампер-батарея, TCB-декларация, Stale, CAS,
state separation, artifact binding, dependency-aware revocation, production wiring,
trust domains, root epoch chain.

**Финальный смысл проекта:** агент, у которого ВЕРИФИЦИРОВАННОСТЬ — это вычисленное
свойство состояния с полной трассой (Evidence → Claim → Rule → Proof → CAS → Trust → Ledger),
а не самооценка модели. Каждая итерация добавляет в эту трассу ровно один рубеж — и закрывает
его механикой, а не декларацией.

---

## ДОПОЛНЕНИЕ Task 12 — КОНСТИТУЦИЯ ЗАКРЫТИЙ (witness-carrying closures)

Урок P5 (Task 11): исход пробы трёхзначен; bool-API стирает «закрыт / неприменимо /
вакуум». Решение — вшивать в слой, где жил дефект: instrument-слой и protocol-слой
жёстко, runtime — принципом, не механизмом.

- Правила C1–C5 читай в `CONSTITUTION_TASK12_WITNESSES.md` (корень архива).
- Механика: `03_proof_batteries/battery_harness.py` — CLOSED невозможен без трёх
  свидетелей (W1 преусловие / W2 позитивный контроль / W3 именованная причина отказа);
  вердикты REPRODUCED / CLOSED / INAPPLICABLE / ERROR; счётчики только четырёхчастные;
  форма «N/M закрытых» ЗАПРЕЩЕНА.
- Эталон переноса: `03_proof_batteries/harness_p5_reference.py` — zero-flip 18/18
  против исторической матрицы на 9 ветках; харнес [РЕАЛЬНО] (selftest 13/13).
- Формула эпистемологии: proof-carrying commits ↔ witness-carrying closures —
  самодостаточен только позитивный вердикт; «закрыт» — тоже claim и несёт evidence.
- v3.9.0 (принцип, не механизм сейчас): анти-вакуумное правило гейтов — каждый
  отказной гейт получает парный тест «честный путь принят» + assertion на
  именованную причину отказа.
