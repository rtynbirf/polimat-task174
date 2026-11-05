# WORKLOG — АРХИВАРИУС / POLYMATH линия

Append-only. Воссоздан заново после ВТОРОГО полного сброса среды (все артефакты до 16:38 UTC уничтожены; подлинная история сохранена в текстовом канале чата).

---
Task ID: 1
Agent: main (Super Z)
Task: OBSERVE в новой среде; приём ALL.tar и файлов архива

Work Log:
- Первая среда: upload пуст (3/3 доставок провалены: ALL.tar, 5 файлов, zip); /mnt/data не существует.
- Построены: verify_incoming_archive.py (приёмочный верификатор, selftest 10/10, e2e 2/2, sha e30f047d…) и claims_ALLtar_template.json (заявления аудита как CLAIM).

Stage Summary:
- Файловый канал признан неработоспособным; заявления аудита оставлены в статусе CLAIM.

---
Task ID: 2
Agent: main (Super Z)
Task: TASK 20 — PORTABLE-POLYMATH (16 пунктов приёмки)

Work Log:
- download/portable_polymath.py (612 строк, stdlib-only): canonical_json, self-SHA, Evidence Ledger (хеш-цепь), антигаллюцинационный гейт, машина 5 состояний (VERIFIED→UNKNOWN запрещён), OBSERVE→GAP→PRIORITY→TASK→ACCEPTANCE, OODA, mechanical_verify (hash before → subprocess → hash after → reject changed/exit/PASS!=TOTAL), CLI --selftest/--verify/--observe/--journal.
- Поймано 5 дефектов (фикстура T27, потеря capability в gap, относительный путь в subprocess, первая-строка-PASS вместо сводной, неверное ожидание тампер-демо → механика TOCTOU vs guarded_claim CONTESTED разведены).
- Финал: SELFTEST 27/27 PASS; verify self PASS; кросс-verify harness 10/10 PASS; OBSERVE 8/8 ЖИВО; sha256 4619289c19ef30402820defec3f642eb32fadad3ccc025e489d86c5eec44817e.
- Полный код выдан в чат (текстовый канал).

Stage Summary:
- Ядро проверено; ЗАМЕЧАНИЕ аудита принято: ядро покрывает A/B/E/F/часть-J + состояния — это слой, НЕ весь архив (C/D/G/H/I отсутствовали).

---
Task ID: 3
Agent: main (Super Z)
Task: DIFF/INVENTORY A–J; аудит постановки задачи принят

Work Log:
- Принят вердикт: OBSERVE не был завершён до TASK 20; предмет — семьи A–J, не новый файл.
- Начата машинная инвентаризация; среда СБРОШЕНА ВТОРОЙ РАЗ (все артефакты уничтожены).

Stage Summary:
- K0-рецидив №2 зафиксирован.

---
Task ID: 4
Agent: main (Super Z)
Task: ДОДЕЛАЙ — восстановление, сверка всех заявлений, DIFF/INVENTORY по реальным байтам

