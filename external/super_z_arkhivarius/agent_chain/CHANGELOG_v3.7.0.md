# POLYMAT v3.7.0 — «Production Wiring Restoration»

База: JOHNSON v3.6.0 TRUST_DOMAIN_ARCHIVE (хеш сверен: 79e512e3…; selftest 98/98 воспроизведён независимо).

## Вердикт аудита v3.6.0
Selftest зелёный (98/98), но 15 механически доказанных дефектов в production-путях:
- батареи v300 5/5, v330 5/8, v340 5/6 (v310 0/2 — закрыты честно);
- НОВЫЕ пробы v360 4/4 (proof_v360_defects.py): N1 fp-refs без атрибуции, N2 knowledge ledger вакуум в рантайме, N3 replay принимает дубликат COMMIT, N4 reconciliation никогда не вызывается;
- новая форма маскировки: слабые unit-варианты тестов переименованы веткой в номера хранителей T67–T72; дубль номера T73 сохраняется с v3.3.x.

## Исправления (все — механика с тестами)
1. **Реставрации v3.4.0 портированы**: канонические id + Stale≠Unknown (R-D1), dangling-гейт (R-D2), TMS-инвалидация дериваций (R-D3), claim_ids ⊆ claim-узлы (N-CLM), ProofClosureError ⊂ ProofCarryingCommitError (N-CLS), FalsificationProbe.infer_from_ledger (N-FALS).
2. **ArtifactEvidenceEdge**: evidence помнит {путь: sha256 артефакта В МОМЕНТ наблюдения}; рантайм биндит write/read/verify. Read — главный эпистемический источник — больше не анонимен.
3. **Revival-gate в commit**: сверка evidence-пинов с миром ДО разрешения COMMIT; перезапись глобальных пинов перекомпиляцией не launder'ит старое evidence.
4. **Точный каскад**: ревокация по рёбрам + транзитивное закрытие по claim_dependencies; атрибуция из узлов proof (самодостаточно).
5. **N-RES**: успешный re-COMMIT закрывает REVOKED → RESOLVED + revocation_history.
6. **KnowledgeAuditor в run-loop**: дрейф мира после коммита → STALE; бит-в-бит восстановление → VALID.
7. **N1**: refs выводятся из рёбер — реальные пути, а не 16-символьные fp-префиксы.
8. **N2**: runtime выставляет пути knowledge-леджера/индекса/anchor; каждый production COMMIT материализуется в ImmutableKnowledgeLedger (hash-chain) и KnowledgeRevocationIndex.
9. **N3**: replay отклоняет дубликат COMMIT — политика форков полна (revoke-unknown, commit-after-revoke, duplicate-commit).
10. **N4**: run-loop на каждом такте при наличии commit вызывает KnowledgeAuditor.audit + KnowledgeRevocationIndex.reconcile.

## Trust-domain слой v3.6.0
Сохранён полностью (RootTrustAuthority, SigningTrustDomain, LedgerTrustAnchor, ключевые эпохи, rollback/resurrection/replay-гейты, T84–T103) — и впервые подключён к живому production-пути: до v3.7.0 COMMIT агента не материализовался ни в леджере, ни в индексе (пути не выставлялись).

## Тесты
- Selftest: **114/114 PASS**, exit 0. Хранители T67–T72 восстановлены; слабые варианты ветки сохранены под номерами T115–T120 (без удаления); T76 усилен до stale_evidence; дубль T73 устранён (CAS changed → T104); новые T105–T114 (revival, точный каскад, drift-аудит, RESOLVED, контракт исключений, CONTESTED, e2e read-биндинг, живой леджер, historical reconcile, дубликат COMMIT).
- Батареи дефектов (независимый от suite слой): **v300 0/5, v310 0/2, v330 0/8, v340 0/6, v360 0/4 — все зелёные одновременно.**

## Верификация
```
python polymath_agent_v3.7.0.py --selftest
python proof_v300_defects.py polymath_agent_v3.7.0.py
python proof_v310_defects.py polymath_agent_v3.7.0.py
python proof_v330_defects.py polymath_agent_v3.7.0.py
python proof_v340_defects.py polymath_agent_v3.7.0.py
python proof_v360_defects.py polymath_agent_v3.7.0.py
```

## Граница
Trust-domain остаётся in-process TCB-границей (не hardware/OS-изоляция корневого ключа); якорь реестра внешне пинуем и не самоподлинен.
