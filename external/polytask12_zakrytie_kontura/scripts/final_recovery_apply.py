#!/usr/bin/env python3
"""RECOVERY APPLY: восстановление 9 обнулённых файлов из верифицированных источников
(git-блобы, zip-члены), с квитанциями before/after и двойной перепроверкой байтов."""
import hashlib, json, zipfile
from pathlib import Path

ROOT = Path("/home/z/my-project")
EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
UZIP = ROOT / "upload/POLYMATH_ARCHIVARIUS_CHAT_ALGORITHMS_2026-09-01.zip"
IZIP = ROOT / "download/inner_archive/POLYMATH_CHAT_ALGORITHMS_ARCHIVE_2026-09-01.zip"

def git_bytes(spec: str) -> bytes:
    return subprocess_bytes(["git", "-C", str(ROOT), "cat-file", "blob", spec])

def subprocess_bytes(cmd):
    import subprocess
    r = subprocess.run(cmd, capture_output=True, check=True)
    return r.stdout

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def zip_member(zp: Path, suffix: str) -> bytes:
    with zipfile.ZipFile(zp) as z:
        names = [n for n in z.namelist() if n.endswith(suffix)]
        assert len(names) == 1, f"{suffix}: {names}"
        return z.read(names[0])

PLANS = [
    # (целевой путь, источник-функция, эталон sha256 (полный или префикс+), описание источника)
    ("download/portable_polymath.py",
     lambda: git_bytes("f27e7695ae6939f01dca1b48d12ce5341928325c"),
     "4619289c19ef30402820defec3f642eb32fadad3ccc025e489d86c5eec44817e",
     "git blob f27e7695 (content-addressed)"),
    ("download/inventory_diff_task20.json",
     lambda: git_bytes("2eb99ec608d174b95e6527adce5e8d7db7f8a9cf"),
     "185487ae6b5703ffa8e921d8c6851f3914828f4dca0b180c5053806ec1861289",
     "git blob 2eb99ec6 (content-addressed)"),
    ("download/inner_archive/unpacked/polymath_archive/╨¥╨╛╨▓╤ï╨╣ ╤é╨╡╨║╤ü╤é╨╛╨▓╤ï╨╣ ╨┤╨╛╨║╤â╨╝╨╡╨╜╤é (4).txt",
     lambda: zip_member(IZIP, "(4).txt"),
     "cdbbba25153a7ed303b525f93a0faff8e3aaab5684db295fda86bad62400c0de",
     "inner zip member (MANIFEST ref)"),
    ("download/zip_extract/WORKFLOW_REPRODUCED.json",
     lambda: zip_member(UZIP, "WORKFLOW_REPRODUCED.json"),
     "9b0c50b9a269cd4bf7dee66e2497a475ee0304816a4de025f1051b493b9a8b46",
     "upload zip member (SHA256SUMS ref)"),
    ("download/zip_extract/verify_ARCHIVARIUS_v3.5.0.py",
     lambda: zip_member(UZIP, "verify_ARCHIVARIUS_v3.5.0.py"),
     "72c2ab5efeded4819d3886fd71fed9c6d233763e4a7f12047d7ac816600c3fd7",
     "upload zip member (SHA256SUMS ref)"),
    ("download/POLYMATH_BOOTSTRAP_AMENDMENTS_v1.1.md",
     lambda: git_bytes("4ac7dce26e0da4fc2dba5407380a69e135926ca4"),
     "d2fe5b2b", "git blob 4ac7dce3 (prefix ref d2fe5b2b из worklog)"),
    ("download/v2_extract/ARCHIVARIUS_POLYMATH_v2.py",
     lambda: git_bytes("0b0448fa7f12e02370d4ea60ecfea9d95dd27fa8"),
     "e0db0b5b", "git blob 0b0448fa (prefix ref e0db0b5b из worklog)"),
    ("download/POLYMATH_BOOTSTRAP_v1.1_PROMPT.txt",
     lambda: git_bytes("dab32e38bb1c6ca25894e67a51ec2d6b60ff3fb8"),
     None, "git blob dab32e38 (критерий 17056 байт; приёмка чекером после)"),
    ("download/proof_envelope_spec_v0.json",
     lambda: subprocess_bytes(["git", "-C", str(ROOT), "cat-file", "blob",
                               "f2a3905:download/proof_envelope_spec_v0.json"]),
     None, "git commit-path f2a3905:download/proof_envelope_spec_v0.json"),
]

receipts = []
for rel, src, ref, src_desc in PLANS:
    tgt = ROOT / rel
    before = sha(tgt.read_bytes()) if tgt.exists() else None
    data = src()
    h = sha(data)
    # запись с двойной перепроверкой
    tgt.write_bytes(data)
    after = sha(tgt.read_bytes())
    assert after == h, f"перепроверка записи не сошлась: {rel}"
    if ref:
        ok = (after == ref) if len(ref) == 64 else after.startswith(ref)
    else:
        ok = None
    receipts.append({
        "path": rel,
        "before_sha256": before,
        "before_empty": before == EMPTY,
        "source": src_desc,
        "source_bytes": len(data),
        "after_sha256": after,
        "ref": ref,
        "ref_match": ok,
    })
    status = "MATCH-REF" if ok else ("SIZE/CONTENT-CRITERION" if ok is None else "REF-MISMATCH!")
    print(f"[{status}] {rel}: {len(data)} байт, after={after[:12]}…")

Path("/tmp/repair_receipts.json").write_text(
    json.dumps(receipts, ensure_ascii=False, indent=1), encoding="utf-8")
print("\nквитанции: /tmp/repair_receipts.json")
