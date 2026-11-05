#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка POLIMAT handoff-страницы на базе шаблона GOLOGRAMMA v1.
Структура и CSS/JS шаблона не меняются: заменяются только заголовок,
meta-описание, шапка+main, футер и список бегущей строки TRENDS."""
import re, sys

TPL = '/home/z/my-project/upload/GOLOGRAMMA_v1_V_EGO_SHABLONE_2026-08-30.html'
OUT = '/home/z/my-project/download/POLIMAT_H5d_HOLOBIONT_HANDOFF_2026-09-03.html'
PARTS = ['/home/z/my-project/scripts/parts/p%d.html' % i for i in (1, 2, 3, 4, 5)]
FOOTER = '/home/z/my-project/scripts/parts/footer.html'

TRENDS_JSON = ('["CONTACT","PARKED_CHALLENGED","LAW-COMPLETE","COHERENCE","GLUED","EPOCH SWITCH",'
               '"N5","H5d\\u2032v3","HOLOBIONT","\\u0426\\u0415\\u041b\\u041e\\u0415 > \\u0421\\u0423\\u041c\\u041c\\u0410 \\u0427\\u0410\\u0421\\u0422\\u0415\\u0419",'
               '"CLAIM \\u2260 EVIDENCE","CONTACT \\u2260 TRUTH","SILENT = 0","INTEGRATION"]')

html = open(TPL, encoding='utf-8').read()
orig_len = len(html)

# 1) title и meta description
html = re.sub(r'<title>.*?</title>',
              '<title>POLIMAT / H5d\u2032 / HOLOBIONT — мастер-хэндофф: целое, которое не исключает части и не отдаёт себя части</title>',
              html, flags=re.S)
html = re.sub(r'<meta name="description" content="[^"]*">',
              '<meta name="description" content="Мастер-хэндофф POLIMAT: модель H5d\u2032 против N5 — паразитического присвоения функции целого легитимным агентом. Раунды 8–13, канонические инварианты, статусы CLOSED*/DEGRADED-LOUD/UNKNOWN, границы и открытые фронты. Автономный файл: шрифты, стили и скрипты внутри.">',
              html)

# 2) шапка + main целиком (от <header class="site-header" до </main>)
new_top = ''.join(open(p, encoding='utf-8').read() for p in PARTS)
h0 = html.find('<header class="site-header"')
h1 = html.find('</main>') + len('</main>')
assert h0 != -1 and h1 > h0, 'main anchors not found'
html = html[:h0] + new_top + html[h1:]

# 3) футер
f0 = html.find('<footer class="site-footer"')
f1 = html.find('</footer>') + len('</footer>')
assert f0 != -1 and f1 > f0, 'footer anchors not found'
html = html[:f0] + open(FOOTER, encoding='utf-8').read() + html[f1:]

# 4) бегущая строка
html, n = re.subn(r'var TRENDS = \[.*?\];', lambda m: 'var TRENDS = ' + TRENDS_JSON + ';', html, flags=re.S)
assert n == 1, 'TRENDS not patched'

open(OUT, 'w', encoding='utf-8').write(html)
print('OK: %d -> %d chars, out=%s' % (orig_len, len(html), OUT))
