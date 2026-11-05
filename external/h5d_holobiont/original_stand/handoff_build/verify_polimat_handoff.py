#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Верификация собранного POLIMAT handoff HTML."""
import re, sys
from html.parser import HTMLParser

OUT = '/home/z/my-project/download/POLIMAT_H5d_HOLOBIONT_HANDOFF_2026-09-03.html'
html = open(OUT, encoding='utf-8').read()

# ── 1. Баланс тегов ──
VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr','circle','path'}
class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack=[]; self.errors=[]
    def handle_starttag(self, tag, attrs):
        if tag not in VOID: self.stack.append((tag, self.getpos()))
    def handle_endtag(self, tag):
        if tag in VOID: return
        if not self.stack: self.errors.append('extra </%s> at %s' % (tag, self.getpos())); return
        if self.stack[-1][0]==tag: self.stack.pop()
        else:
            found=False
            for i in range(len(self.stack)-1,-1,-1):
                if self.stack[i][0]==tag:
                    self.errors.append('mismatch: closing </%s> at %s, open stack top: %s' % (tag, self.getpos(), self.stack[i:]))
                    del self.stack[i:]; found=True; break
            if not found: self.errors.append('stray </%s> at %s' % (tag, self.getpos()))
p=P(); p.feed(html)
print('TAG BALANCE:', 'OK' if not p.errors and not p.stack else 'FAIL')
for e in p.errors[:10]: print('  ERR:', e)
if p.stack: print('  UNCLOSED:', [(t,pos) for t,pos in p.stack[:10]])

# ── 2. JS-зависимости ──
deps = ['id="healthOpenPanel"','id="mqRow1"','id="mqRow2"','id="pFs"','id="pLh"','id="pCh"','id="pCr"','id="pCc"','id="pW"',
        'id="e1991"','id="e1996"','id="e2005"','id="e2013"','id="e2026"','p-1991','p-1996','p-2005','p-2013','p-2026',
        'id="themeBtn"','id="comfortFab"','id="comfortPanel"','id="fsBtn"','id="resetBtn"','class="lead reveal"',
        'CONTACT','PARKED_CHALLENGED','LAW-COMPLETE','HOLOBIONT']
missing=[d for d in deps if d not in html]
print('JS DEPS:', 'OK' if not missing else 'MISSING: %s' % missing)

