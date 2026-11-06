#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Пакетирование релиза v3.10.0 «C5 GATE ANTI-VACUUM» + пакетные исправления Task 14.

Ш-01: tool_catalog.json входит в пакет.
Ш-13: SHA-аддендум с GNU #-комментариями (sha256sum -c без предупреждений).
Ш-11 (часть): STATUS.md батарей с таблицей exit-конвенций харнеса.
"""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

REL = Path("/home/z/my-project/download/polymath/v3.10.0_release")
ART = Path("/home/z/my-project/download/polymath/v3.10.0_release/artifacts")
AGENT = REL / "polymath_agent_v3.10.0.py"
CATALOG_SRC = Path("/home/z/my-project/download/polymath/tool_catalog.json")
BATT_DIR = Path("/home/z/my-project/download/proof_batteries_task13")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    assert sha256_file(AGENT) == "ef73a15881fa4212abe5ab0ff5ff4ee947255048b342f90607c731d6621067dd"

    # ── Каталог в пакет (Ш-01) ──
    shutil.copy2(CATALOG_SRC, REL / "tool_catalog.json")
    catalog = json.loads((REL / "tool_catalog.json").read_text(encoding="utf-8"))

    # ── Лог самопроверки ──
    shutil.copy2("/home/z/my-project/scripts/v3100_ws_selftest_run.txt",
                 REL / "SELFTEST_v3.10.0_local_run.txt")

    # ── Лестница (16 логов) + батареи (12 логов) → artifacts/ ──
    ART.mkdir(exist_ok=True)
    for src in sorted(Path("/home/z/my-project/scripts/v3100_ladder").glob("*.txt")):
        shutil.copy2(src, ART / f"ladder_{src.name}")
    for h in ["proof_v300_harness", "proof_v310_harness", "proof_v330_harness",
              "proof_v340_harness", "proof_v360_harness", "proof_v360_rt_harness"]:
        shutil.copy2(f"/home/z/my-project/scripts/v3100_ws_{h}_v390.txt", ART / f"{h}__v390.txt")
        shutil.copy2(f"/home/z/my-project/scripts/v3100_ws_{h}_v3100.txt", ART / f"{h}__v3100.txt")

    battery_rows = []
    for h in ["proof_v300_harness", "proof_v310_harness", "proof_v330_harness",
              "proof_v340_harness", "proof_v360_harness", "proof_v360_rt_harness"]:
        log = (ART / f"{h}__v3100.txt").read_text(encoding="utf-8")
        line = [l for l in log.splitlines() if "ИТОГ" in l][0]
        battery_rows.append((h, line.strip()))

    # ── STATUS.md батарей (Ш-11: exit-конвенции) ──
    status = ["# STATUS батарей v3.10.0 (Task 14, Ш-11)", "",
              "Прибор: battery_harness.py-семейство (rev2-харнесы, трёхзначная эпистемология).",
              "Вердикты: REPRODUCED (дефект жив, 1 бит), CLOSED (только при W1+W2+W3),",
              "INAPPLICABLE (преусловие не материализовалось / вакуум / затмение, причина названа),",
              "ERROR (сбой прибора).", "",
              "## Exit-конвенции", "",
              "| exit | значение |", "|---|---|",
              "| 0 | zero-flip против матрицы: ни одного переключения вердикта |",
              "| 1 | ПЕРЕКЛЮЧЕНИЕ вердикта против исторической матрицы |",
              "| 2 | ветка вне матрицы / сценарий не собрался (zero-flip не проверялся) |", "",
              "## Прогоны против polymath_agent_v3.10.0.py (ef73a158…)", "",
              "| батарея | итог |", "|---|---|"]
    for h, line in battery_rows:
        status.append(f"| {h} | {line.replace('ИТОГ: ', '')} |")
    status += ["", "Контроль: те же харнесы на v3.9.0 (ea1e9001…) — вердикты бит-в-бит",
               "идентичны (логи в artifacts/*__v390.txt). REPRODUCED=0 и ERROR=0 на обеих ветках.",
               ""]
    (REL / "STATUS_batteries_v3.10.0.md").write_text("\n".join(status), encoding="utf-8")

    # ── CHANGELOG ──
    changelog = """# CHANGELOG v3.10.0 — C5 GATE ANTI-VACUUM