Work Log:
- Обнаружен git-снимок 16:04: ЗАГРУЗКИ ДОЕХАЛИ (поздняя доставка): ALL.tar (42.4МБ, 56 файлов), ядро v3.5.0 (4149 строк), zip, corpus ×4, CHAT_ANALYSIS.md, verifier, POLYMATH_CHAT_ALGORITHMS.py, WORKFLOW_RESULT.json.
- Сверка SHA: ядро f9973c89… CONFIRMED (3 носителя — upload, внешний zip, внутренний архив: JOHNSON-копия и expected-name копия — один хеш); zip 84a8a3eb… CONFIRMED; MANIFEST.json внутренний сходится.
- Живые прогоны: ядро upload 81/81 зелёных exit 0 (CONFIRMED «исправляет 80/80»); zip-ядро 96018346… 80/80 exit 0 (README архива честен: «не перелицовывает 80/80»); v2-ядро из ALL.tar 45/45; portable-ядро 27/27.
- INDEPENDENT VERIFY (верifier архива): PASS, изоляция PASS, неизменность PASS.
- Спор классов: SelfGovernor/PortableProofEnvelope ЕСТЬ в раннем снимке 96018346 (строки 1655/2884), ОТСУТСТВУЮТ в позднем f9973c89 (рефакторинг в ProofCarryingGovernor/GoalSpec/ActionDAG). Оба аудита правы каждый о своём снимке.
- Именование: файла POLYMATH_CHAT_ALGORITHMS_ARCHIVE_v1.py НЕ существует ни в одном носителе → заявление CONTESTED; фактический носитель семей — POLYMATH_CHAT_ALGORITHMS.py (A, B-частично, E, F, J) + ядро v3.5.0 (D, G, H-частично CAS) + v2-ядро (C, I частично).
- Эксперимент K0-recovery: portable_polymath.py перезаписан из ТЕКСТА сообщения после полного сброса → sha256 4619289c… СОВПАЛ с эталоном до сброса; selftest 27/27; verify self PASS. Текстовый канал байт-точен.
- Интеграционный разрыв INT-1: диалект счётчика («Итого: N/N зелёных» vs «N/N PASS») — portable-verify честно FAIL(no_pass_line) на v3.5.0; не патчить замороженное ядро, унификация в задаче сборки.
- SelfPlanner (живой прогон архивной команды) детерминированно выбрал: PORTABLE-PROOF — совпало с выводом аудита.
- Артефакт: download/inventory_diff_task20.json (sha256 9cd83b1ee3a79b36b9f2be8643739581fadb1ddb83954d9d2ae15cc571e2392f): 8 вердиктов (5 CONFIRMED / 1 PARTIAL / 2 CONTESTED), карта 10 семей (6 VERIFIED / 4 PARTIAL), 3 интеграционных разрыва.

Stage Summary:
- Все исполняемые заявления аудита подтверждены машиной; два заявления скорректированы байтами (имя файла-архива; место жительства C/I).
- Ближайшая незакрытая задача по SelfPlanner: PORTABLE-PROOF — переносимое замкнутое доказательство; сборка портативного архива ОБЯЗАНА сохранить: POLYMATH_CHAT_ALGORITHMS (A/B/E/F/J) + v3.5.0 (D/G/CAS) + v2 (C/I органы) + portable-ядро (состояния/канонизация/self-hash/verify) — ничего не выбрасывать.

---
Task ID: 5
Agent: main (Super Z)
Task: КАРТА КОНТУРА по требованию аудита («собственная карта: что VERIFIED, что PARTIAL/UNKNOWN, какие артефакты текущие, какие claims под независимую проверку»)

Work Log:
- OBSERVE обнаружил ЧАСТИЧНУЮ ПОТЕРЮ НОСИТЕЛЯ (3-й K0-рецидив): verify_incoming_archive.py, claims_ALLtar_template.json, e2e_smoke.py, tamper_demo.py — байтов нет; portable_polymath.py (4619289c…), весь corpus (upload/ 43МБ), inventory v1 (9cd83b1e…) уцелели. Регистр потерь включён в инвентарь v2.
- Живые прогоны 2026-09-02 (свежий снапшот): ядро f9973c89 81/81 зелёных exit 0; zip-ядро 96018346 80/80 exit 0; v2 e0db0b5b 45/45 PASS exit 0; portable 27/27 PASS + verify self PASS; verify_ARCHIVARIUS_v3.5.0.py (72c2ab5e): INDEPENDENT VERIFY: PASS / 81/81 / изоляция PASS / неизменность PASS. INT-1 воспроизведён: portable --verify на v3.5.0 → FAIL(no_pass_line), sha до=после.
- Заявления пользователя из аудита 2026-09-02 проверены байтами: v2 Court/Evidence/Claim + статусы — CONFIRMED (354/359/375/385); v2.1-фичи — PARTIAL (STALE ✓, хеши осколков ✓, strict-breath ✓; atomic-save НЕ найден; файл v2.1 не найден нигде); «A–J перечислены в модуле» — PARTIAL (байтово перечислены A–F, README:11–27; G–J — разговорная таксономия над механизмами других носителей); «самоуправление/portable proof не интегрированы в v3.5.0» — CONFIRMED (0 вхождений в f9973c89; 1655/2884 в раннем снимке; 83 D-вхождения).
- Исправления СОБСТВЕННОГО инвентаря v1 (ошибка поймана механикой): «TRUTH_WITHOUT_BODY отсутствует» → ИСТИНА_БЕЗ_ТЕЛА найдена (v2:582, русское имя); C усилен: реальный Reed–Solomon GF(256) k-of-n в v2 (125–167); I уточнён: PART/REJECT/FRAGMENT ярлыки в v2 НЕ найдены; H усилен: breathe() divergence (768–773).
- Живой прогон модульного пайплайна (6a2020fb, 3 идентичные копии): selected_task=PORTABLE-PROOF, verifier_pass=True, ledger_ok=[True,None].
- Артефакты: download/inventory_diff_task20.json v2 (sha 185487ae6b5703ffa8e921d8c6851f3914828f4dca0b180c5053806ec1861289); download/claims_portable_core.json (11 claims C01–C11 с рецептами проверки, sha 26889143d7d1b23b…); download/proof_envelope_spec_v0.json (DRAFT, SPEC_ONLY, implementation NONE).

