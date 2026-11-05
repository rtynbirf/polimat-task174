#!/usr/bin/env python3
"""Extract the 6 built-in comparator challenges byte-exactly from the JS bundle,
hash-verify against the service's builtInTrusted registry, save to JSON.
The '^[m' iterate-notation is handled at byte level (no retyping)."""
import re, hashlib, json, sys, requests

BUNDLE = 'research/comparator_bundle.js'
TRUSTED_URL = "https://comparator.live.lean-lang.org/assets/builtInTrusted-Cf2BvbPq.js"
OUT = 'research/comparator_challenges.json'

src = open(BUNDLE, encoding='utf-8').read()
i = src.find('var dH=Object.fromEntries([')
assert i >= 0, "dH marker not found"
seg = src[i:i+3000]
end = seg.find('}].map(')
assert end > 0
seg = seg[:end]

entries = []
pos = 0
while True:
    a = seg.find('{label:`', pos)
    if a < 0:
        break
    lb = seg.find('`', a + len('{label:`'))
    label = seg[a + len('{label:`'):lb]
    c = seg.find('contents:`', lb)
    if c < 0:
        break
    c += len('contents:`')
    e = seg.find('`}', c)
    body = seg[c:e]
    entries.append((label, body))
    pos = e + 2

assert len(entries) == 6, f"expected 6 challenges, got {len(entries)}"

def dec(s):
    # decode \uXXXX escapes used inside the bundle's template literals
    return re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), s)

challenge_texts = {}
for label, body in entries:
    text = dec(body).strip()
    challenge_texts[label] = text
    # byte-level proof of any iterate-notation content (avoids display mangling)
    if 'collatz' in label.lower():
        k = text.find('collatzStep^')
        print("collatz bytes after collatzStep^:",
              text[k + len('collatzStep^'):k + len('collatzStep^') + 4].encode('utf-8').hex())

# hash-verify against the service registry (UI: value = contents.trim(); hash = sha256(trimEnd()+'\n'))
trusted_js = requests.get(TRUSTED_URL, timeout=30).text
trusted = {}
for m in re.finditer(r'"?([0-9a-f]{64})"?:\{name:`([^`]*)`', trusted_js):
    trusted[m.group(1)] = m.group(2)
print("registry size:", len(trusted))

out = {}
all_ok = True
for label, text in challenge_texts.items():
    h = hashlib.sha256((text.rstrip() + "\n").encode('utf-8')).hexdigest()
    name = trusted.get(h)
    print(f"[{label}] sha256={h[:16]}... builtin={name!r}")
    if name is None:
        all_ok = False
    out[label] = {"text": text, "sha256_trimEnd_nl": h, "builtin_name": name}

assert all_ok, "at least one challenge hash did not match builtInTrusted"
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print("saved", OUT)