Бейзлайн: polymath_agent_v3.9.0.py (ea1e9001d53a646a4def4930f4e17ec4ca5d63512d37284cbd466bd314fda2b3, 133/133).
Рубеж: Р-01 из ревизии приборного слоя (POLYMAT_AUDIT_REV1, CH5) — анти-вакуумное
правило гейтов (C5) переводится из принципа v3.9.0 в МЕХАНИКУ рантайма.

## Что вошло

1. **VacuousRefusalError** — отказ отказа: отказной гейт, отказавший без именованной
   причины, сам поднимается как нарушение политики. Вакуумный отказ (урок P5/N-ART)
   структурно невыразим.
2. **GateAntiVacuum.refuse(gate, reason)** — единственный законный способ отказа
   гейта COMMIT-контура: сообщение гарантированно несёт namespaced-причину
   `<gate>: <reason>`. Все 10 точек отказа ProofCarryingGovernor (validate/commit)
   и StateCAS.assert_unchanged переведены на refuse(); тексты причин сохранены
   байт-в-байт (zero-flip по сообщениям).
3. **GATE_REGISTRY** — явный реестр 11 отказных семейств COMMIT-контура
   (COMMIT, PROOF_CLOSURE, TEMPORAL, CAS, FALSIFICATION, ROOT_TRUST_GATE,
   ROOT_AUTH, SIGNING, ANCHOR, LEDGER, GOVERNOR-пути) с именованными причинами
   и парными свидетелями самопроверки: honest_witnesses («честный путь принят»)
   + refusal_witnesses («отказ по своей причине») — 51 свидетель.
4. **GateAntiVacuum.audit()** — механическая сверка реестра: безымянная причина
   или отсутствующий свидетель = нарушение C5.
5. **T140 (мета-гейт)**: реестр непротиворечив и ВСЕ 51 парный свидетель реально
   исполнены и зелёные — удаление/обесточивание парного теста роняет --selftest.
6. **T141**: позитивный контроль невыразимости вакуумного отказа.
7. **Усиление refusal-проб (C5: голый факт исключения — не свидетель)**:
   T64, T65, T115, T117, T120 теперь ассертируют именованную причину отказа
   (префикс и/или точный текст). T72/T77/T78 уже несли ассерты причин.
8. **Пакетные исправления Task 14 (Ш-01, Ш-11, Ш-13)**: tool_catalog.json входит
   в пакет; STATUS.md батарей с таблицей exit-конвенций харнеса; SHA-аддендум
   с GNU #-комментариями.

## Гейты Тела — честная граница охвата

Гейты Тела (изоляция путей T01, схемный валидатор T02, SSRF T09, каталог T11,
процедуры T14, пустая запись T15, план-замок T17, план-гигиена T19, redirect T21)
уже несут парные пробы «отказ + честный путь» в каждой паре; вшивание их в
GATE_REGISTRY — следующий рубеж при ревизии Тела (Р-02…Р-04 в силе).

## Верификация

- py_compile: OK. Самопроверка v3.10.0: **135/135 зелёных**, exit 0
  (133 унаследованных + T140 + T141; T12 — реальный PASS, каталог 2444/34).
- Самопроверка лестницы (16 веток, живой каталог): **ZERO-FLIP, 0 переключений** —
  v1.2.4 19, v1.5.1 29, v2.1.0 43, v2.2.0 52, v2.9.0 57, v3.2.0 66, v3.3.0 69,
  v3.3.1 78, v3.3.2 72, v3.3.3 74, v3.4.0 88, v3.6.0(TD/RT) 98, v3.7.0 114,
  v3.8.0 130, v3.9.0 133 — все числа воспроизведены.
- Батареи дефектов (6 харнесов, rev2): REPRODUCED=0, ERROR=0 на v3.10.0;
  вердикты бит-в-бит идентичны прогонам на v3.9.0 (zero-flip поколения).