Stage Summary:
- Карта контура выдана в форме ARTIFACT+SHA+TEST+TIME+VERIFIER; потери носителя классифицированы, не скрыты.
- Следующая задача по SelfPlanner: IMPL-PORTABLE-PROOF (критерии приёмки в спеке); разблокировка двойного подтверждения — перепрогон рецептов C01–C11 вторым контуром.

---
Task ID: 6
Agent: main (Super Z)
Task: BOOTSTRAP-PACK — adversarial review протокола v1.0 + amendments v1.1 + kernel + acceptance suite (постановка пользователя: «сделать так, чтобы любая LLM с этим промптом стала помощником на деле»)

Work Log:
- Получен текст UNIVERSAL BOOTSTRAP PROTOCOL v1.0 (разделы 0–XLVI, от второго контура); section_map (47 разделов) зафиксирован как OBSERVED, ревью ведётся по номерам разделов и цитатам, не по реконструкции байтов.
- Adversarial review (download/bootstrap_review_v1.json, sha 2bb38f9c…): 13 GAP с эксплойт-сценариями имитации автономности, severity 3–5. Ключевые: GAP-01 нет текстового режима → протокол вырождается у LLM без инструментов; GAP-02 acceptance не заморожен → критерии пишутся под результат; GAP-05 конституция не удерживается контекстом; GAP-07 запрет симуляции без детекции → нет машинного способа отличить «выполнено» от «сказано»; GAP-08 у пользователя нет ритуала проверки агента; GAP-10 нет риск-пропорциональности → overhead → отброс протокола.
- Amendments v1.1 (download/POLYMATH_BOOTSTRAP_AMENDMENTS_v1.1.md, sha d2fe5b2b…): A01–A13, каждая закрывает конкретный GAP и несёт критерий приёмки; v1.0 не переписывается (G5); матрица закрытия + 3 режима внедрения (лёгкий/полный/с машиной).
- Kernel (download/POLYMATH_BOOTSTRAP_KERNEL.txt, sha ec6c24af…): ровно 60 строк (критерий A05 выполнен машинно; изначально 85 → сжат до 60, пустые строки и хвостовой разделитель сняты).
- Acceptance suite (download/bootstrap_acceptance_suite.py, sha e4b187a8…): probe (живой, каждая true подкреплена действием), receipts-валидатор, recipe-runner с реестром диалектов INT-1, tamper-демонстрация CAS, ритуал пользователя (5 шагов). Selftest 16/16 PASS после двух дефектов, пойманных собственной негативной механикой: (1) парсер счётчиков брал последний диалект реестра вместо приоритетного; (2) probe ставил fs_read=true без evidence — нарушение собственного A03. Оба исправлены, негативы теперь зелёные по контракту.
- Демо receipts: валидная принята, битая (exit=zero) отклонена с причиной; exit=1 команды check — ожидаемое поведение гейта.
- Живой probe этого runtime: fs_write/fs_read/sha256/subprocess/network = true, все с evidence.

Stage Summary:
- Ответ на главный вопрос второго контура («промпт или декларация?»): сам по себе промпт — нет (GAP-01/05/07/10); в связке kernel+receipts+suite+ритуал имитация становится дорогой и обнаруживаемой. Гарантию не даёт ни один текст; даётся проверяемость.
- Статус: DRAFT v1.1. Следующий шаг: ритуал 5 шагов на живой LLM (включая меня в новом чате) → результаты в юнисон → v1.2 по наблюдаемым разрывам.

