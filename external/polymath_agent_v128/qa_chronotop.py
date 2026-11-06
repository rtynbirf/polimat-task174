#!/usr/bin/env python3
"""QA «Хронотопа» v1.2: алфавитная гигиена + баланс тегов + сверка токенов кампании."""
import re, sys
from html.parser import HTMLParser
from pathlib import Path

PATH = str(Path(__file__).resolve().parent / "report_v12_chronotop.html")
html_src = open(PATH, encoding="utf-8").read()
fails = []

# ── 1. баланс тегов ──────────────────────────────────────────────────────
VOID = {"area","base","br","col","embed","hr","img","input","link","meta",
        "param","source","track","wbr"}
class Chk(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.problems = [], []
    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append((tag, self.getpos()))
    def handle_endtag(self, tag):
        if not self.stack:
            self.problems.append(f"лишний </{tag}> @ {self.getpos()}")
            return
        top, pos = self.stack.pop()
        if top != tag:
            self.problems.append(f"несоответствие: открыт <{top}> @ {pos}, закрыт </{tag}> @ {self.getpos()}")
c = Chk()
c.feed(html_src)
c.close()
if c.problems:
    fails += c.problems[:6]
if c.stack:
    fails += [f"незакрыт <{t}> @ {p}" for t, p in c.stack[:6]]

# ── 2. алфавитная гигиена видимого текста ────────────────────────────────
body = re.sub(r"<style.*?</style>", "", html_src, flags=re.S)
body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
body = re.sub(r"<[^>]+>", " ", body)          # выкидываем разметку целиком
bad_tokens = []
# дефис — граница: «maxLength-бюджетами» = «maxLength» + «бюджетами» (легальные термины)
for tok in re.findall(r"[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9_:/]*", body):
    has_cyr = re.search(r"[А-Яа-яЁё]", tok)
    has_lat = re.search(r"[A-Za-z]", tok)
    if has_cyr and has_lat:
        bad_tokens.append(tok)
if bad_tokens:
    fails.append(f"смешанные алфавиты в словах: {bad_tokens[:12]}")

# ── 3. сверка токенов кампании ───────────────────────────────────────────
must = ["ХРОНО", "v1.2.8", "19/19", "2444", "1601", "220", "219.7", "187.6", "162.9",
        "70bd1f0a", "T17", "T18", "T19", "66c4119357", "5a1b0a7390", "05a5fef056",
        "1406a05ad5", "accb1c587c", "9c177a7aa4", "f15e64b15b", "32fba99ad2",
        "46f7a434cf", "84c3291b70", "167490b354", "KEEP_ALIVE", "20.3", "3.41",
        "1536", "q8_0", "ARSENAL CHAIN WORKS", "полимат держит цепь", "maxItems",
        "state-save"]
for m in must:
    if m not in html_src:
        fails.append(f"в отчёте нет токена: {m}")

# ── 4. артефакт кампании жив на диске ────────────────────────────────────
try:
    content = open("/home/z/my-project/bench/ws_c1/upper.txt", encoding="utf-8").read()
    if content.strip() != "ARSENAL CHAIN WORKS":
        fails.append(f"C1-артефакт изменился: {content!r}")
except OSError as e:
    fails.append(f"C1-артефакт недоступен: {e}")

print("=" * 46)
if fails:
    print("QA ХРОНОТОПА: НАЙДЕНЫ ДЕФЕКТЫ:")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("QA ХРОНОТОПА: ВСЕ КОНТРОЛИ ЗЕЛЁНЫЕ")
print("  теги сбалансированы; алфавиты чисты; токены кампании на месте; C1-артефакт цел")
