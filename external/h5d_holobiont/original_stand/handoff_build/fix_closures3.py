#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Финальная расстановка </article> для p3/p5.
   1) убрать все автономные строки '</article>';
   2) в каждом <div class="bento"> / <div class="hf-grid">: depth стартует 1 (мы внутри сетки),
      сетка закрыта, когда depth вернулся к 0; каждую открытую <article> закрыть
      перед следующей <article> или перед закрывающим </div> сетки."""
import re

FILES = ['/home/z/my-project/scripts/parts/p3.html',
         '/home/z/my-project/scripts/parts/p5.html']

def close_cards(lines, gp):
    out = list(lines)
    i = gp + 1
    depth = 1
    opened = False
    ins = 0
    while i < len(out) and depth > 0:
        line = out[i]
        m = re.match(r'^(\s*)<article\b', line)
        if m and opened:
            out.insert(i, m.group(1) + '</article>')
            ins += 1
            opened = False
            i += 1
            line = out[i]
            m = re.match(r'^(\s*)<article\b', line)
        if m:
            opened = True
        if opened and '</article>' in line:
            opened = False
        opens = len(re.findall(r'<div\b', line))
        closes = len(re.findall(r'</div>', line))
        depth += opens - closes
        if depth == 0:
            if opened:
                indent = re.match(r'^(\s*)', out[i]).group(1)
                out.insert(i, indent + '</article>')
                ins += 1
                opened = False
            break
        i += 1
    return out, ins

for path in FILES:
    s = open(path, encoding='utf-8').read()
    s = re.sub(r'\n[ \t]+</article>(?=\n)', '', s)
    lines = s.split('\n')
    positions = [i for i, l in enumerate(lines) if re.search(r'<div class="(?:bento|hf-grid)"', l)]
    total = 0
    for gp in reversed(positions):
        lines, ins = close_cards(lines, gp)
        total += ins
    s = '\n'.join(lines)
    open(path, 'w', encoding='utf-8').write(s)
    print('%s: grids=%d inserted=%d -> <article=%d </article>=%d' % (
        path.split('/')[-1], len(positions), total, s.count('<article'), s.count('</article>')))