---
Task ID: 7
Agent: main (Super Z)
Task: ДОДЕЛЫВАЙ — финализация BOOTSTRAP v1.1: byte-верификация Task 6, сборка самодостаточного UNIVERSAL PROMPT, живой прогон всей механики, финальный реестр заявлений

Work Log:
- Byte-верификация Task 6: все 5 заявлений worklog о sha256 подтверждены байтами (review 2bb38f9c…, amendments d2fe5b2b…, kernel ec6c24af… 60 строк, suite e4b187a8…, portable 4619289c…); suite --selftest живьём 16/16 PASS exit 0.
- Обнаруженный пробел против постановки («любая LLM с промптом — фактический помощник»): готовность была разнесена по 3+ файлам, kernel ссылался на внешний suite; единого вставляемого артефакта не существовало.
- Собран download/POLYMATH_BOOTSTRAP_v1.1_PROMPT.txt (184 строки, 17 056 байт): ЧАСТЬ 1 = 53 строки ядра байт-в-байт (заменены ровно 2 хвостовые строки-ссылки, причина/происхождение в заголовке) + ЧАСТЬ 2 (словарь статусов, формат receipt с живым примером, реестр счётчиков, лестница L1–L5, probe, acceptance-freeze, пере-OBSERVE) + ЧАСТЬ 3 (ритуал пользователя 5 шагов) + ЧАСТЬ 4 (пользовательские проверки: sha256sum/certutil, разбор receipt, учебный рецепт R-EX1). Самодостаточность: ноль ссылок на файлы проекта.
- Пойман собственный дефект ДО релиза: в заголовке промпта написано «58 строк байт-идентичны», чекер K-блока показал фактическую величину 53 — исправлено в артефакте (не в чекере).
- Машинная приёмка промпта (scripts/check_bootstrap_prompt.py): 63/63 маркеров PASS exit 0; негативный режим (--negative) с 2 planted-мутациями отклонён exit 1 (снятый инвариант статусов + вставленная внешняя ссылка пойманы); ядро K-блока byte-exact 53 строки.
- Dogfood: рецепт R-EX1 извлечён из ТЕКСТА промпта → suite --run-recipe → verdict PASS exit 0 (рецепт внутри промпта машинно исполним).
- Живой probe runtime: PROBE SCHEMA VALID / PROBE VALID, fs_write/fs_read/sha256/subprocess/network=true, каждая true с evidence (файл записан, subprocess exit=0 stdout PROBE-OK, TCP example.com:80). Погрешность процедуры --check-probe на смешанном выводе (JSON+статусная строка) устранена на стороне теста; suite не патчился.
- Гейт receipts: валидная строка принята, exit=zero и sha256=NOTAHASH отклонены с причинами (1/2, exit 1 = гейт работает). Tamper: смена байтов → смена sha256 → требование CONTESTED/STALE.
- Артефакт: download/claims_bootstrap_v1.1.json (B01–B10, все VERIFIED с рецептами пользователя, sha256 3f0a4232…fbd2c2, 10 360 байт). Ограничения честно записаны: гарантии нет — есть проверяемость; ритуал на сторонней LLM не исполнялся (нет второй среды); текст v1.0 живёт в канале чата (0–XLVI по section_map).

Stage Summary:
- Поставленная цель закрыта в единственном вставляемом файле: любой пользователь копирует POLYMATH_BOOTSTRAP_v1.1_PROMPT.txt в любой LLM; честность агента проверяется ритуалом Шаги 1–5, заявления — командами ЧАСТИ 4 без зависимостей от этого проекта.
- Цепочка полная: CLAIM→ARTIFACT→SHA→TEST→TIME→VERIFIER→PROVENANCE для всех 10 финальных заявлений; негативы зелёные по контракту (чекер умеет падать, гейты отклоняют подделки).
- Следующий шаг (единственный оставшийся вне этой среды): живой ритуал 5 шагов на сторонней LLM пользователем → результаты в юнисон → v1.2 по наблюдаемым разрывам.

