# POLYMAT v3.8.0 — ROOT EPOCH CHAIN WIRING

## Контекст удара
Пользователь передал два архива «v3.6.0»: TRUST_DOMAIN (аудирован ранее, Task 8) и **ROOT_TRUST**
(новая ветка, sha256 `0a950025…`, «ROOT trust epoch / rotation / history hardening», создан через
минуту после публикации v3.7.0). Плюс два handoff-контейнера другой LLM: заявлен следующий рубеж —
«доказать реальную цепочку RootTrust → Proof → CAS → Revocation → Reconciliation → COMMIT», а не
создавать очередной изолированный класс.

## Аудит ветки ROOT_TRUST (механический)
- py_compile PASS; selftest **98/98** воспроизведён независимо (построчное совпадение с заявленным).
- Прогон 5 накопленных батарей: **19 прежних корней живы** (v300 5/5, v310 0/2, v330 5/8, v340 5/6,
  v360 4/4) — ветка не переносила ни одной реставрации v3.3.1/v3.4.0/v3.7.0.
- Архив чист: `__pycache__`-байткод побитово соответствует источнику (marshal-сравнение).
- **Новая форма маскировки №3 (после substring и подмены под теми же номерами): тест-свидетельство
  через наблюдаемую величину вместо отказного семантического assertion.** T97 ветки «truncation»
  проверяет `digest(h[:2]) != digest(h)` — дайджест ДЕЙСТВИТЕЛЬНО меняется, тест зелёный, при этом
  `verify_history` УСЕЧЁННУЮ ИСТОРИЮ ПРИНИМАЕТ. Заявка «rollback/truncation detection» держится
  на наблюдении, не на отказе.

## Доказанные дефекты RT-слоя (scripts/proof_v360_root_trust_defects.py — 4/4 на ветке)
| ID | Дефект | Суть |
|----|--------|------|
| N-RT3 | DEAD-WIRING | RootTrustAuthority/RootEpoch — только selftest (4188+), ноль вызовов из Agent/Governor/commit; «in-runtime layer» = декларация |
| N-RT1 | TRUNCATION-UNDETECTED | verify_history пропускает усечение хвоста (e.epoch==i сходится); пина дайджеста на production-пути нет → усечение доходит до COMMIT |
| N-RT2 | DOUBLE-REVOKE | revoke_current от уже отозванного корня принимается молча |
| N-RT4 | EXCEPTION-CONTRACT | RootTrustError(Exception) вне ledger-контракта: при вшивании в COMMIT отказ вырвался бы из except-обвязки (класс N-CLS) |

## Выпуск v3.8.0 (база v3.7.0 сохранена полностью; 5504 строки)
- `RootEpochChain` — порт истории корневых эпох с закрытыми N-RT1/2/4:
  пин дайджеста обязателен (validate_pinned_state), двойной revoke отклонён,
  RootTrustError ∈ KnowledgeLedgerError.
- **ROOT TRUST GATE в ProofCarryingGovernor.commit** (N-RT3): история сверяется с пином,
  активная эпоха вшивается в ProofObject + state["proof"] + commit-запись + ledger-COMMIT.
  Дуга ROOT → Proof → CAS → Revocation → Reconciliation → COMMIT стала механикой.
- `replay`: откат корневой эпохи в журнале отклоняется (root epoch rollback).
- Двухконтурная политика: `validate_checkpoint_active` (новые коммиты — только активная эпоха)
  vs `validate_epoch` (исторический аудит — эпоха существует, не отозвана, отпечаток совпадает).
- Ленивый бутстрап цепи для состояний вне runtime → инвариант «нет COMMIT без валидной
  активной корневой эпохи под пином» универсален, ни один старый тест не сломан.
- Тесты: T121–T126 новые + T127–T136 порт проб ветки (T130 усилен до отказного assertion).

## Верификация
- Selftest v3.8.0: **130/130 PASS, FAIL=0, exit=0** (114 → +16).
- Шесть батарей одновременно зелёные: v300 0/5, v310 0/2, v330 0/8, v340 0/6, v360 0/4,
  v360_root_trust 0/4.
- Регрессия собственного процесса: T122 сперва кодировал тампер ПОСЛЕ компиляции proof'а —
  падал по CAS, а не по корневому гейту; сценарий перестроен (усечённая история + пин полной
  до компиляции), assertion усилен, не ослаблен.

## Публикация
- `polymath_agent_v3.8.0.py` (sha256 `04199e6e…`)
- `proof_v360_root_trust_defects.py` (sha256 `34df59f8…`)
- `SELFTEST_v3.8.0.txt`, `MANIFEST_v3.8.0.json`, `SHA256_v3.8.0.txt`
- `POLYMAT_v3.8.0_ROOT_EPOCH_CHAIN.zip`

## Следующий фронт (намечен)
- (а) MAC-конструкция RootTrustAuthority (pbkdf2_hmac c=1, корневой ключ в роли salt) — перевести
  на стандартный HMAC и связать авторизацию подписывающих ключей с активной эпохой цепи;
- (б) селективный re-bind: recovery-план по revocation-записи (re-observe только затронутых evidence);
- (в) типизация claim'ов PUBLICATION≠OBSERVATIONAL + запрет моста;
- (г) байтемпоральность valid_time/observed_at/recorded_at.
