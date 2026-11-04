#!/usr/bin/env python3
# TASK174 / Task 35 — подготовка слепой руки для Б25.8-прогона на связке КРАСНАЯ_НИТЬ
# Принцип: byte-invariant материал (байт-в-бит копии), никакого контекста линии рядом.
import hashlib, os, shutil, subprocess, json

DL = "/home/z/my-project/download"
UP = "/home/z/my-project/upload"
TAR = os.path.join(UP, "..........RENTA.tar")
STAGE = "/home/z/my-project/work/b25_svazka_blind"

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

# 1) Чистая сборка стейджинга
if os.path.exists(STAGE):
    shutil.rmtree(STAGE)
MAT = os.path.join(STAGE, "MATERIAL")
os.makedirs(MAT)

# 2) Документ под проверкой (копия связки)
doc_src = os.path.join(DL, "КРАСНАЯ_НИТЬ_СВЯЗКА.md")
doc_dst = os.path.join(STAGE, "ДОКУМЕНТ_К_ПРОВЕРКЕ.md")
shutil.copy2(doc_src, doc_dst)

# 3) Распаковка RENTA.tar (байт-инвариантно) в MATERIAL
subprocess.run(["tar", "-xf", TAR, "-C", MAT], check=True)

# 4) Отдельные артефакты: №6, №8, №9 из upload; №10, №11 из download
for name in ["Синтезировать структуру алгоритма.md", "Grok.md", "✅ ЕДИНЫЙ СПИСОК.md"]:
    shutil.copy2(os.path.join(UP, name), os.path.join(MAT, name))
for name in ["POLIMAT_PROMPT_v5.1.2.md", "Б25_ПРОГОН2_ФИНАЛЬНЫЙ_ВЕРДИКТ.md"]:
    shutil.copy2(os.path.join(DL, name), os.path.join(MAT, name))
# №12 — сам tar, байт-в-бит
shutil.copy2(TAR, os.path.join(MAT, "..........RENTA.tar"))

# 5) Пересверка 12 пломб из §1 связки против реальных файлов
artifacts = {
    1:  ("RENTA.txt", os.path.join(MAT, "RENTA.txt")),
    2:  ("RENTA_1.txt", os.path.join(MAT, "RENTA_1.txt")),
    3:  ("Машина_долговой_ямы_исследование.docx", os.path.join(MAT, "Машина_долговой_ямы_исследование.docx")),
    4:  ("механизм-долговой-ямы-ренты-тысячелетняя-структура.md", os.path.join(MAT, "механизм-долговой-ямы-ренты-тысячелетняя-структура.md")),
    5:  ("2. «Должник возобновляется через родильное отделение и запись».md", os.path.join(MAT, "2. «Должник возобновляется через родильное отделение и запись».md")),
    6:  ("Синтезировать структуру алгоритма.md", os.path.join(MAT, "Синтезировать структуру алгоритма.md")),
    7:  ("ЕДИНОЕ_КОЛЬЦО_первичный_документ.md", os.path.join(MAT, "ЕДИНОЕ_КОЛЬЦО_первичный_документ.md")),
    8:  ("Grok.md", os.path.join(MAT, "Grok.md")),
    9:  ("✅ ЕДИНЫЙ СПИСОК.md", os.path.join(MAT, "✅ ЕДИНЫЙ СПИСОК.md")),
    10: ("POLIMAT_PROMPT_v5.1.2.md", os.path.join(MAT, "POLIMAT_PROMPT_v5.1.2.md")),
    11: ("Б25_ПРОГОН2_ФИНАЛЬНЫЙ_ВЕРДИКТ.md", os.path.join(MAT, "Б25_ПРОГОН2_ФИНАЛЬНЫЙ_ВЕРДИКТ.md")),
    12: ("..........RENTA.tar", os.path.join(MAT, "..........RENTA.tar")),
}
expected = {
    1:  "52628ff10d81b26b24d937005087c4fc07d6422b0c0940310707694478d8b9f2",
    2:  "2992a27c3ed93f6f377a0a7253ca9939562f77d34246452850b14d4c38fde8fd",
    3:  "4a62498e225ddac31010d837c429a845e0f48b2f251721f36cf6b0be57a15ff8",
    4:  "4ac5a7dc426a4199b17305905b8723266076e2c1de92a1cc470e8c2f2526b255",
    5:  "7259b5d626b89b56b33b670928996ef730b3a83b07750746eb49e6fc369a24c9",
    6:  "c988ca5c4368d4eaf89a77da266df2191dcff939f13a5d2ed98bbcc236f41f97",
    7:  "5ca398eefd71a46b10659ef61dc97281789610a5f80fc985bafef8d3121894db",
    8:  "c208dd864252f49514d44b89c3c5fff71add2cb96f04c57d125be92090cea13d",
    9:  "9c625135a0e7a4be79660119fd298018b0436d4f19eb172fe8969dc7c73433bb",
    10: "9384b44a6843a8321e5bc267880d387039317bd8b08acb65e17bf33a16980dc7",
    11: "981d2c85ef33f9fb2225cb89f5376d87f3c39fcab70ce596f866ad260370d06b",
    12: "13a5227794b8b1ab0eadbb3a60dfb602c5798764f91433e2a144054ef969cbca",
}
report = {}
for k, (label, path) in artifacts.items():
    if not os.path.exists(path):
        report[k] = {"file": label, "present": False, "match": None}
        continue
    got = sha256(path)
    report[k] = {"file": label, "present": True, "match": got == expected[k], "computed": got}

ok = all(v["match"] for v in report.values() if v["present"])
out = {"doc_sha256": sha256(doc_dst), "doc_src_sha256": sha256(doc_src),
       "all_12_match": ok, "per_artifact": report}
print(json.dumps(out, ensure_ascii=False, indent=1))
with open("/home/z/my-project/work/b25_svazka_blind/_prep_report.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("STAGE:", STAGE)
print("MATERIAL listing:")
for p in sorted(os.listdir(MAT)):
    print("  -", p)