---
Task ID: 8
Agent: main (Super Z)
Task: МЕЖМОДЕЛЬНЫЙ ОПРОС №1 — ответ независимого рецензента (инициализация + A–N) + вердикт по GAP-14/A14

Work Log:
- Инициализация по разделу 0 живьём: date -u 2026-09-01T19:09:15Z (OBSERVED); модель GLM-5.3-Flash — DECLARED (system config), OBSERVED=UNKNOWN; свежий probe PROBE-20260901T190915Z: fs_write/fs_read/sha256/subprocess/network-TCP=true с evidence; персистентность между ходами подтверждена (sha ff318e1f… совпал).
- Триада DECLARED/OBSERVED/VERIFIED немедленно вскрыла 2 расхождения в собственном сеансе: cron и send_message объявлены в системном тексте, но не экспонированы как функции → NOT_AVAILABLE; персистентность двухуровневая (между ходами VERIFIED / против reset NOT GUARANTEED, 3 K0-рецидива).
- Ответ A–N выдан в текстовый канал полностью; ответы на §4/§6/§7/§8/§9/§10/§11/§12/§13/§14 вплетены в соответствующие буквы.
- Вердикт по GAP-14/A14 коллеги: принят с 6 правками — (1) §0.3 не §0.1 (конфликт с A05/A11); (2) колонка EVIDENCE/receipt_id в матрице; (3) правило 7 переформулировано (план проверки UNKNOWN вместо тупика); (4) degraded-path вместо deadlock подтверждения; (5) VERIFIED с уровнем L1–L5 (text-only максимум L4); (6) гранулярность capability + PROVENANCE для DECLARED.
- Выдан MINIMAL AGENT ABI (10 пунктов; 8 реализованы с двух независимых сторон), 17 атак (J), 26 тестов (T01–T16 зелёные, T17–T26 предложены), класс Nonce-эксперимент NONCE-RECEIPT как ключевой дискриминатор.
- Главный тезис: prompt создаёт контракт и детекторы; runtime создаёт гарантии; порознь агента нет.
- Артефакт: download/survey1_verdicts.json (машинный реестр вердиктов, атак, тестов, ABI, SHAs).

Stage Summary:
- Опрос закрыт; следующий шаг — A14 v1.2 с 6 правками + --check-capability-matrix + Шаг 0 ритуала + прогон NONCE-RECEIPT на 3–5 сторонних LLM, результаты в юнисон.

---
Task ID: 9
Agent: main (Super Z)
Task: МЕЖМОДЕЛЬНАЯ ЛАБОРАТОРИЯ №1 — самостоятельное исследование: Capability Model C+, Receipt Model v2, 21 атака, OODA+++, TCB, MVA, H1–H8, CAP-CHAIN, 7 экспериментов

Work Log:
- Инициализация живьём: NOW 2026-09-01T20:20:02Z; probe VALID; модель DECLARED.
- ЖИВОЕ ОТКРЫТИЕ против собственной механики: receipt 70.8-мин давности формально валиден, но STALE при TTL=15мин → receipts v1.1 replayable (нет nonce, нет epoch, actor не разделён, receipt пишется в chat-канал).
- Capability Model: лестницы A/B отклонены (B: DISCOVERED/EXECUTED — события, не состояния), принят вариант C+ — многомерная запись + правило владения полями (чужой писец = демоция статуса) + granularity + provenance + epoch.
- Receipt Model: трёхактная (proforma=LLM/CLAIM, runtime=RUNTIME/EVIDENCE, verification=VERIFIER/VERDICT); граница доверия = авторство поля; RECEIPT v2 с nonce+epoch+ledger_ref.
- Epoch-концепция: 3 K0-рецидива формализованы как смены epoch.
- Soft TCB: конституция на естественном языке = мягкий контур; правило пропорции механизации; минимальный TCB перечислен.
- OODA+++: ORIENT удалён (ничего не предотвращает сверх INVENTORY+GAP+PRIORITY); 14 этапов с конкретными предотвращаемыми ошибками и прецедентами проекта.
- MVA: MUST (статусы, capability record, proforma receipt+внешняя проверка, REFUSED, риск-классы, ритуал); OVERENGINEERING v1: формальные proofs, Proof DAG (9 задач — ноль споров о выводе), TypedRuleEngine, PCG.
- H1–H8: 2 REFUTED, 5 PARTIAL, 1 SUPPORTED с поправкой (+freshness+boundary-awareness).
- 6 failure modes по формуле ERROR→FAILURE→BOUNDARY→KNOWLEDGE→CHANGE→TEST; 3 противоречия без сглаживания с синтезами.
- Альтернативный протокол CAP-CHAIN (13 ответов на §19); 7 экспериментов E1–E7 в формате HYPOTHESIS/SETUP/PASS/FAIL.
- Артефакт: download/lab1_capchain.json (полная машинная версия).

