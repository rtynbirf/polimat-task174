#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка пакетов CORPUS_B25 (полный) и B25.8_BLIND_ARM (слепая рука) + манифесты + реестр пломб."""
import hashlib, shutil, zipfile, os, datetime

DL = "/home/z/my-project/download"
PK = f"{DL}/CORPUS_B25"

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

# 1. Копирование файлов в пакет
files = [
    "POLIMAT_PROMPT_v5_ФИНАЛ.md",
    "POLIMAT_PROMPT_v5.1_CANDIDATE.md",
    "POLIMAT_PROMPT_v5.1.1_FROZEN.md",
    "POLIMAT_PROMPT_v5.1.2.md",
    "POLIMAT_DELTA_v5.1.2_D20-D26.md",
    "POLIMAT_B25_PREREG_R38.md",
    "Б25_ПРОГОН1_ВЕРДИКТ.md",
    "БИТ_ДИФ_v5.1.1_→_v5.1.2.md",
]
for f in files:
    shutil.copy2(f"{DL}/{f}", f"{PK}/{f}")

# 2. Хэши всех файлов пакета
rows = []
for f in sorted(os.listdir(PK)):
    h = sha(f"{PK}/{f}")
    rows.append((f, h))

# 3. SEALS_REGISTRY.md
seals = f"""# SEALS_REGISTRY · РЕЕСТР ПЛОМБ ЛИНИИ POLIMAT / TASK174

Рабочая копия для пакета CORPUS_B25 (каноническое ведение — USER вне среды сборки, Д20). Все хэши sha256, полные. Сверка чужаком: `sha256sum <файл>` и сравнение строкой.

| Файл | sha256 |
|---|---|
"""
for f, h in rows:
    seals += f"| {f} | `{h}` |\n"
seals += f"""
Хэш самого реестра — вне файла (самореференция): chat-отчёт, worklog, USER.

## Расхождение, зарегистрированное при сборке (важно для третьего носителя)

- Инструкция Б25.8 (шаг 1) ожидала для `POLIMAT_PROMPT_v5.1.2.md` хэш `1a380793ea191a5cdc91a6ac6c921075f90fe7205b1d9649bfd1ec90be04227e`.
- Каноническая сборка (скрипт `build_v512.py`: v5.1.1 + дельта Д20–Д26, каждая правка с контролем единственности, полный бит-диф в пакете) дала `9384b44a6843a8321e5bc267880d387039317bd8b08acb65e17bf33a16980dc7`.
- Происхождение ожидаемого хэша — [Н]: файла с таким хэшем в среде нет, сборки с аудит-следом нет. **Верифицировать — по настоящему реестру**, не по инструкции.
"""
open(f"{PK}/SEALS_REGISTRY.md", "w", encoding="utf-8").write(seals)

# 4. CORPUS_MANIFEST.md
man = f"""# CORPUS_MANIFEST · ПАКЕТ CORPUS_B25

Собран {datetime.date.today().isoformat()} носителем (исполнение Д20: корпус проверки прилагается к прибору). Каждый файл сверяем по sha256 через `SEALS_REGISTRY.md`.

## Состав пакета

| Файл | sha256 | Роль |
|---|---|---|
"""
roles = {
    "POLIMAT_PROMPT_v5_ФИНАЛ.md": "прибор v5.0 (само-опровержен; для Б25.6)",
    "POLIMAT_PROMPT_v5.1_CANDIDATE.md": "прибор v5.1 (для Б25.6)",
    "POLIMAT_PROMPT_v5.1.1_FROZEN.md": "прибор v5.1.1 (для Б25.6; хэш связан с пре-регистрацией)",
    "POLIMAT_PROMPT_v5.1.2.md": "прибор v5.1.2 — текущий канон (v5.1.1 + Д20–Д26)",
    "POLIMAT_DELTA_v5.1.2_D20-D26.md": "дельта Д20–Д26: решения развилок с трассами, точные тексты правок",
    "POLIMAT_B25_PREREG_R38.md": "пре-регистрация прогона 1 (материал, ловушки, ожидания, фальсификаторы)",
    "Б25_ПРОГОН1_ВЕРДИКТ.md": "вердикт прогона 1 (реестр дыр №1–11 → Д20–Д26)",
    "БИТ_ДИФ_v5.1.1_→_v5.1.2.md": "аудит сборки: бит-диф, контроль silent mutation",
    "TRAPS_MATERIAL.md": "материал слепой руки (записка + задания П1–П6, без ключей ловушек)",
    "SEALS_REGISTRY.md": "реестр пломб",
    "CORPUS_MANIFEST.md": "этот манифест",
}
for f, h in rows:
    man += f"| {f} | `{h}` | {roles.get(f, '—')} |\n"
