#!/usr/bin/env python3
"""LAB1: live demonstration of the receipt model proposed in the report.
Executes a REAL action (writes a probe artifact), observes the EFFECT
(not the ack), appends an HMAC-signed receipt to an append-only ledger.
NOTE (honest limitation): in this sandbox the LLM-agent and this runtime
share one principal, so key separation is DEMONSTRATIVE, not ENFORCED.
"""
import json, hashlib, hmac, os, time, uuid

BASE = "/home/z/my-project"
KEY = f"{BASE}/.keys/hmac.key"
LEDGER = f"{BASE}/receipts/ledger.jsonl"
ART = f"{BASE}/download/__lab1_probe_artifact.txt"
for d in (f"{BASE}/.keys", f"{BASE}/receipts", f"{BASE}/download"):
    os.makedirs(d, exist_ok=True)

if not os.path.exists(KEY):
    fd = os.open(KEY, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.write(fd, os.urandom(32)); os.close(fd)
key = open(KEY, "rb").read()

boot = "unknown"
try:
    boot = open("/proc/sys/kernel/random/boot_id").read().strip()[:8]
except Exception:
    pass

# --- ACTION REQUEST (drafted by "model"; would be validated by runtime) ---
req = {"tool": "fs.write_file", "authority_ref": "demo:self:R1",
       "params": {"path": ART, "content": "LAB1 probe artifact - if you can read this, the receipt below refers to a real write.\n"}}

# --- ACT (runtime) ---
content = req["params"]["content"].encode()
with open(ART, "wb") as f:
    f.write(content)

# --- OBSERVE EFFECT + POSTCONDITION (effect, not exit code) ---
blob = open(ART, "rb").read()
effect = {"size": len(blob), "sha256": "sha256:" + hashlib.sha256(blob).hexdigest()}
pc = {"id": "pc.file_exists_and_content_matches",
      "passed": len(blob) == len(content) and effect["sha256"] == "sha256:" + hashlib.sha256(content).hexdigest()}

# --- LEDGER: chain to previous receipt ---
prev_hash, seq = "GENESIS", 1
if os.path.exists(LEDGER):
    lines = open(LEDGER).read().strip().splitlines()
    if lines:
        last = json.loads(lines[-1]); prev_hash = last["receipt_hash"]; seq = last["seq"] + 1

body = {"receipt_id": "rcpt_" + uuid.uuid4().hex[:12], "seq": seq, "prev_hash": prev_hash,
        "env_generation": "boot:" + boot, "nonce": uuid.uuid4().hex,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "actor": {"principal": "agent", "session": "lab1"}, "request": req,
        "outcome": {"status": "executed", "effect": effect, "postcondition": pc}}
h = "sha256:" + hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
body["receipt_hash"] = h
body["mac"] = "hmac-sha256:" + hmac.new(key, h.encode(), hashlib.sha256).hexdigest()
with open(LEDGER, "a") as f:
    f.write(json.dumps(body, ensure_ascii=False) + "\n")
print(json.dumps(body, ensure_ascii=False, indent=2))