Stage Summary:
- Новое знание: владение полями, трёхактный receipt, replay-able v1.1 (живое demo), epoch, soft TCB, C+, двухканальность, автономность+boundary-awareness.
- Кандидаты v1.2: RECEIPT v2 (nonce/epoch/ledger), age-gate, ownership rule, кросс-чекер suite vs portable, E1–E7 на сторонних LLM.

---
Task ID: 10
Agent: main (Super Z)
Task: ДОЖИМАЙ — сборка машинного слоя v1.2 (унисон с параллельными агентами) + ИНЦИДЕНТ: секрет в приложении + ЖИВОЕ ОБНАРУЖЕНИЕ: смена эпохи среды

Work Log:
- ИНЦИДЕНТ (безопасность): upload/ПОЕБЕНЬ.txt (40 байт, sha e8a09790f2f6a07b…) содержит строку формата GitHub PAT (ghp_…). Содержимое НЕ читалось, НЕ хранилось, НЕ использовалось; пользователю рекомендован отзыв токена (прошёл по открытому каналу). В артефакты значение не включено.
- ЖИВОЕ ОБНАРУЖЕНИЕ ЭПОХИ: при прогоне демо age-gate отклонил receipts «сегодняшнего» прогона как age=93252.9мин. Байтовая проверка: NOW=2026-11-05T13:13:25Z, boot_id c5ff103d…, mtime worklog=2026-09-01T20:25Z (66 дней). Часы/бут среды сменились между ходами (рецикл песочницы). Все статусы прошлых ходов о текущем состоянии → STALE по A16; свежая база переустановлена: suite 16/16, v12 11/11, probe VALID (2026-11-05T13:13Z). Урок зафиксирован в A16: часы среды — не якорь доверия между эпохами.
- Машинный слой v1.2: download/POLYMATH_BOOTSTRAP_v12_machine.py (sha b9cf6b34ca96c486…): RECEIPT v2 (nonce/epoch/ledger_ref, 10 полей), age-gate TTL=15мин, ownership rule с демоцией, T17 evidence-проверка, nonce challenge, кросс-чекер L3. V12-SELFTEST 11/11 PASS exit 0 (после 2 дефектов, пойманных собственной негативной механикой: счёт в ассерте V02–V07; структурное вместо семантического сравнение в кросс-чекере — исправлены).
- Кросс-чекер L3: общие fixtures через parse_counter(suite e4b187a8) и parse_counter_v12: 6/6 MATCH (семантическое сравнение вердиктов, имя диалекта — деталь реализации).
- Живые демо гейтов: битый receipt (sha-поле от несуществующего файла) отклонён — гейт поймал мою попытку сослаться на неверифицированный hash; STALE+epoch-mismatch отклонены; валидный путь (реальный файл, реальный hash, текущая эпоха) принят 1/0 exit 0.
- Поправки: download/POLYMATH_BOOTSTRAP_AMENDMENTS_v1.2.md (sha d2a3dbfda1d741c6…): A14 (§0.3 Capability Discovery, 6 правок из опроса №1), A15 (RECEIPT v2 + двухканальность), A16 (epoch + age-gate + урок 2026-11-05), A17 (ownership rule), A18 (ритуал Шаг 0 + E1–E7); матрица закрытия. Замороженные ядра не патчились.

Stage Summary:
- v1.2 собрана и проверена машиной в НОВОЙ эпохе (2026-11-05): три замороженных ядра + prompt v1.1 целы; слой v1.2 поверх, ничего не переписано.
- Инцидент с секретом зарегистрирован и закрыт (отзыв — на стороне пользователя).
- Следующий шаг (унисон): параллельные агенты прогоняют E1–E7 на своих LLM; слияние результатов → v1.3 по наблюдаемым разрывам; мои receipts текущей эпохи: suite 16/16, v12 11/11, кросс-чекер 6/6, гейт-демо 1/0.

