#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble COMPARATOR_LIVE_PROMPT_GOLOGRAMMA.html:
   GOLOGRAMMA v1 template structure (head/css/js untouched) + body text
   filled from download/COMPARATOR_LIVE_PROMPT.md (verbatim prompt block)."""
import html as ihtml
import re
import sys

TPL = '/home/z/my-project/upload/GOLOGRAMMA_v1_V_EGO_SHABLONE_2026-08-30.html'
MD  = '/home/z/my-project/download/COMPARATOR_LIVE_PROMPT.md'
OUT = '/home/z/my-project/download/COMPARATOR_LIVE_PROMPT_GOLOGRAMMA.html'

tpl = open(TPL, encoding='utf-8').read()
md  = open(MD, encoding='utf-8').read()
A = open('/home/z/my-project/scripts/comparator_body_a.html', encoding='utf-8').read()
B = open('/home/z/my-project/scripts/comparator_body_b.html', encoding='utf-8').read()
C = open('/home/z/my-project/scripts/comparator_body_c.html', encoding='utf-8').read()

# ── 1. Verbatim prompt from the md (```text fenced block; contains a nested ```lean fence!) ──
start = md.find('```text\n')
assert start != -1, '```text fence not found'
start += len('```text\n')
end = md.rfind('\n```')
assert end > start, 'closing fence not found'
prompt = md[start:end]
assert prompt.lstrip().startswith('SYSTEM/TASK PROMPT'), prompt[:80]
assert 'HONESTY CLAUSE (non-negotiable)' in prompt
assert 'CANDIDATE-INCOMPLETE' in prompt
assert prompt.rstrip().endswith('protocol result).'), prompt[-80:]
print('[ok] prompt extracted:', len(prompt), 'chars,', prompt.count(chr(10)) + 1, 'lines')

# ── 2. Head: title + description ──
NEW_TITLE = ('<title>Comparator Live — эталон живого промпта: заявление ≠ доказательство, '
             'вердикт выдаёт компилятор</title>')
OLD_TITLE = '<title>Словарь-голограмма 2026 — эталон: часть знает целое, целое знает все части</title>'
assert OLD_TITLE in tpl, 'old title not found'
head = tpl[:tpl.find('<style>')]
head = head.replace(OLD_TITLE, NEW_TITLE)
NEW_DESC = ('<meta name="description" content="Живой промпт Comparator Live '
            '(comparator.live.lean-lang.org): реальная проверка Lean 4 + Mathlib в закреплённом '
            'тулчейне, механика POST/SSE и три вердикта, шесть встроенных челленджей, Honesty '
            'Clause и протокол CANDIDATE-INCOMPLETE. Заметка Полимата: RESULT ≠ VERIFICATION, '
            'CLAIMS_EXECUTION ≠ EXECUTION_EVIDENCE, TAG ≠ VERIFICATION ≅ CONTACT ≠ TRUTH. '
            'Автономный файл: шрифты, стили и скрипты внутри.">')
head, n = re.subn(r'<meta name="description" content="[^"]*">', NEW_DESC, head)
assert n == 1, 'description replace failed'

# ── 3. CSS block untouched ──
css_start = tpl.find('<style>')
css_end   = tpl.find('</style>') + len('</style>')
css = tpl[css_start:css_end]

# ── 4. Body ──
body = A + B + C
assert body.count('@@PROMPT_VERBATIM@@') == 1, 'placeholder count'
body = body.replace('@@PROMPT_VERBATIM@@', ihtml.escape(prompt, quote=False))

# ── 5. Tail JS: replace TRENDS array (displayed text only, mechanics untouched) ──
tail_start = tpl.find('<script>', css_end)
tail = tpl[tail_start:]
OLD_TRENDS = ('  var TRENDS = ["ТЕКСТ","ШУМ","ГИП","ЗАКОН ЦЕПОЧЕК","ШЕСТЬ СЛОВ","ШЕСТЬ СЛОЁВ",'
              '"СУД","СИНКЛЕР 1987","ИДИОТ","ГРАЖДАНИН ВНЕ ДЕЛ","МАШИНА","ЧЕЛОВЕК-СУД","СЛОВАРЬ",'
              '"ГОЛОГРАММА"];')
NEW_TRENDS = ('  var TRENDS = ["VERIFICATION-OK","VERIFICATION-FAILED","CONNECTION-LOST",'
              '"HONESTY CLAUSE","CLAIMS \\u2260 EVIDENCE","TAG \\u2260 VERIFICATION",'
              '"CONTACT \\u2260 TRUTH","CANDIDATE-INCOMPLETE","NO SORRY","TOFU + HASH",'
              '"IN-PREPARATION","IN-QUEUE","IN-PROGRESS","PNat.pow_add_pow_ne_pow"];')
assert OLD_TRENDS in tail, 'old TRENDS not found'
tail = tail.replace(OLD_TRENDS, NEW_TRENDS)

out = head + css + body + tail
open(OUT, 'w', encoding='utf-8').write(out)
print('[ok] written:', OUT, len(out), 'chars')

# ────────────────── VERIFICATION ──────────────────
src = open(OUT, encoding='utf-8').read()
body_zone = src[src.find('<body>'):src.rfind('<script>')]

# 5.1 required ids (JS hooks + anchors)
need_ids = ['siteHeader','main','top','time-machine','timeline','dna','health','prompt','offline',
            'glossary','sources','mqRow1','mqRow2','themeBtn','toTop','comfortFab','comfortPanel',
            'healthOpenPanel','fsBtn','motionBtn','contrastBtn','ecoBtn','fontBtn','resetBtn',
            'pFs','pLh','pCh','pCr','pCc','pW','e1991','e1996','e2005','e2013','e2026']
missing = [i for i in need_ids if ('id="%s"' % i) not in src]
assert not missing, 'missing ids: %s' % missing
print('[ok] all %d required ids present' % len(need_ids))

# 5.2 structural counts (scoped)
def count(pat, zone=body_zone):
    return len(re.findall(pat, zone))
def zone_between(a, b):
    i, j = src.find(a), src.find(b)
    assert -1 < i < j, 'zone %s..%s not found' % (a, b)
    return src[i:j]
dna_zone = zone_between('id="dna"', 'id="health"')
nav_zone = zone_between('class="main-nav"', '</nav>')
checks = {
    'tm panels (5)':            (body_zone, r'class="tm-panel ', 5),
    'tl items (8)':             (body_zone, r'<li class="tl-item reveal"', 8),
    'bento cards in dna (8)':   (dna_zone, r'<article class="card(?: span2)? reveal"', 8),
    'health cards (6)':         (zone_between('id="health"', 'id="prompt"'), r'<article class="card reveal"', 6),
    'offline cards (6)':        (zone_between('id="offline"', 'id="glossary"'), r'<article class="card reveal"', 6),
    'details (14)':             (zone_between('id="glossary"', '</main>'), r'<details class="reveal">', 14),
    'pre blocks (1)':           (body_zone, r'<pre ', 1),
    'era-desc (5)':             (body_zone, r'<div class="era-desc">', 5),
    'checklist (2)':            (body_zone, r'<div class="checklist reveal">', 2),
    'main-nav links (8)':       (nav_zone, r'<a href="#', 8),
}
for name, (zone, pat, want) in checks.items():
    got = count(pat, zone)
    assert got == want, '%s: got %d want %d' % (name, got, want)
    print('[ok] %s = %d' % (name, got))

# 5.3 era radio ↔ panel class pairing
for e in ['1991','1996','2005','2013','2026']:
    assert 'id="e%s"' % e in src and 'class="tm-panel p-%s"' % e in src
print('[ok] era ids/classes paired')

# 5.4 prompt verbatim (unescape round-trip)
pre_m = re.search(r'<pre class="mono"[^>]*>(.*?)</pre>', body_zone, re.S)
assert pre_m, 'pre not found'
unesc = ihtml.unescape(pre_m.group(1))
assert unesc == prompt, 'prompt differs from md!'
print('[ok] prompt block is byte-identical to COMPARATOR_LIVE_PROMPT.md (%d chars)' % len(unesc))

# 5.5 no leftovers from the donor template text
leftovers = ['идиот','ИДИОТ','Ожегов','Шведова','Синклер','COBUILD','wiktionary','ἰδι',
             'судовой','невежда','ёмкий','ГОЛОГРАММА v1','slovardal','slovarozhegova']
bad = [w for w in leftovers if w in body_zone]
bad += ['Даль(word)'] if re.search(r'\bДаль\b', body_zone) else []
assert not bad, 'leftover words: %s' % bad
print('[ok] no donor-template leftovers in body')

# 5.6 key content spot-checks (md fully represented)
must_have = ['comparator.live.lean-lang.org','index-B3V-f9ua.js','in-preparation','in-queue',
             'in-progress','verification-ok','verification-failed','connection-lost',
             'PNat.pow_add_pow_ne_pow','exists_prime_factor','factorial','IsPrime','collatzStep',
             'native_decide','@[implemented_by]','@[extern]','Classical.choice','byte-for-byte',
             'modulo whitespace','CLAIMS ARE NOT EVIDENCE','proven artifact','GAP:',
             'Finite Ramsey theorem','Collatz Conjecture','prove True','prove False',
             'Latest Mathlib with Lean v4.34.0-rc2','v4.33.0','v4.32.x','TOFU','I trust this challenge',
             'RESULT ≠ VERIFICATION','CLAIMS_EXECUTION ≠ EXECUTION_EVIDENCE','TAG ≠ VERIFICATION',
             'CONTACT ≠ TRUTH','§7-канал value-загрязнения','ЕДИНСТВЕННЫЙ lean-блок',
             'дрейф API','Infinitely Many Primes','HARD REQUIREMENTS','SELF-CHECK','BEGIN']
miss = [w for w in must_have if w not in body_zone and w not in src[src.rfind('<script>'):]]
assert not miss, 'missing content: %s' % miss
print('[ok] all %d key content items present' % len(must_have))

# 5.7 tag balance sanity
from html.parser import HTMLParser
class P(HTMLParser):
    VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self):
        super().__init__(convert_charrefs=True); self.stack=[]; self.errs=[]
    def handle_starttag(self, t, a):
        if t not in self.VOID: self.stack.append(t)
    def handle_endtag(self, t):
        if t in self.VOID: return
        if self.stack and self.stack[-1]==t: self.stack.pop()
        else: self.errs.append('mismatch </%s> at %d (top=%s)' % (t, self.getpos()[0], self.stack[-3:]))
p = P(); p.feed(src)
assert not p.errs and not p.stack, 'tag balance: %s / open: %s' % (p.errs[:4], p.stack[:8])
print('[ok] tag balance clean')

print('DONE — all checks passed.')
