#!/usr/bin/env python3
# TASK174 / Task 35 — spot-check трасс чужаков перед вердиктом прогона 3 (проверяй строкой)
import subprocess, re, os, json

UP = "/home/z/my-project/upload"
MAT = "/home/z/my-project/work/b25_svazka_blind/MATERIAL"
SV = "/home/z/my-project/work/b25_svazka_blind/ДОКУМЕНТ_К_ПРОВЕРКЕ.md"

def sh(p): return os.path.getsize(p)
def wc(p):
    with open(p, "rb") as f: return f.read().count(b"\n")
def grep(pat, path, flags=re.IGNORECASE, maxn=6):
    out = []
    with open(path, "rb") as f:
        data = f.read().decode("utf-8", "replace")
    for i, line in enumerate(data.splitlines(), 1):
        if re.search(pat, line, flags):
            out.append((i, line.strip()[:160]))
            if len(out) >= maxn: break
    return out

res = {}
# 1. RENTA.txt размер/строки (зерно Кольца §12)
renta = os.path.join(MAT, "RENTA.txt")
res["renta_size_lines"] = (sh(renta), wc(renta))

# 2. A_crit: адрес и наличие i_m в артефакте №6
a6 = os.path.join(MAT, "Синтезировать структуру алгоритма.md")
res["a6_acrit"] = grep(r"A_crit", a6, maxn=8)
res["a6_svazka_formul"] = grep(r"СВЯЗКА ФОРМУЛ", a6, maxn=3)
res["a6_i_m"] = grep(r"i_m|i_m,t|im,", a6, maxn=3)
res["a6_d_next"] = grep(r"D_\{?t\+1|D\(t\+1\)", a6, maxn=4)

# 3. Машина [0]-[12]: где маркеры — RENTA.txt или RENTA_1.txt
r1 = os.path.join(MAT, "RENTA_1.txt")
res["renta0_kontrol"] = grep(r"\[0\]\s*КОНТРОЛЬ РЕСУРСА", renta, maxn=2) or "нет в RENTA.txt"
res["renta1_kontrol"] = grep(r"\[0\]\s*КОНТРОЛЬ РЕСУРСА", r1, maxn=2) or "нет в RENTA_1.txt"
res["renta1_perezapusk"] = grep(r"\[12\]\s*ПЕРЕЗАПУСК", r1, maxn=2)
res["renta1_26sekcij"] = grep(r"26\s*секц|26\s*РАЗДЕЛ", r1, maxn=3)
res["renta0_26sekcij"] = grep(r"26\s*секц", renta, maxn=3) or "нет в RENTA.txt"

# 4. Канон В1: независимость носителей
canon = os.path.join(MAT, "POLIMAT_PROMPT_v5.1.2.md")
res["canon_v1_nezav"] = grep(r"[Нн]езависимост", canon, maxn=5)

# 5. Связка §6.1 «независимо пришли» + §7 строка «старше всех институций»
res["sv_nezavisimo"] = grep(r"независимо пришли", SV, maxn=3)
res["sv_starshe_vseh"] = grep(r"старше всех институций", SV, maxn=3)
res["sv_upakovka"] = grep(r"упаковка", SV, maxn=3)

# 6. «11/11» в вердикте прогона 2: какой §
verd2 = os.path.join(MAT, "Б25_ПРОГОН2_ФИНАЛЬНЫЙ_ВЕРДИКТ.md")
res["verd2_11_11"] = grep(r"11/11", verd2, maxn=4)

# 7. Запрос Grok дословно
grok = os.path.join(MAT, "Grok.md")
res["grok_zapros"] = grep(r"КРАСНОЙ НИТЬЮ", grok, maxn=4)

# 8. 220 узлов / 550 связей в Grok.md; 150/350 в ЕДИНОМ СПИСКЕ
res["grok_220"] = grep(r"220", grok, maxn=3)
sp = os.path.join(MAT, "✅ ЕДИНЫЙ СПИСОК.md")
res["sp_150_350"] = grep(r"150\s*узлов", sp, maxn=3)

# 9. №4 «самые первые документы» (опора для «старше всех институций»)
a4 = os.path.join(MAT, "механизм-долговой-ямы-ренты-тысячелетняя-структура.md")
res["a4_pervye_dokumenty"] = grep(r"первые документы|древнейший", a4, maxn=5)
res["a4_kabalnye_knigi"] = grep(r"кабальн", a4, maxn=6)

# 10. Тар: содержимое (№6/№8/№9 внутри?)
lst = subprocess.run(["tar", "-tf", os.path.join(MAT, "..........RENTA.tar")],
                     capture_output=True, text=True).stdout.strip().splitlines()
res["tar_members"] = lst

print(json.dumps(res, ensure_ascii=False, indent=1))