"""
    (REL / "CHANGELOG_v3.10.0.md").write_text(changelog, encoding="utf-8")

    # ── MANIFEST ──
    manifest = {
        "project": "POLYMAT",
        "version": "3.10.0",
        "version_string": "C5 GATE ANTI-VACUUM",
        "baseline": "polymath_agent_v3.9.0.py (ea1e9001d53a646a4def4930f4e17ec4ca5d63512d37284cbd466bd314fda2b3, 133/133)",
        "status": "IMPLEMENTED_AND_SELFTESTED",
        "artifact": "polymath_agent_v3.10.0.py",
        "sha256": sha256_file(AGENT),
        "lines": AGENT.read_text(encoding="utf-8").count("\n") + 1,
        "selftest": "135/135 PASS",
        "exit_code": 0,
        "catalog": (f"tool_catalog.json (polymat.arsenal/1.0): {catalog.get('total')} записей, "
                    f"{catalog.get('categories')} категорий, каталог входит в пакет (Ш-01)"),
        "gate_registry": {"families": 11, "paired_witnesses": 51,
                          "meta_gate": "T140", "vacuous_refusal_probe": "T141"},
        "ladder_zero_flip": {
            "branches": 16,
            "numbers": {"v1.2.4": 19, "v1.5.1": 29, "v2.1.0": 43, "v2.2.0": 52,
                        "v2.9.0": 57, "v3.2.0": 66, "v3.3.0": 69, "v3.3.1": 78,
                        "v3.3.2": 72, "v3.3.3": 74, "v3.4.0": 88, "v3.6.0_TD": 98,
                        "v3.6.0_RT": 98, "v3.7.0": 114, "v3.8.0": 130, "v3.9.0": 133},
            "flips": 0},
        "batteries": {
            "proof_v300_harness.py": "REPRODUCED=0 CLOSED=4 INAPPLICABLE=1 ERROR=0",
            "proof_v310_harness.py": "REPRODUCED=0 CLOSED=2 ERROR=0",
            "proof_v330_harness.py": "REPRODUCED=0 CLOSED=7 INAPPLICABLE=1 ERROR=0",
            "proof_v340_harness.py": "REPRODUCED=0 CLOSED=6 ERROR=0",
            "proof_v360_harness.py": "REPRODUCED=0 CLOSED=4 ERROR=0",
            "proof_v360_rt_harness.py": "REPRODUCED=0 CLOSED=4 ERROR=0",
            "zero_flip_vs_v390": "вердикты бит-в-бит идентичны на всех 6 харнесах"},
        "task14_packaging": ["Ш-01: каталог в пакет", "Ш-11: STATUS батарей с exit-конвенциями",
                             "Ш-13: SHA-аддендум с #-комментариями"],
        "changes": [
            "C5.1: VacuousRefusalError — отказной гейт без именованной причины сам поднимает нарушение политики",
            "C5.2: GateAntiVacuum.refuse(gate, reason) — единственный способ отказа COMMIT-контура; 10 точек отказа переведены; тексты причин байт-в-байт",
            "C5.3: GATE_REGISTRY — 11 отказных семейств, именованные причины, 51 парный свидетель (honest+refusal)",
            "C5.4: GateAntiVacuum.audit() — механическая сверка реестра",
            "C5.5: T140 мета-гейт — реестр сверен с фактом исполнения всех парных проб",
            "C5.6: T141 — позитивный контроль невыразимости вакуумного отказа",
            "C5.7: усиление refusal-проб T64/T65/T115/T117/T120 — ассерт именованной причины",
            "Task 14: Ш-01/Ш-11/Ш-13 включены в пакет релиза",
        ],
        "note": "Гейты Тела (T01–T23) уже несут парные пробы в каждой паре; их вшивание в реестр — рубеж ревизии Тела. Р-02 (селективный re-bind), Р-03 (типизация claims), Р-04 (байтемпоральность) — в силе.",
        "timestamp_utc": "2026-08-30T00:00:00+00:00",
    }
    (REL / "MANIFEST_v3.10.0.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ── SHA256 с #-комментариями (Ш-13) ──
    lines = ["# SHA256 v3.10.0 release — GNU sha256sum -c совместимо (Ш-13)"]
    for f in sorted(REL.iterdir()):
        if f.is_file() and f.name != "SHA256_v3.10.0.txt":
            lines.append(f"{sha256_file(f)}  {f.name}")
    for f in sorted(ART.iterdir()):
        lines.append(f"{sha256_file(f)}  artifacts/{f.name}")
    (REL / "SHA256_v3.10.0.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("ПАКЕТ ГОТОВ:", REL)
    for f in sorted(REL.rglob("*")):
        if f.is_file():
            print(f"  {f.relative_to(REL)}  {f.stat().st_size} байт")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
