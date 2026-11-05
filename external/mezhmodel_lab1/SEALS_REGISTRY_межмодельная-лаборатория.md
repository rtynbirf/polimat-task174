# РЕЕСТР ПЛОМБ линии «МЕЖМОДЕЛЬНАЯ ЛАБОРАТОРИЯ №1»

Назначение: реестр пломб вне среды носителя (метод §1 программы). Все «ИЗМЕРЕНО» —
hashlib SHA-256, порции 1 МБ, ни одного «примерного» хэша. [RELAY] нет: все файлы
перенесены в репо вербатим и измеримы локально. Пломба самого реестра и двух
документов интеграции — в корневом MANIFEST_SHA256.txt (запаивается после записи).

| Артефакт (external/mezhmodel_lab1/) | Размер, Б | sha256 | Статус измерения |
|---|---|---|---|
| `README.md` | 4433 | `32428798…` | ИЗМЕРЕНО сейчас (hashlib) |
| `lab1_report_llm_assistant_architecture.md` | 119643 | `fb5df2ec…` | ИЗМЕРЕНО сейчас (hashlib) |
| `lab1_report_llm_assistant_architecture.docx` | 58546 | `ce49a3c8…` | ИЗМЕРЕНО сейчас (hashlib) |
| `results/lab1_round2_results.json` | 8110 | `7ac2b2b1…` | ИЗМЕРЕНО сейчас (hashlib) |
| `results/lab1_round2_results.txt` | 6570 | `b4b44549…` | ИЗМЕРЕНО сейчас (hashlib) |
| `results/lab1_agent_halves_e1_e8.json` | 36726 | `0bfce5a6…` | ИЗМЕРЕНО сейчас (hashlib) |
| `results/lab1_agent_halves_e1_e8.md` | 21406 | `f1fc176d…` | ИЗМЕРЕНО сейчас (hashlib) |
| `results/lab1_e91_cross_review.md` | 19288 | `ea9c203f…` | ИЗМЕРЕНО сейчас (hashlib) |
| `results/lab1_emergent_synthesis.md` | 18742 | `a679c01f…` | ИЗМЕРЕНО сейчас (hashlib) |
| `receipts/ledger.jsonl` | 10887 | `fa8955b1…` | ИЗМЕРЕНО сейчас (hashlib) |
| `scripts/lab1_round2.py` | 17632 | `c0e03d62…` | ИЗМЕРЕНО сейчас (hashlib) |
| `scripts/lab1_finalize_r2.py` | 2065 | `063b3b02…` | ИЗМЕРЕНО сейчас (hashlib) |
| `scripts/make_receipt.py` | 2731 | `8adf9a13…` | ИЗМЕРЕНО сейчас (hashlib) |
| `scripts/receipt_for_file.py` | 0 | `e3b0c442…` | ИЗМЕРЕНО сейчас (hashlib) |
| `scripts/state_check.py` | 1802 | `d7f7c004…` | ИЗМЕРЕНО сейчас (hashlib) |
| `scripts/lab1_agent_halves.py` | 58348 | `c2afb4a1…` | ИЗМЕРЕНО сейчас (hashlib) |
| `scripts/report_parts/p1.md` | 0 | `e3b0c442…` | ИЗМЕРЕНО сейчас (hashlib) |
| `scripts/report_parts/p2.md` | 10551 | `6a43f678…` | ИЗМЕРЕНО сейчас (hashlib) |
| `scripts/report_parts/p3.md` | 11228 | `8595edfe…` | ИЗМЕРЕНО сейчас (hashlib) |
| `scripts/report_parts/p4.md` | 0 | `e3b0c442…` | ИЗМЕРЕНО сейчас (hashlib) |
| `scripts/report_parts/p5.md` | 13004 | `88847632…` | ИЗМЕРЕНО сейчас (hashlib) |
| `scripts/report_parts/p6.md` | 0 | `e3b0c442…` | ИЗМЕРЕНО сейчас (hashlib) |
| `scripts/report_parts/p7.md` | 14740 | `c10b7f81…` | ИЗМЕРЕНО сейчас (hashlib) |
| `worklog_межмодельная_лаборатория_полный.md` | 9253 | `1caeb488…` | ИЗМЕРЕНО сейчас (hashlib) |

Итого артефактов линии: 24 (вербатим, cmp 24/24 OK).
Суммарный объём: 445705 Б.

Документы интеграции (SEALS_REGISTRY, ИНТЕГРАЦИЯ_R2_ОТЧЁТ, 00_MANIFEST_SHA256.txt)
в реестр не вносятся — их пломбы запаиваются только в корневом MANIFEST_SHA256.txt
(разрыв цикла: реестр пломбит артефакты, манифест пломбит реестр).
