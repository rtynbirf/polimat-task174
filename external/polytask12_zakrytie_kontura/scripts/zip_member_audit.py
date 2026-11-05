#!/usr/bin/env python3
"""Аудит zip-контейнеров: хеш каждого члена ПРЯМО ИЗ АРХИВА (без экстракции),
сравнение с распакованными копиями на диске. Закрывающая верификация носителей."""
import hashlib, json, sys, zipfile
from pathlib import Path

ROOT = Path("/home/z/my-project")
ZIPS = [
    ROOT / "upload/POLYMATH_ARCHIVARIUS_CHAT_ALGORITHMS_2026-09-01.zip",
    ROOT / "download/inner_archive/POLYMATH_CHAT_ALGORITHMS_ARCHIVE_2026-09-01.zip",
]

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

report = {}
for zp in ZIPS:
    if not zp.exists():
        report[zp.name] = {"error": "zip не найден"}
        continue
    entry = {"container_sha256": sha(zp.read_bytes()), "container_bytes": zp.stat().st_size, "members": {}}
    try:
        with zipfile.ZipFile(zp) as z:
            bad = z.testzip()
            entry["crc_test"] = "PASS" if bad is None else f"FAIL:{bad}"
            for info in z.infolist():
                data = z.read(info)
                m = {"zip_member_sha256": sha(data), "zip_member_bytes": len(data)}
                # сравнить с распакованной копией
                for base in [ROOT / "download/zip_extract", ROOT / "download/inner_archive/unpacked/polymath_archive"]:
                    cand = base / info.filename
                    if cand.exists():
                        disk = sha(cand.read_bytes())
                        m[f"disk_copy@{base.name}"] = disk
                        m[f"match@{base.name}"] = (disk == m["zip_member_sha256"])
                entry["members"][info.filename] = m
    except Exception as e:
        entry["error"] = repr(e)
    report[zp.name] = entry

print(json.dumps(report, ensure_ascii=False, indent=1))
