#!/usr/bin/env python3
# ПОЛИМАТ · Б25.8 · финальная сверка перед вердиктом (Task 33)
# Проверка: канон v5.1.2, состав CORPUS_B25, слепая рука, zip-пломбы, экспонат USER.
import hashlib, os, json

BASE = "/home/z/my-project/download"
UPLOAD = "/home/z/my-project/upload"

EXPECT_FILES = {
    "POLIMAT_PROMPT_v5.1.2.md":        "9384b44a6843a8321e5bc267880d387039317bd8b08acb65e17bf33a16980dc7",
    "POLIMAT_B25_PREREG_R38.md":       "7214d9f0ba4e93e7e770a70f4ed9ced02fd46b33071e0b53fd399eb9180039c8",
    "POLIMAT_DELTA_v5.1.2_D20-D26.md": "ea6153d6f33de31c6d7ab0482a7bc731708080336bbd9119d0294a24e732f39a",
    "POLIMAT_PROMPT_v5.1.1_FROZEN.md": "5711d74a16b435f1a3aab101da6c5591115a6885d2ba57c65451f66d477f804f",
    "POLIMAT_PROMPT_v5.1_CANDIDATE.md":"b98746cc007eb3badb8119545abaa64bcf3daeecf1742636b9c68b3569471cb5",
    "POLIMAT_PROMPT_v5_ФИНАЛ.md":      "f57af58b20d0c68f41dc2421809106690312eb405dde439e7276c2cc44d188cc",
    "TRAPS_MATERIAL.md":               "992023000cef621f512ecb3b2e352d0ec179ccad356e84fe3bb8c7ef20b34304",
    "Б25_ПРОГОН1_ВЕРДИКТ.md":          "26f461315008156670b4d0278c3965b1d2c5d8e439916dd1f981e832e64ba777",
    "БИТ_ДИФ_v5.1.1_→_v5.1.2.md":      "3e06e3c4d260304c08ec74d3827b846da77c7f72e990fd101528fe5b452270eb",
}
EXPECT_ZIPS = {
    "CORPUS_B25.zip":     "75892a475f9145b1679778f47c8124ef2a918edc18610142925d757fc851facf",
    "B25.8_BLIND_ARM.zip":"bb85d6300f181361551c52e493898fbc7bb3ddfd7ead48ededf51997cf3f53e8",
}

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

report = {"files": {}, "zips": {}, "blind_arm": {}, "exhibit": {}, "pass": True}

# 1) Канонические файлы в корне download/ и в пакете CORPUS_B25/
for name, exp in EXPECT_FILES.items():
    row = {}
    for where, root in (("download", BASE), ("CORPUS_B25", os.path.join(BASE, "CORPUS_B25"))):
        p = os.path.join(root, name)
        if os.path.exists(p):
            got = sha256(p)
            row[where] = {"got": got, "match": got == exp}
            if got != exp:
                report["pass"] = False
        else:
            row[where] = {"got": None, "match": False}
            report["pass"] = False
    report["files"][name] = row

# 2) Слепая рука
blind_expect = {
    "POLIMAT_PROMPT_v5.1.2.md": EXPECT_FILES["POLIMAT_PROMPT_v5.1.2.md"],
    "TRAPS_MATERIAL.md": EXPECT_FILES["TRAPS_MATERIAL.md"],
}
for name, exp in blind_expect.items():
    p = os.path.join(BASE, "B25.8_BLIND_ARM", name)
    got = sha256(p) if os.path.exists(p) else None
    report["blind_arm"][name] = {"got": got, "match": got == exp}
    if got != exp:
        report["pass"] = False

# 3) Пломбы zip (до пересборки — контроль неизменности задачей 32)
for name, exp in EXPECT_ZIPS.items():
    p = os.path.join(BASE, name)
    got = sha256(p) if os.path.exists(p) else None
    report["zips"][name] = {"got": got, "match_task32": got == exp}

# 4) Экспонат USER (сторонний манифест N+1) — фиксация как есть
ex = os.path.join(UPLOAD, "CORPUS_MANIFEST.md")
if os.path.exists(ex):
    report["exhibit"]["upload/CORPUS_MANIFEST.md"] = sha256(ex)

print(json.dumps(report, ensure_ascii=False, indent=2))