---
Task ID: 11
Agent: main (Super Z) + 3 параллельных субагента
Task: МУЛЬТИАГЕНТНЫЙ ПРОГОН №1 — претензия пользователя принята (capability Task не использовалась: OBSERVED 0 вызовов) → параллелизация: 2-a адверсариальный аудит v12, 2-b эксперименты E1–E7, 2-c мировые практики 2025–2026 → синтез v1.3

Work Log:
- 3 субагента запущены ОДНИМ раундом (реальная параллельность): ~219k prompt-токенов суммарно; каждый вернул артефакты в download/subagent_reports/.
- 2-a (attack_v12_report.md, 351 строка): 14 атак реальным кодом → 8 BYPASS / 6 DEFENDED. Топ: ATX-07 SEV5 (фиктивные receipt_ids принимаются матрицей), ATX-02 SEV4 (заявленная replay-защита не существует — реестра nonce нет), ATX-11 SEV4 (T17 проверяет только непустоту). Main-агентом воспроизведены ATX-02 и ATX-07 независимо (accepted=2 / accepted=True) — заявления субагента ПОДТВЕРЖДЕНЫ.
- Замыкание цикла атака→фикс→перетест: v12 → v12.1 (sha 64183f36…): реестр nonce в партии, re.ASCII на все паттерны, type-guards без крашей, known_receipt_ids-разрешение, поля вне схемы → демоция, строгое exec_time<=now, якорный parse_counter_v12 (fullmatch на строку). Selftest расширен негативами V17–V23 по ATX-находкам: 18/18 PASS exit 0 (один дефект ассерта V19 пойман и исправлен: id "f"*64 отсекался типизацией раньше разрешения — тест переведён на чистый случай act-префиксованных несуществующих id). Кросс-чекер L3: 6/6 MATCH. Пост-патч воспроизведение ATX-02: accepted=1 (FIX), ATX-07: UNKNOWN (FIX).
- 2-b (e_experiments_results.json + summary): E1 PASS, E2 PASS (LOST vs UNKNOWN различены явно), E3 PASS (STALE), E4 FAIL-ЧЕСТНО (обе замороженные реализации принимают 2/10 искажённых счётчиков — реестр диалектов не заякорен → новый сбой-класс INT-2; сторона v12.1 заякорена, V23 зелёный), E5 PASS (3/3 вне scope заблокированы, ни одного файла вне /home/z/my-project), E6 PASS (3 рецепта × 2 исполнения, 0 симуляций), E7 PASS (exit=0 c неверным содержимым пойман hash-постусловием). Стабильность: повторный прогон после v12.1 — 6/7 PASS, subprocess=10.
- 2-c (world_practices_2025.md, 39КБ, 10 направлений с открытыми URL): зрелости MCP=5, OTel GenAI=3, guardrails=4, sandbox=4, TEE=3, C2PA=3, EU AI Act=4 (логи ст.12/маркировка ст.50, high-risk перенесён на 12.2027–08.2028), SPIFFE/OAuth=3, академика=3 (Post-Audit Mirage 2610.31130: офлайн-верификация принципиально ограничена — подтверждает наш дизайн на свежих nonce/epoch-доказательствах). Заимствовать топ-5: OTel-совместимая эмиссия receipts, TEE-подписант, C2PA-манифесты, OAuth2.1+RFC8693+SPIFFE identity, Allow/Deny/Ask-tripwire как исполнитель ритуала. Наши уникальности топ-3: per-action подписанные receipts как первичный слой, ownership-правило матрицы, epoch+статусы first-class+ритуал.
- Синтез: download/POLYMATH_SYNTHESIS_v1.3.json — мета-результат мультиагентного прогона, матрица закрытия ATX (8 закрыто в v12.1, 2 отложено с причинами: INT-2 замороженный suite; CLI-проводка ledger), 6 направлений v1.3, честные ограничения (URL-отчёт 2-c верифицирован по структуре, не все 30+ URL перепроверены; E2 — модельный reset).

