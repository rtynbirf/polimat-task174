#!/usr/bin/env python3
"""НЕЗАВИСИМАЯ ВЕРИФИКАЦИЯ v1.2 РИД-СОЛОМОН (Task 20): subprocess, диск, подмена, незатронутость v1.1."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

CORE_V12 = Path("/home/z/my-project/download/АРХИВАРИУС_v1.2_РИД_СОЛОМОН.py")
CORE_V11 = Path("/home/z/my-project/download/АРХИВАРИУС_v1.1_ПЕРЕЖИВАНИЕ.py")
WORK = Path("/home/z/my-project/scripts/verify_tmp"); WORK.mkdir(exist_ok=True)
V11_SHA = "497c461d7aa664361111f8b2d633e2ab612444f757ce310af9ffa1aa43aa66f9"

passed, failed = 0, 0
def check(num, cond, desc):
    global passed, failed
    print(f"  {'✓' if cond else '✗'} W{num:02d}: {desc}")
    if cond: passed += 1
    else: failed += 1

def run(lines):
    p = WORK / f"w12_{abs(hash(tuple(lines))) % 10**8}.py"
    p.write_text("\n".join(lines), encoding="utf-8")
    r = subprocess.run([sys.executable, str(p)], capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout + r.stderr

LOAD = ["import sys", "from importlib import util",
        f"spec = util.spec_from_file_location('core', {str(CORE_V12)!r})",
        "core = util.module_from_spec(spec); spec.loader.exec_module(core)"]

print("=" * 70)
print("ВЕРИФИКАЦИЯ АРХИВАРИУС v1.2 РИД-СОЛОМОН (независимая)")
print("=" * 70)

# W01: selftest v1.2
rc, out = run(LOAD + ["r = __import__('subprocess').run([sys.executable, " + repr(str(CORE_V12)) + ", '--selftest'], capture_output=True, text=True)",
                      "print('OK' if '60/60 PASS' in r.stdout and r.returncode == 0 else 'FAIL:' + r.stdout[-150:])"])
check(1, rc == 0 and "OK" in out, "Selftest v1.2 в отдельном процессе: 60/60 PASS")

# W02: v1.1 не тронут
rc, out = run(LOAD + ["r = __import__('subprocess').run([sys.executable, " + repr(str(CORE_V11)) + ", '--selftest'], capture_output=True, text=True)",
                      "print('OK' if '52/52 PASS' in r.stdout and r.returncode == 0 else 'FAIL')"])
check(2, rc == 0 and "OK" in out, "v1.1 не тронута: 52/52 PASS")

# W03: sha256 v1.1
h = hashlib.sha256(CORE_V11.read_bytes()).hexdigest()
check(3, h == V11_SHA, f"sha256 v1.1 совпадает: {h[:16]}...")

# W04: процесс 1 запечатал документ на диск и умер; процесс 2 загрузил и собрал
WHOLE = WORK / "whole12.json"
rc1, out1 = run(LOAD + [
    "a = core.Archivarius()",
    "sealed = a.seal_document('Протокол партии: данные переживают смерть частей.'.encode('utf-8'), 3, 9, 'протокол')",
    "core.Persistence.save(a, " + repr(str(WHOLE)) + ")",
    "print('SEALED', len(sealed))",
])
rc2, out2 = run(LOAD + [
    "a = core.Persistence.load(" + repr(str(WHOLE)) + ")",
    "doc = a.unseal_document(a.shards)",  # все шарды с диска = 9 кусков
    "print('DOC_OK' if doc.startswith('Протокол партии'.encode('utf-8')) else 'DOC_FAIL')",
])
check(4, rc1 == 0 and rc2 == 0 and "DOC_OK" in out2 and "SEALED 9" in out1,
      "Диск: процесс 1 запечатал 9 кусков и умер; процесс 2 загрузил и собрал документ")

# W05: собрать из МИНимальных 3 живых кусков после подмены остальных на диске
bad = json.loads(WHOLE.read_text(encoding="utf-8"))
import base64 as b64
# портим куски 0,1,2,3,4,5 (подменяем b64) — живы 6,7,8 (ровно k=3)
for i in range(6):
    for s in bad["shards"]:
        if s["body"].get("rs") and s["body"]["piece_index"] == i:
            s["body"]["b64"] = b64.b64encode(f"порча{i}".encode()).decode("ascii")
badp = WORK / "spoiled12.json"
badp.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
rc5, out5 = run(LOAD + [
    "a = core.Persistence.load(" + repr(str(badp)) + ")",
    "try:",
    "    doc = a.unseal_document(a.shards)",
    "    print('REBUILT_OK' if 'данные переживают'.encode('utf-8') in doc else 'WRONG')",
    "except core.НедостаточноЧастей as e:",
    "    print('HONEST_REFUSE:', e)",
])
check(5, rc5 == 0 and "REBUILT_OK" in out5,
      "Подмена 6 кусков на диске: живы ровно 3 (паритеты) → документ собран без потерь")

# W06: испортить 7 кусков (живо 2 < k) → честный отказ
bad2 = json.loads(WHOLE.read_text(encoding="utf-8"))
for i in range(7):
    for s in bad2["shards"]:
        if s["body"].get("rs") and s["body"]["piece_index"] == i:
            s["body"]["b64"] = b64.b64encode(f"порча{i}".encode()).decode("ascii")
bad2p = WORK / "spoiled12_hard.json"
bad2p.write_text(json.dumps(bad2, ensure_ascii=False), encoding="utf-8")
rc6, out6 = run(LOAD + [
    "a = core.Persistence.load(" + repr(str(bad2p)) + ")",
    "try:",
    "    a.unseal_document(a.shards)",
    "    print('FAIL_TOLERATED')",
    "except core.НедостаточноЧастей:",
    "    print('HONEST_REFUSE_OK')",
])
check(6, rc6 == 0 and "HONEST_REFUSE_OK" in out6, "Живо 2 < k=3 → честный отказ (не тишина, не ложь)")

# W07: исчерпывающая проверка k=3,n=6 (20 комбинаций) в отдельном процессе
rc7, out7 = run(LOAD + [
    "ok = core.ReedSolomon.exhaustive_check(3, 6, 'экзистенциальная избыточность'.encode('utf-8'))",
    "print('EXHAUSTIVE_OK' if ok else 'EXHAUSTIVE_FAIL')",
])
check(7, rc7 == 0 and "EXHAUSTIVE_OK" in out7, "Исчерпывающе: все 20 комбинаций 'любые 3 из 6' собирают")

# W08: demo EXIT=0 со сценой [10]
r8 = subprocess.run([sys.executable, str(CORE_V12), "--demo"], capture_output=True, text=True, timeout=120)
check(8, r8.returncode == 0 and "РИД-СОЛОМОН" in r8.stdout and "Совпадает с оригиналом: True" in r8.stdout,
      "Demo v1.2: EXIT=0, сцена [10] играет")

# W09: детерминизм двойного selftest
r9a = subprocess.run([sys.executable, str(CORE_V12), "--selftest"], capture_output=True, text=True)
r9b = subprocess.run([sys.executable, str(CORE_V12), "--selftest"], capture_output=True, text=True)
check(9, r9a.returncode == r9b.returncode == 0 and "60/60" in r9a.stdout and "60/60" in r9b.stdout,
      "Двойной selftest: 60/60 оба раза (детерминизм)")

# W10: все импорты ядра (верх + локальные) — только stdlib
import re as _re
src = CORE_V12.read_text(encoding="utf-8")
mods = set()
for l in src.split("\n"):
    l = l.strip()
    m = _re.match(r"^(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)", l)
    if m:
        mods.add(m.group(1))
STDLIB_OK = {"hashlib", "json", "struct", "dataclasses", "typing", "enum", "sys",
             "os", "base64", "math", "itertools", "tempfile"}
foreign = mods - STDLIB_OK
check(10, not foreign, f"Все импорты ядра stdlib: {sorted(mods)}; чужих: {sorted(foreign)}")

print("\n" + "=" * 70)
print(f"ИТОГ ВЕРИФИКАЦИИ: {passed}/10 PASS, {failed} FAIL")
print("=" * 70)
sys.exit(0 if failed == 0 else 1)
