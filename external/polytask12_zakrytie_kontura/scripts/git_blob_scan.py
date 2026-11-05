#!/usr/bin/env python3
"""RECOVERY SCAN (read-only): карта всех git-блобов sha256→blob; кандидаты на восстановление обнулённых файлов."""
import hashlib, json, subprocess
from pathlib import Path

ROOT = Path("/home/z/my-project")

def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, check=True).stdout

objs = git("cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype)").split()
blobs = objs[0::2] if False else [objs[i] for i in range(0, len(objs), 2) if objs[i+1] == "blob"]

sha_map = {}  # sha256 -> [ (blob, size) ]
for b in blobs:
    data = subprocess.run(["git", "-C", str(ROOT), "cat-file", "blob", b],
                          capture_output=True, check=True).stdout
    h = hashlib.sha256(data).hexdigest()
    sha_map.setdefault(h, []).append((b, len(data)))

print(f"всего blob'ов: {len(blobs)}, уникальных sha256: {len(sha_map)}")

targets_full = {
    "portable_polymath.py": "4619289c19ef30402820defec3f642eb32fadad3ccc025e489d86c5eec44817e",
    "inventory_diff_task20.json": "185487ae6b5703ffa8e921d8c6851f3914828f4dca0b180c5053806ec1861289",
    "corpus_Новый_текстовый_документ(4).txt": "cdbbba25153a7ed303b525f93a0faff8e3aaab5684db295fda86bad62400c0de",
    "zip_WORKFLOW_REPRODUCED.json": "9b0c50b9a269cd4bf7dee66e2497a475ee0304816a4de025f1051b493b9a8b46",
    "zip_verify_ARCHIVARIUS_v3.5.0.py": "72c2ab5efeded4819d3886fd71fed9c6d233763e4a7f12047d7ac816600c3fd7",
}
targets_prefix = {
    "AMENDMENTS_v1.1.md": "d2fe5b2b",
    "v2_extract_ARCHIVARIUS_POLYMATH_v2.py": "e0db0b5b",
}
print("\n=== ПОЛНЫЕ SHA (точные) ===")
for name, h in targets_full.items():
    hits = sha_map.get(h, [])
    print(f"{name}: {'FOUND ' + str(hits) if hits else 'NOT-IN-GIT'}")

print("\n=== ПРЕФИКСЫ ===")
for name, pref in targets_prefix.items():
    hits = [(b, s) for h, bs in sha_map.items() if h.startswith(pref) for b, s in bs]
    print(f"{name} ({pref}…): {hits if hits else 'NOT-IN-GIT'}")

print("\n=== PROMPT v1.1 (критерий: 17056 байт, 184 строки) ===")
for h, bs in sha_map.items():
    for b, size in bs:
        if size == 17056:
            data = subprocess.run(["git", "-C", str(ROOT), "cat-file", "blob", b],
                                  capture_output=True, text=True, check=True).stdout
            print(f"candidate blob={b} size={size} lines={data.count(chr(10))+1} head={data[:60]!r}")

print("\n=== SPEC proof_envelope (JSON c SPEC_ONLY) ===")
for h, bs in sha_map.items():
    for b, size in bs:
        if 200 < size < 20000:
            data = subprocess.run(["git", "-C", str(ROOT), "cat-file", "blob", b],
                                  capture_output=True, text=True, check=True).stdout
            if "SPEC_ONLY" in data and "proof_envelope" in data.lower():
                print(f"candidate blob={b} size={size} head={data[:80]!r}")

print("\n=== git-история обнулённых путей ===")
for p in ["download/portable_polymath.py", "download/inventory_diff_task20.json",
          "download/POLYMATH_BOOTSTRAP_v1.1_PROMPT.txt", "download/POLYMATH_BOOTSTRAP_AMENDMENTS_v1.1.md",
          "download/proof_envelope_spec_v0.json", "download/v2_extract/ARCHIVARIUS_POLYMATH_v2.py"]:
    r = subprocess.run(["git", "-C", str(ROOT), "log", "--oneline", "--", p],
                       capture_output=True, text=True)
    print(f"{p}: {r.stdout.strip().splitlines()[:3]}")
