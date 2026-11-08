# kanon-verify · верификатор канона ПОЛИМАТ как библиотека

**Волна ×4 · П45 (issue #2)** · извлечение верификатора в pip-пакет + CLI.
Инвариант протокола: **«проверяй строкой, не смыслом»**. Инструмент = договор:
hub-воркфлоу и клетки роя потребляют ОДИН канон проверок — одна правда на всех.

## Приёмка (машинная, из issue)

```bash
pip install -e ./verifier
kanon-verify --selftest                      # rc=0
python3 -m unittest discover -s verifier/tests -v   # юнит-тесты зелёные
python3 scripts/hub_inventory.py             # hub-инвентарь импортирует пакет
```

## Канон (то, что обязаны исполнять все потребители)

| Функция | Договор |
|---|---|
| `sha256_file(path)` | пломба файла строкой; потоковое чтение, равное разовому |
| `parse_manifest(text)` | «`<sha256>  <путь>`» (sha256sum-совместимо); дубликат пути = ПРОВАЛ |
| `verify_manifest(root, text)` | сверка дерева; MISSING/MUTATED/STRUCTURE — три провала |
| `verify_files(root, expect)` | сверка словаря `{имя: sha256}` — канон Б25.8 |
| `selftest()` | самоиспытание канона (5 кейсов) до проверки чужого |
| `report_bytes(report)` | одинаковый вход → одинаковые байты отчёта |

Отчёт канона: `{"canon":1,"ok":bool,"checked":n,"failures":[{path,expected,got,reason}]}`.

## CLI

```
kanon-verify --selftest                       # самоиспытание
kanon-verify manifest MANIFEST_SHA256.txt     # сверка пломб репозитория
kanon-verify files --expect expect.json       # сверка по словарю (канон Б25.8)
```

## Потребление клетками роя (без установки)

Клетки без pip используют пакет как subtree: `verifier/kanon_verify/` —
чистый std-only, добавление в `sys.path` даёт тот же канон:

```python
sys.path.insert(0, "<репо>/verifier")
from kanon_verify import sha256_file, verify_manifest
```

## Происхождение

Извлечено из `scripts/verify_b25_final.py` (финальная сверка Б25.8, Task 33).
Исходный скрипт не модифицируется (тексты прогонов не ревизуются) —
пакет покрывает его канон и добавляет самоиспытание. `CANON_VERSION = 1`
растёт только дельтой с санкции Хозяина.