# ── 3. Полнота контента: ключевые фразы всех 45 секций MD ──
keys = [
 # 0 главное правило
 'CLAIMS_EXECUTION ≠ EXECUTION_EVIDENCE','*_stdout.log','биологическую аналогию',
 # 1 архитектура
 'ЦЕЛОЕ', 'не подавление части', 'легитимность агента ≠ легитимность изменения',
 # 2 holobiont
 'Rosenberg', 'Bordenstein', 'Moran', 'hologenome concept',
 # 3 CONTACT
 'голос части достигает целого', 'CONTACT ≠ AUTHORITY',
 # 4 PARKED
 'пространство временной интеграционной проверки', 'CONTACT → PARKED_CHALLENGED → COHERENCE → possible integration',
 # 5 law-complete
 '4 резидуума', 'слепую зону',
 # 6 паразитизм
 'непропорциональное управление', 'CAPABILITY ≠ AUTHORITY', 'AUTHENTICATION ≠ LEGITIMATE CHANGE',
 # 7 N5
 'WHO MAY SPEAK', 'WHO MAY CHANGE THE WHOLE', 'допустимым участником',
 # 8 H5d′
 'все потенциальные свидетельства могут войти', 'GLUED IMMUTABILITY', 'структурного порога доказательств',
 # 9 v3
 '_relearn', 'M4 quarantine', '[R2, R3, W1]', 'STAT_EXCESS', 'false rejection', '1/30',
 # 10 value-layer
 'law_write=True', 'TENTATIVE', 'anchor election + evidence-gated attestation', 'PAIRWISE ≠ GLOBAL',
 # 11 три оси
 'external-vs-self', 'my-history / foreign-history', 'self-sector', 'FALSIFIED', 'SURVIVED',
 # 12 E11
 'SPRT', 'Huber', 'violation budget', 'S0/VLI-equivalence', 'attested overwrite',
 # 13 N5 closure
 'overwrite = 0', 'A1 content search', '0 false-glue / 210', 'convergent pre-emption', 'freeze/delay',
 # 14 Round 11
 '10/10 PASS', 'NC1–NC4', 'матрица 8 порядков', 'oracle-flow', 'ATTRIBUTED_TO ≠ PERFORMED_BY', 'CONTRADICTION ≠ BLAME',
 'CONTENT_CONTINUITY ≠ PERSONAL_IDENTITY_CONTINUITY', 'PAIRWISE_CONSISTENCY ⊬ GLOBAL_COMPATIBILITY',
 # 15-16 Round 12
 'eps0 × eps', 'alpha × eps', 'E_MIN × V_MIN', 'eta × R', 'n5v', '8/8', 'bit-identical', '2–8%',
 '[0.062', '0.125', 'V1', 'V8',
 # 17 G2
 'correlated', 'коррелированные нарушения', 'availability cost', 'биномиальная',
 # 18 PO
 'random drops', 'burst loss', 'reorder', 'DEGRADED-LOUD', '0.938', 'M2-relearn', 'M2-value', 'rho=0.2',
 # 19 G2 round
 'union-find', 'k_eff', '0.104 → 0.062', 'min(merged)', 'v3.2',
 # 20-21 comparator
 'comparator.live.lean-lang.org', '/comparator/api/start', 'requestId', 'in-preparation', 'verification-ok',
 'verification-failed', 'connection-lost', 'Collatz', 'Ramsey', 'FLT', 'Mathlib', 'Honesty Clause', 'native_decide',
 'implemented_by', 'CANDIDATE-INCOMPLETE', 'refusal', 'primes',
 # 22 статус
 'CLOSED*', 'UNCHANGED', 'MD5 identical',
 # 23 уровни
 'LEVEL A', 'LEVEL B', 'LEVEL C', 'кольце 16', 'периоде 4',
 # 24-25 человек
 'максимизирует непосредственный локальный интерес', 'evolutionary biology', 'behavioral economics',
 'major transitions in evolution', 'philosophy of personhood', 'нормативно-системную аксиому',
 # 26 integration
 'SYNTHESIS OF THE BEST, BOUNDED BY NON-HARM', 'NON-HARM',
 # 27 паразит новая
 'cancer', 'rent extraction', 'institutional capture', 'principal-agent', 'Byzantine',
 # 28 задача
 'PARASITIC CAPTURE', 'WHOLE-PRESERVING UPDATE', 'LOCAL INTEREST', 'GLOBAL INTEREST',
 # 29 веб
 'information theory', 'causal inference', 'CLAIM → SOURCE → EVIDENCE → INFERENCE',
 # 30-31 holobiont критика
 'mutualism', 'antagonism', 'horizontal transmission', 'низкую fidelity', 'механизм интеграции конфликтующих',
 'превращает конфликт в безопасно интегрируемое свидетельство',
 # 32 оси + identity
 'Can every part contribute evidence', 'Whose history produced this change', 'coexist with the whole structure',
 'What makes the whole remain the same whole through change',
 # 33 non-harm
 'Harm(x, whole, context, t)', 'жизнеспособности', 'identity-preserving invariants',
 'пространства будущих состояний',
 # 34 этика
 'математика доказала мораль', 'non-maleficence', 'common good', 'collective agency',
 # 35 схема
 'AUTONOMOUS PARTS', 'EVIDENCE SPACE', 'INTEGRATION TEST', 'NO SILENT OVERWRITE',
 # 36 инварианты
 'PARTICIPATION ≠ SOVEREIGNTY', 'SOVEREIGNTY ≠ SUPPRESSION', 'LEGITIMATE_AGENT ≠ LEGITIMATE_MODIFICATION',
 'LAW_COMPLETE ≠ AUTOMATICALLY NON_HARM', 'RESULT ≠ VERIFICATION',
 # 37-38 закрыто/открыто
 'oracle independence', 'state integrity', 'параметрическая сетка Round 12', 'source-of-propagation clustering',
 'Replication', 'Real-world mapping', 'trust anchor', 'world_channel_pubkey', 'Non-harm formalization',
 'Identity of whole',
 # 39 правило
 'OBSERVE → ORIENT → PLAN → ACT → VERIFY → UPDATE', 'falsifier', 'baseline', 'независимый audit',
 # 40 запрещено
 'повышать статус UNKNOWN до VERIFIED', 'маскировать неудачный тест как успех', 'придумывать библиографию',
 # 41 код
 'preregistration', 'battery', 'results.json', 'Замороженное ядро',
 # 42 lean
 'pinned toolchain', 'theorem/API', 'Lean proof',
 # 43 точка остановки
 'Task 16-d', '6.2–12.5%',
 # 44 задача
 'скрытые логические скачки', 'CURRENT STATE', 'WHAT IS ACTUALLY PROVEN', 'OPEN GAP', 'NEXT EXPERIMENT',
 'критикой ради критики', 'destructive capture',
 # 45 финал
 'не отдаёт себя части', 'учиться у всех своих частей',
]
miss = [k for k in keys if k not in html]
print('CONTENT KEYS: %d/%d' % (len(keys)-len(miss), len(keys)))
for k in miss: print('  MISSING:', k)

# ── 4. Остатки старого контента шаблона в body ──
body = html[html.find('<body'):]
leftovers = ['идиот','ИДИОТ','COBUILD','Ожегов','Даль','ἰ','wiktionary','slovardal','словарь-голограмма','WCAG 2.2, критерий']
found = [w for w in leftovers if w in body]
print('OLD CONTENT LEFTOVERS:', 'NONE' if not found else found)

print('FILE SIZE: %.1f KB' % (len(html.encode('utf-8'))/1024))
sys.exit(0)
