#!/usr/bin/env python3
"""
НЕЗАВИСИМАЯ ВЕРИФИКАЦИЯ v1.1 (Task 19): adversarial, subprocess, тамперинг, неизменность v1.0r.
12 проверок. Вердикт печатается машиной.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

CORE_V11 = Path("/home/z/my-project/download/АРХИВАРИУС_v1.1_ПЕРЕЖИВАНИЕ.py")
CORE_V10R = Path("/home/z/my-project/download/АРХИВАРИУС_v1.0r_ЯДРО.py")
WORK = Path("/home/z/my-project/scripts/verify_tmp")
WORK.mkdir(exist_ok=True)

V10R_SHA = "e2512b28e449eb1b6dc78799b33bc43ac6b4cdb4c004118928679e7f6d6f4528"

passed, failed = 0, 0

def check(num, cond, desc):
    global passed, failed
    mark = "✓" if cond else "✗"
    if cond:
        passed += 1
    else:
        failed += 1
    print(f"  {mark} V{num:02d}: {desc}")

def run(script_lines, args=None):
    """Запустить временный python-скрипт subprocess-ом. Вернуть (rc, out)."""
    p = WORK / f"scene_{abs(hash(tuple(script_lines))) % 10**8}.py"
    p.write_text("\n".join(script_lines), encoding="utf-8")
    cmd = [sys.executable, str(p)] + (args or [])
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout + r.stderr

print("=" * 70)
print("ВЕРИФИКАЦИЯ АРХИВАРИУС v1.1 ПЕРЕЖИВАНИЕ (независимая, subprocess)")
print("=" * 70)

# --- 1. Selftest v1.1 (subprocess) -------------------------------------------
rc, out = run(["import subprocess, sys",
               f"r = subprocess.run([sys.executable, {str(CORE_V11)!r}, '--selftest'], capture_output=True, text=True)",
               "ok = '52/52 PASS' in r.stdout and r.returncode == 0",
               "print('SELFTEST_OK' if ok else 'SELFTEST_FAIL:' + r.stdout[-200:] + r.stderr[-200:])"])
check(1, rc == 0 and "SELFTEST_OK" in out, f"Selftest v1.1 в отдельном процессе: 52/52 PASS {(out[-200:] if 'SELFTEST_OK' not in out else '')}")

# --- 2. Selftest v1.0r не сломан ----------------------------------------------
rc, out = run(["import subprocess, sys",
               f"r = subprocess.run([sys.executable, {str(CORE_V10R)!r}, '--selftest'], capture_output=True, text=True)",
               "ok = '36/36 PASS' in r.stdout and r.returncode == 0",
               "print('SELFTEST_OK' if ok else 'SELFTEST_FAIL:' + r.stdout[-200:] + r.stderr[-200:])"])
check(2, rc == 0 and "SELFTEST_OK" in out, "Реконструкция v1.0r не тронута: 36/36 PASS")

# --- 3. sha256 v1.0r неизменен -------------------------------------------------
h = hashlib.sha256(CORE_V10R.read_bytes()).hexdigest()
check(3, h == V10R_SHA, f"sha256 v1.0r совпадает с зафиксированным: {h[:16]}...")

# --- 4. ПРОЦЕСС 1: создать Целое, сохранить, умереть ---------------------------
WHOLE = WORK / "whole.json"
rc1, out1 = run([
    "import sys, json",
    f"sys.path.insert(0, {str(CORE_V11.parent)!r})",
    "from importlib import util",
    f"spec = util.spec_from_file_location('core', {str(CORE_V11)!r})",
    "core = util.module_from_spec(spec); spec.loader.exec_module(core)",
    "a = core.Archivarius()",
    "a.birth('летопись', {'содержимое': 'Task 19: переживание доказано'})",
    "a.birth('суд', {'содержимое': 'вердикты append-only'})",
    "d = core.Persistence.save(a, " + repr(str(WHOLE)) + ")",
    "print(d, a.manifest.root())",
])
last1 = out1.strip().split("\n")[-1] if rc1 == 0 else ""
digest1 = last1.split(" ")[0]
root1 = last1.split(" ")[1] if " " in last1 else ""
check(4, rc1 == 0 and WHOLE.exists(), "Процесс 1: Целое создано и сохранено (process died after)")

# --- 5. ПРОЦЕСС 2 (независимый): загрузить, судить ЧАСТЬ, корень сверить --------
rc2, out2 = run([
    "import sys",
    "from importlib import util",
    f"spec = util.spec_from_file_location('core', {str(CORE_V11)!r})",
    "core = util.module_from_spec(spec); spec.loader.exec_module(core)",
    "a = core.Persistence.load(" + repr(str(WHOLE)) + ")",
    "s = a.shards[0]",
    "claim = {'genome_hash': a.genome.hash(), 'manifest_root': s.manifest_root,",
    "          'index': s.index, 'merkle_path': s.merkle_path,",
    "          'body_hash': core.hash_obj(a.manifest.entries[s.index].data)}",
    "v = a.judge(claim)",
    "print(f'ROOT={a.manifest.root()} VERDICT={v.value}')",
])
line = [l for l in out2.split("\n") if l.startswith("ROOT=")]
ok5 = rc2 == 0 and line and line[0].startswith("ROOT=" + root1) and "VERDICT=ЧАСТЬ" in line[0]
check(5, ok5, f"Процесс 2 (новый python): LOAD → суд ЧАСТЬ → корень совпадает [{out2[-300:] if not ok5 else 'ok'}]")

# --- 6. Тамперинг записи → LoadError (в новом процессе) -------------------------
bad = json.loads(WHOLE.read_text(encoding="utf-8"))
bad["manifest"]["entries"][1]["data"]["body"]["содержимое"] = "ПОДДЕЛКА"
badp = WORK / "tampered.json"
badp.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
rc6, out6 = run([
    "import sys",
    "from importlib import util",
    f"spec = util.spec_from_file_location('core', {str(CORE_V11)!r})",
    "core = util.module_from_spec(spec); spec.loader.exec_module(core)",
    "try:",
    "    core.Persistence.load(" + repr(str(badp)) + ")",
    "    print('NO_ERROR')",
    "except core.LoadError as e:",
    "    print('LOAD_ERROR_OK')",
])
check(6, rc6 == 0 and "LOAD_ERROR_OK" in out6, "Тамперинг записи пойман: LoadError (пересчёт хэшей)")

# --- 7. Подмена генома → LoadError ----------------------------------------------
bad2 = json.loads(WHOLE.read_text(encoding="utf-8"))
bad2["genome"]["rules"]["Г1"] = "Украдённый геном"
bad2p = WORK / "tampered_genome.json"
bad2p.write_text(json.dumps(bad2, ensure_ascii=False), encoding="utf-8")
rc7, out7 = run([
    "import sys",
    "from importlib import util",
    f"spec = util.spec_from_file_location('core', {str(CORE_V11)!r})",
    "core = util.module_from_spec(spec); spec.loader.exec_module(core)",
    "try:",
    "    core.Persistence.load(" + repr(str(bad2p)) + ")",
    "    print('NO_ERROR')",
    "except core.LoadError:",
    "    print('LOAD_ERROR_OK')",
])
check(7, rc7 == 0 and "LOAD_ERROR_OK" in out7, "Подмена генома поймана: LoadError")

# --- 8. Подмена корня шарда → LoadError ------------------------------------------
bad3 = json.loads(WHOLE.read_text(encoding="utf-8"))
bad3["shards"][0]["manifest_root"] = "0" * 64
bad3p = WORK / "tampered_root.json"
bad3p.write_text(json.dumps(bad3, ensure_ascii=False), encoding="utf-8")
rc8, out8 = run([
    "import sys",
    "from importlib import util",
    f"spec = util.spec_from_file_location('core', {str(CORE_V11)!r})",
    "core = util.module_from_spec(spec); spec.loader.exec_module(core)",
    "try:",
    "    core.Persistence.load(" + repr(str(bad3p)) + ")",
    "    print('NO_ERROR')",
    "except core.LoadError:",
    "    print('LOAD_ERROR_OK')",
])
check(8, rc8 == 0 and "LOAD_ERROR_OK" in out8, "Подмена корня рождения шарда поймана: LoadError")

# --- 9. Только stdlib ------------------------------------------------------------
imports = [l.strip() for l in CORE_V11.read_text(encoding="utf-8").split("\n")
           if l.strip().startswith(("import ", "from ")) and not l.strip().startswith(("import os", "import tempfile"))]
body_imports = sorted(set(l for l in imports))
check(9, all(any(mod in l for mod in ("hashlib", "json", "struct", "dataclasses", "typing", "enum", "sys"))
             for l in body_imports), "Зависимости: только stdlib (hashlib, json, struct, dataclasses, typing, enum, sys)")

# --- 10. Demo v1.1: EXIT=0 -------------------------------------------------------
rc10 = subprocess.run([sys.executable, str(CORE_V11), "--demo"], capture_output=True, text=True, timeout=120)
check(10, rc10.returncode == 0 and "ПЕРЕЖИВАНИЕ" in rc10.stdout and "КОНФЛИКТ-ДЫХАНИЕ" in rc10.stdout,
      "Demo v1.1: EXIT=0, сцены [8] ПЕРЕЖИВАНИЕ и [9] КОНФЛИКТ-ДЫХАНИЕ играются")

# --- 11. Детерминизм selftest: повторный прогон даёт тот же итог -----------------
r11a = subprocess.run([sys.executable, str(CORE_V11), "--selftest"], capture_output=True, text=True)
r11b = subprocess.run([sys.executable, str(CORE_V11), "--selftest"], capture_output=True, text=True)
check(11, r11a.returncode == r11b.returncode == 0 and "52/52" in r11a.stdout and "52/52" in r11b.stdout,
      "Двойной прогон selftest: 52/52 PASS оба раза (детерминизм)")

# --- 12. Суд-журнал append-only переживает диск -----------------------------------
rc12, out12 = run([
    "import sys",
    "from importlib import util",
    f"spec = util.spec_from_file_location('core', {str(CORE_V11)!r})",
    "core = util.module_from_spec(spec); spec.loader.exec_module(core)",
    "a = core.Persistence.load(" + repr(str(WHOLE)) + ")",
    "n0 = len(a.manifest.entries)",
    "a.judge_recorded({})",
    "core.Persistence.save(a, " + repr(str(WHOLE)) + ")  # ПЕРЕЗАПИСЫВАЕМ файл новым состоянием",
    "b = core.Persistence.load(" + repr(str(WHOLE)) + ")  # и загружаем заново",
    "journal = [e.data['verdict'] for e in b.manifest.entries if e.data.get('type') == 'verdict']",
    "ok = len(b.manifest.entries) == n0 + 1 and journal == ['ОТКАЗ']",
    "print('JOURNAL_OK' if ok else 'JOURNAL_FAIL')",
])
check(12, rc12 == 0 and "JOURNAL_OK" in out12, "Суд-журнал: verdict-запись survives save/load (append-only)")

print("\n" + "=" * 70)
print(f"ИТОГ ВЕРИФИКАЦИИ: {passed}/12 PASS, {failed} FAIL")
print("=" * 70)
sys.exit(0 if failed == 0 else 1)