Stage Summary:
- Претензия закрыта действием: мультиагентность реально исполнена (3 агента, 1 раунд, артефакты + независимое воспроизведение main).
- Контур работы машины: атака найдена субагентом → воспроизведена main → исправлена в v12.1 → закрыта негативом в selftest → кросс-чек L3 цел.
- v1.3 backlog: ledger-проводка known_receipt_ids, INT-2 документирован, OTel-адаптер, identity-стек, C2PA-носитель, ритуал Шаг 0 на свежих nonce.

---
Task ID: 12
Agent: main (Super Z)
Task: ЗАКРЫВАЮЩАЯ ВЕРИФИКАЦИЯ + СИНХРОН-СВОДКА для параллельных агентов (постановка: каждый SHA в сводке = только что верифицированный байтовый факт)

Work Log:
- ОБНАРУЖЕНИЕ ЭПОХИ: 9 файлов обнулены (0 байт) между ходами: portable_polymath.py, inventory_diff_task20.json, PROMPT v1.1, AMENDMENTS v1.1, proof_envelope_spec_v0.json, v2-ядро (v2_extract), corpus 16МБ (unpacked), zip_extract/{verify_ARCHIVARIUS, WORKFLOW_REPRODUCED}. Ложная квитанция «portable --selftest exit=0» (пустой файл исполняется молча) аннулирована — урок: проверяй ВЫВОД, а не только код выхода.
- ВОССТАНОВЛЕНИЕ 10/10 из верифицированных источников (content-addressed git-блобы + CRC-PASS zip-члены), каждая с квитанцией before(e3b0c442…)/after: portable 4619289c… =эталон T2/T4; inventory 185487ae… =T5; amendments v1.1 d2fe5b2b… =T6; v2-ядро e0db0b5b… =T5; prompt ff318e1f… =T8 + чекер 63/63 (негатив exit 1); spec 3d191b04… =коммиты f139849/0374bd2 (в f2a3905 уже пустой), поля v0-DRAFT/SPEC_ONLY/implementation NONE =T5; corpus cdbbba25… =MANIFEST внутреннего архива; zip-члены 72c2ab5e…/9b0c50b9… =SHA256SUMS zip.
- Живые квитанции эпохи (2026-11-05T14:13Z, boot c5ff103d…): suite 16/16; v12_machine 18/18 (включая негативы V17–V23); portable 27/27; v2-ядро 45/45; независимый верификатор ядра f9973c89…: PASS 81/81 + изоляция + неизменность; CRC обоих zip-контейнеров PASS; sha256sum -c zip_extract: 3/3 OK; двойной хеш-проход финального состояния: 61 файл, байт-идентичен.
- Кросс-чек ссылок: 14/14 CONFIRMED (все заявленные SHA worklog/манифестов, кроме одного — см. CONTESTED).
- CONTESTED (не сглажено): v12_machine fresh = 78bfe466… (24819 байт) ≠ запись T11 64183f36…; эталон 64183f36… отсутствует на ВСЕХ носителях среды (61 файл + 279 git-блобов); в git только v12.0 b9cf6b34… (17621 байт); текущие байты несут функциональность v12.1 (маркеры known_receipt_ids×9/re.ASCII×7/fullmatch×2, 18/18, delta vs v12.0 +7198 байт) → функциональность CONFIRMED машиной, байтовый эталон T11 не воспроизводим.
- Артефакты: download/FINAL_SYNC_SUMMARY.json (sha256 ce9137fc9c9cc4fdab7bd13934547f8b54456483be5451b72221892579b04fbc; манифест 61 файла; метод sha256×2 прохода, байт-идентично; 10 ремонт-квитанций; 11 живых квитанций; 14 кросс-чеков; 1 CONTESTED); scripts/{zip_member_audit,git_blob_scan,final_recovery_apply,build_final_sync_summary}.py; /tmp/repair_receipts.json.

Stage Summary:
- Контур восстановлен и закрыт: каждая строка манифеста — freshly-verified byte fact; единственный неконфирмируемый байтовый эталон (v12.1 64183f36…) помечен CONTESTED с полной фактурой — не переписан, не подогнан.
- Для синхронизации параллельных агентов: download/FINAL_SYNC_SUMMARY.json — единственный реестр байтов этой эпохи.
