#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Структурная проверка собранного файла: дочерние карточки сеток, панели эпох, details."""
from html.parser import HTMLParser

OUT = '/home/z/my-project/download/POLIMAT_H5d_HOLOBIONT_HANDOFF_2026-09-03.html'
html = open(OUT, encoding='utf-8').read()

class S(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.counts = {}
        self.cur = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        ident = a.get('id') or a.get('class') or tag
        self.stack.append(ident)
        key = ' > '.join(self.stack[-3:])
        self.cur.append((tag, ident))
        if tag in ('article', 'details', 'li', 'div') and len(self.stack) >= 2:
            parent = ' > '.join(self.stack[-2:])
            self.counts.setdefault(parent, 0)
            if tag in ('article', 'details'):
                self.counts[parent] += 1
    def handle_endtag(self, tag):
        for j in range(len(self.stack) - 1, -1, -1):
            if self.stack[j].startswith(tag) or self.cur and False:
                pass
        # simple: pop until matching tag
        while self.stack and not self.stack[-1].startswith(tag + ('.' if False else '')):
            # our idents are not pure tags; find by tag stored separately
            break
        # pop matching: track tags in cur
        if self.cur:
            while self.cur and self.cur[-1][0] != tag:
                self.cur.pop()
                # also pop stack item
            if self.cur:
                self.cur.pop()
                self.stack.pop()

# simpler: custom tracking
class T2:
    def __init__(self):
        self.tag_stack = []   # (tag, ident)
        self.res = {}
    def feed(self, html):
        import re
        pos = 0
        for m in re.finditer(r'<(/?)([a-zA-Z][a-zA-Z0-9]*)((?:"[^"]*"|[^>"])*)>', html):
            close, tag, attrs_s = m.group(1), m.group(2).lower(), m.group(3)
            if tag in ('meta','link','br','hr','img','input','circle','path','output'):
                if close: 
                    while self.tag_stack and self.tag_stack[-1][0] != tag: self.tag_stack.pop()
                    if self.tag_stack: self.tag_stack.pop()
                continue
            attrs = dict(re.findall(r'([a-zA-Z-]+)="([^"]*)"', attrs_s))
            if close:
                # pop to matching tag
                k = len(self.tag_stack) - 1
                while k >= 0 and self.tag_stack[k][0] != tag: k -= 1
                if k >= 0: del self.tag_stack[k:]
            else:
                ident = attrs.get('id') or attrs.get('class') or tag
                parent = ' | '.join('%s.%s' % (t, i.split()[0]) for t, i in self.tag_stack[-2:])
                if tag == 'article':
                    self.res.setdefault(parent, []).append(attrs.get('class', ''))
                if tag == 'details':
                    self.res.setdefault(parent + ' DETAILS', []).append(1)
                if tag == 'input' and attrs.get('type') == 'radio':
                    self.res.setdefault('ERA RADIOS', []).append(attrs.get('id'))
                self.tag_stack.append((tag, ident))

t = T2(); t.feed(html)
for k in sorted(t.res):
    v = t.res[k]
    if k in ('ERA RADIOS',) or 'bento' in k or 'hf-grid' in k or 'DETAILS' in k or 'tl-list' in k:
        print('%-70s -> %d %s' % (k, len(v), v if len(str(v)) < 120 else ''))
