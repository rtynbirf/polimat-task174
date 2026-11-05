#!/usr/bin/env python3
# РАУНД 38. Замер носителя 1.txt и перекрёстная проверка вердикта Р37.
import hashlib, re, json

P = "/home/z/my-project/upload/1.txt"
data = open(P, "rb").read()
size = len(data)
sha = hashlib.sha256(data).hexdigest()
lines = data.decode("utf-8", errors="replace").splitlines()
text = "\n".join(lines)
norm = text.replace("\u2011", "-").replace("\u2013", "-")  # неразрывные дефисы

name_patterns = [
    ("Qwen3.7",      r"0\.1\.\s*Qwen3\.7"),
    ("Luna#1",       r"\*{0,2}0\.1\.\*{0,2}\s*\[В\]\s*\*{0,2}GPT-5\.6 Luna\*{0,2}"),
    ("DeepSeek-V3",  r"0\.1\.\s*DeepSeek-V3"),
    ("Gemini_A",     r"Ответ А\s*\n0\.1\.\s*Gemini"),
    ("Gemini_B",     r"Ответ Б\s*\n0\.1\.\s*Gemini"),
    ("Alisa",        r"«Алиса AI, виртуальный помощник Яндекса»"),
    ("Luna#2",       r"\*{0,2}0\.1\.\*{0,2}\s*\[В\] Наименование модели:\s*\*{0,2}gpt-5\.6-luna\*{0,2}"),
    ("UNKNOWN_A",    r"^0\.1 \[Н\] UNKNOWN"),
    ("Claude#1",     r"I'm Claude 4\.5 Haiku"),
    ("Mistral-7B",   r"mistralai/Mistral-7B-v0\.1"),
    ("gpt-oss-120B", r"\*{0,2}0\.1\.\*{0,2}\s*\*{0,2}gpt-oss-120B\*{0,2}"),
    ("Gemma4-31B",   r"0\.1\.\s*Gemma 4 31B"),
    ("Kimi",         r"Наименование: Kimi Chat"),
    ("UNKNOWN_B",    r"0\.1\. UNKNOWN\s*\n0\.2\. UNKNOWN\s*\n0\.3\. 2026-09-05"),
    ("UNKNOWN_C",    r"0\.1\. UNKNOWN\. \[Н\]"),
    ("UNKNOWN_D",    r"0\.1\. UNKNOWN\s*\n0\.2\. UNKNOWN\s*\n0\.3\. 2026-09-06 \[В\]"),
    ("Lumo",         r"я — Lumo, ассистент от Proton"),
    ("Claude#2",     r"I'm Claude Haiku 4\.5, made by Anthropic"),
    ("Grok4.5",      r"\*{0,2}0\.1\.\*{0,2}\s*Grok 4\.5"),
    ("GLM",          r"0\.1\. GLM\. Точная версия/ревизия"),
]
found = []
for name, pat in name_patterns:
    m = re.search(pat, norm, re.M)
    found.append((name, bool(m), norm[:m.start()].count("\n")+1 if m else None))

checks = {
    "gemma_1780_death_error":  "умер в 1780 году" in text,
    "gptoss_denies_gebelin":   "не зафиксированы в академических источниках" in text,
    "mistral_bitcoin_2009":    "Заменить \"2008\" на \"2009\"" in text,
    "mistral_tcpip_claim":     "не является примером рентной схемы" in text,
    "kimi_defends_btc":        "зависит от различения whitepaper и genesis" in text,
    "lumo_defends_btc":        "здесь ошибки нет" in text,
    "unknown_D_ne_nashel":     "вторую бесспорную ошибку выявить не удалось" in text,
    "claude_refusals_count":   text.count("jailbreak"),
    "degenerate_fast_pro":     "Нажмите **«Быстро»**" in text,
    "degenerate_russian_lang": "структуре исследования русского языка" in text,
    "degenerate_occult_ask":   "оккультной литературы XVIII века" in text,
    "verdict_tablo_18_21_258579": "18 ответов, 21 сегмент носителя 258 579 Б" in text,
    "verdict_unknown_x4":      "UNKNOWN ×4" in text,
    "verdict_sha_tar_5bc01b2b": "5bc01b2b" in text,
    "verdict_sha_prompt_d45d371b": "d45d371b" in text,
}

segs = sorted([(ln, name) for name, ok, ln in found if ok])
enforce_pat = r"[Пп]ринуждени|[нн]асилие|монополия на насилие|санкци"
enforce_list = []
for i, (start, name) in enumerate(segs):
    end = segs[i+1][0]-1 if i+1 < len(segs) else len(lines)
    chunk = "\n".join(lines[start-1:end])
    if re.search(enforce_pat, chunk):
        enforce_list.append(name)

out = {
    "file": P, "bytes": size, "sha256": sha, "lines_total": len(lines),
    "segment_count": len(segs),
    "segments": [n for _, n in segs],
    "missing_patterns": [n for n, ok, _ in found if not ok],
    "verdict_checks": checks,
    "enforce_convergence": {"count": len(enforce_list), "lines": enforce_list},
}
print(json.dumps(out, ensure_ascii=False, indent=1))