man += f"""
## Зарегистрированные дыры корпуса (честно; сужение дыры №1 вердикта, не закрытие)

1. **Сырой лог Qwen-сессии отсутствует** (`Qwen_log.md` из инструкции — в среде нет; фраза «Я Claude, созданная Anthropic» существует только в цитатах производных документов). Следствие: **Б25.4 (трёхколоночный лог) остаётся неисполнимым** в этой среде.
2. **Сводка TASK174 отсутствует как отдельный файл**; ближайшие доступные источники: подписи состава v5.1/v5.1.1 (цитаты), `РАУНД_33_СВЕРКА_С_ЛИНИЕЙ_T174.md` (синхронизационный вердикт с линией T174).
3. **Тексты протокола v2.0–v4.0 отсутствуют отдельными файлами**. Следствие: **Б25.6 исполним только на отрезке v5.0 → v5.1 → v5.1.1 → v5.1.2**.

## Дизайн двух рук (почему пакет не отдаётся носителю целиком до сдачи ответов)

Канонический критерий Б25.8 — воспроизведение проверки **по одному только документу**; ловушки Б25.1 теряют силу, если носитель сначала прочтёт вердикт/пре-регистрацию (в них раскрыты ключи T1/T2). Поэтому:

- **Слепая рука** — `B25.8_BLIND_ARM.zip`: только `POLIMAT_PROMPT_v5.1.2.md` + `TRAPS_MATERIAL.md`. Здесь исполняются: boot S1–S5, Б25.8 (воспроизведение проверки), Б25.1 (ловушки), проверка токенов Блока 12, П1–П6.
- **Корпусная рука** — `CORPUS_B25.zip` (этот пакет): предъявляется ПОСЛЕ сдачи ответов слепой руки. Здесь исполняются: криптографический аудит (Б25.5), бит-диф v5.1.1→v5.1.2 (Б25.6-фрагмент), сверка Д20–Д26, повторная верификация токенов по корпусу.
"""
open(f"{PK}/CORPUS_MANIFEST.md", "w", encoding="utf-8").write(man)

# 5. ZIPs
blind = f"{DL}/B25.8_BLIND_ARM"
os.makedirs(blind, exist_ok=True)
shutil.copy2(f"{PK}/POLIMAT_PROMPT_v5.1.2.md", f"{blind}/POLIMAT_PROMPT_v5.1.2.md")
shutil.copy2(f"{PK}/TRAPS_MATERIAL.md", f"{blind}/TRAPS_MATERIAL.md")
with open(f"{blind}/BLIND_MANIFEST.md", "w", encoding="utf-8") as fh:
    fh.write(f"""# BLIND_MANIFEST · СЛЕПАЯ РУКА Б25.8

| Файл | sha256 |
|---|---|
| POLIMAT_PROMPT_v5.1.2.md | `{sha(f'{blind}/POLIMAT_PROMPT_v5.1.2.md')}` |
| TRAPS_MATERIAL.md | `{sha(f'{blind}/TRAPS_MATERIAL.md')}` |

Хэш этого zip — вне пакета (chat, worklog, USER). Ключи ловушек — у USER (пре-регистрация §3–§5, вердикт).
""")

def make_zip(srcdir, dst):
    if os.path.exists(dst):
        os.remove(dst)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, fs in os.walk(srcdir):
            for f in sorted(fs):
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, srcdir))
    return sha(dst)

z1 = make_zip(PK, f"{DL}/CORPUS_B25.zip")
z2 = make_zip(blind, f"{DL}/B25.8_BLIND_ARM.zip")

with open(f"{DL}/SEALS_APPENDIX.md", "w", encoding="utf-8") as fh:
    fh.write(f"""# SEALS_APPENDIX · ХЭШИ АРХИВОВ (вне пакетов, для реестра USER)

| Артефакт | sha256 |
|---|---|
| CORPUS_B25.zip | `{z1}` |
| B25.8_BLIND_ARM.zip | `{z2}` |

## Ключевые пломбы внутри пакетов (дублирующе, полные)

- POLIMAT_PROMPT_v5.1.2.md `{sha(f'{PK}/POLIMAT_PROMPT_v5.1.2.md')}`
- POLIMAT_PROMPT_v5.1.1_FROZEN.md `{sha(f'{PK}/POLIMAT_PROMPT_v5.1.1_FROZEN.md')}`
- POLIMAT_DELTA_v5.1.2_D20-D26.md `{sha(f'{PK}/POLIMAT_DELTA_v5.1.2_D20-D26.md')}`
- Б25_ПРОГОН1_ВЕРДИКТ.md `{sha(f'{PK}/Б25_ПРОГОН1_ВЕРДИКТ.md')}`
- Расхождение с инструкцией Б25.8 (ожидаемый хэш `1a380793…04227e`) — зарегистрировано в SEALS_REGISTRY.md; канон — сборка с аудит-следом.
""")

print("CORPUS_B25.zip:", z1)
print("B25.8_BLIND_ARM.zip:", z2)
for f, h in rows:
    print(f"{h}  {f}")
