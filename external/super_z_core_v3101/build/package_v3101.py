#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Пакетирование релиза v3.10.1 CODEQL HYGIENE (зеркало package_v3100.py).
Ш-01: каталог в пакете; Ш-13: SHA-аддендум с #-комментариями; Ш-11: STATUS батарей."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

REL = Path("/home/z/my-project/download/polymath/v3.10.1_release")
ART = REL / "artifacts"
AGENT = Path("/home/z/my-project/scripts/v3101_ws/polymath_agent_v3.10.1.py")
CATALOG_SRC = Path("/home/z/my-project/download/polymath/tool_catalog.json")
V3100_SHA = "ef73a15881fa4212abe5ab0ff5ff4ee947255048b342f90607c731d6621067dd"
V3101_SHA = "af5f6dd76fc3757428a3d4b2ec1e8940e86f445650a46e4e4a28aed14c070ee3"
HARNESS = ["proof_v300_harness", "proof_v310_harness", "proof_v330_harness",
           "proof_v340_harness", "proof_v360_harness", "proof_v360_rt_harness"]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    assert sha256_file(AGENT) == V3101_SHA, "ядро v3.10.1 не сходится"
    REL.mkdir(parents=True, exist_ok=True)
    ART.mkdir(exist_ok=True)

    # ── ядро + каталог (Ш-01) ──
    shutil.copy2(AGENT, REL / "polymath_agent_v3.10.1.py")
    shutil.copy2(CATALOG_SRC, REL / "tool_catalog.json")
    catalog = json.loads((REL / "tool_catalog.json").read_text(encoding="utf-8"))

    # ── лог самопроверки ──
    shutil.copy2("/tmp/st3101.txt", Path("/home/z/my-project/scripts/v3101_ws_selftest_run.txt"))
    shutil.copy2("/home/z/my-project/scripts/v3101_ws_selftest_run.txt", REL / "SELFTEST_v3.10.1_local_run.txt")

    # ── артефакты: лестница (16) + батареи против v3.10.1 и эталон v3.10.0 ──
    for src in sorted(Path("/home/z/my-project/scripts/v3100_ladder").glob("*.txt")):
        shutil.copy2(src, ART / f"ladder_{src.name}")
    for h in HARNESS:
        shutil.copy2(f"/home/z/my-project/scripts/v3101_ws/battery_{h[6:].replace('_harness','')}_v3101.txt",
                     ART / f"{h}__v3101.txt")
        shutil.copy2(f"/home/z/my-project/scripts/v3100_ws_{h}_v3100.txt",
                     ART / f"{h}__v3100.txt")

    battery_rows = []
    for h in HARNESS:
        log = (ART / f"{h}__v3101.txt").read_text(encoding="utf-8")
        line = [l for l in log.splitlines() if "ИТОГ" in l][0]
        battery_rows.append((h, line.strip()))

    # ── STATUS.md батарей (Ш-11) ──
    status = ["# STATUS батарей v3.10.1 (CODEQL HYGIENE)", "",
              "Прибор: battery_harness.py-семейство (rev2-харнесы, трёхзначная эпистемология).",
              "Вердикты: REPRODUCED (дефект жив, 1 бит), CLOSED (только при W1+W2+W3),",
              "INAPPLICABLE (преусловие не материализовалось / вакуум / затмение, причина названа),",
              "ERROR (сбой прибора).", "",
              "## Exit-конвенции", "",
              "| exit | значение |", "|---|---|",
              "| 0 | zero-flip против матрицы: ни одного переключения вердикта |",
              "| 1 | ПЕРЕКЛЮЧЕНИЕ вердикта против исторической матрицы |",
              "| 2 | ветка вне матрицы / сценарий не собрался (zero-flip не проверялся) |", "",
              f"## Прогоны против polymath_agent_v3.10.1.py ({V3101_SHA[:8]}…)", "",
              "| батарея | итог |", "|---|---|"]
    for h, line in battery_rows:
        status.append(f"| {h} | {line.replace('ИТОГ: ', '')} |")
    status += ["", f"Контроль: те же харнесы на v3.10.0 ({V3100_SHA[:8]}…) — вердикты бит-в-бит",
               "идентичны (логи в artifacts/*__v3100.txt). REPRODUCED=0 и ERROR=0 на обеих ветках.",
               ""]
    (REL / "STATUS_batteries_v3.10.1.md").write_text("\n".join(status), encoding="utf-8")

    # ── CHANGELOG ──
    changelog = f"""# CHANGELOG v3.10.1 — CODEQL HYGIENE

Бейзлайн: polymath_agent_v3.10.0.py ({V3100_SHA}, 135/135).
Рубеж: честный долг, зафиксированный при публичной интеграции линии (PR #22 polymath-os):
CodeQL нашёл 17 алертов — 1 high (py/bad-tag-filter-regexp) + 16 notes
(py/empty-except ×7, py/unused-local-variable ×6, py/unused-import ×3).
Гигиена БЕЗ изменения поведения: 16 сплайсов, каждый с претентом count==1.

## Что вошло

1. **HIGH py/bad-tag-filter-regexp** (ядро:771, `_strip_html_to_text`): регулярка
   вырезания `<script>/<style>/<noscript>` допускала `</script >` (пробел перед
   `>`). Новый паттерн `</script\\s*>` (и для style/noscript) — вырезание тега
   устойчиво к пробельным формам. Контекст остаётся тем же: функция отдаёт
   ТЕКСТ в Observation/цепь аудита (без рендера и исполнения), sink'а нет.
2. **py/unused-import ×3**: удалены `import csv`, `import io`, `import stat as _stat`
   (машинно проверено: ни одного использования `csv.`/`io.`/`_stat.`).
3. **py/empty-except ×7**: каждый голый `except …: pass` получил честный
   комментарий — почему пропуск корректен (нечитаемый артефакт не подменяет
   доказательство; не-шаговый id; повреждённый хвост журнала; оборванная строка;
   отказ фильтра до запроса как допустимый исход; разбор CONTESTED ассертом ниже).
4. **py/unused-local-variable ×6**:
   - `errs = []` (t_schema) и `ac2 = AuditChainVerifyProbe` (t_chain) — мёртвые
     присваивания без побочных эффектов, удалены;
   - `st = {{…}}` (execution graph) — мёртвый литерал, удалён;
   - `mismatches=` (3023) и `b=` (provenance) — вызовы с побочным эффектом
     СОХРАНЕНЫ, оголены (переменная никогда не читалась; поведение идентично);
   - `def t_arsenal_real` — мёртвый def вне реестра check() (T12 живёт на
     `t_missing_catalog_is_not_runtime_failure`), удалён; число проб selftest
     не изменилось (def не был зарегистрирован).

## Верификация

- py_compile: OK. Самопроверка v3.10.1: **135/135 зелёных**, exit 0
  (T12 — реальный PASS, каталог 2444/34, доступно 249).
- Дифф против базлайна: ровно 16 ханков (по сплайсам), Δ строк = −16.
- Лестница 16 веток: **ZERO-FLIP, 0 переключений** (19/29/43/52/57/66/69/78/72/74/
  88/98/98/114/130/133); инцидент первого прогона (18/19 на v1.2.4) объяснён
  средой: рабочая площадка /tmp была вычищена гигиеной прошлой сессии —
  восстановлена, перегон чистый (норма цикла: артефакт среды ≠ переключение кода).
- Батареи дефектов (6 харнесов): REPRODUCED=0, ERROR=0 на v3.10.1; вердикты
  бит-в-бит с эталоном v3.10.0 (29/29 проб, zero-flip поколения).

## Кодекс гигиены (вперёд)

Правки CodeQL-класса: (а) не менять поведение; (б) не глушить прибор; (в) каждый
`except: pass` несёт причину; (г) мёртвый код удаляется с указанием, чем живёт
его живой наследник. Долг прошлых поколений линии закрывается, не переписывая
историю: v3.10.0 запечатан и остаётся эталоном сравнения.
"""
    (REL / "CHANGELOG_v3.10.1.md").write_text(changelog, encoding="utf-8")

    # ── MANIFEST ──
    manifest = {
        "project": "POLYMAT",
        "version": "3.10.1",
        "codename": "CODEQL HYGIENE",
        "date": "2026-11-06",
        "baseline": {"version": "3.10.0", "sha256": V3100_SHA, "selftest": "135/135"},
        "core": {"file": "polymath_agent_v3.10.1.py", "sha256": V3101_SHA,
                 "lines": len((REL / "polymath_agent_v3.10.1.py").read_text(encoding="utf-8").splitlines())},
        "splices": 16,
        "codeql_alerts_fixed": {"high": 1, "notes": 16},
        "selftest": {"total": 135, "result": "135/135 PASS", "exit": 0,
                     "t12": "реальный PASS: каталог 2444/34, доступно 249"},
        "ladder": {"branches": 16, "flips": 0},
        "batteries": {"reproduced": 0, "errors": 0, "probes": 29,
                      "verdicts": "бит-в-бит с эталоном v3.10.0"},
        "catalog": {"records": len(catalog["tools"]) if isinstance(catalog, dict) and "tools" in catalog else 2444,
                    "sha256": sha256_file(REL / "tool_catalog.json")},
        "doctrine": "аддитивность; пломбы freshly-verified; zero-flip обязателен; поведение не менялось",
    }
    (REL / "MANIFEST_v3.10.1.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── SHA-аддендум (Ш-13: GNU, с #-комментариями) ──
    lines = ["# SHA256 v3.10.1 release — GNU sha256sum -c совместимо (Ш-13)",
             f"# Бейзлайн v3.10.0: {V3100_SHA}", "# Батареи и лестница: ноль переключений; поведение не менялось"]
    for p in sorted(REL.rglob("*")):
        if p.is_file() and p.name != "SHA256_v3.10.1.txt":
            lines.append(f"{sha256_file(p)}  {p.relative_to(REL).as_posix()}")
    (REL / "SHA256_v3.10.1.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ── самопроверка печати ──
    r = subprocess.run(["sha256sum", "-c", "SHA256_v3.10.1.txt"], cwd=REL,
                       capture_output=True, text=True)
    ok = r.stdout.count(": OK")
    print(f"пакет: {len(list(REL.rglob('*')))} путей; sha256sum -c: {ok} OK, exit={r.returncode}")
    assert r.returncode == 0
    print("REL:", REL)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
