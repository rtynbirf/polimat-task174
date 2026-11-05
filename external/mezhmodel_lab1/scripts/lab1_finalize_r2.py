#!/usr/bin/env python3
"""LAB1 R2 finalize: квитанции на финальные артефакты доставки (после эффекта)."""
import json, hashlib, hmac, os, time, uuid

BASE = "/home/z/my-project"
KEY = f"{BASE}/.keys/hmac.key"
LEDGER = f"{BASE}/receipts/ledger.jsonl"
key = open(KEY, "rb").read()
boot = open("/proc/sys/kernel/random/boot_id").read().strip()[:8]
GEN = "boot:" + boot

ARTIFACTS = [
    f"{BASE}/download/lab1_report_llm_assistant_architecture.md",
    f"{BASE}/download/lab1_report_llm_assistant_architecture.docx",
    f"{BASE}/download/README.md",
]

def body_hash(body):
    b = dict(body); b.pop("receipt_hash", None); b.pop("mac", None)
    return "sha256:" + hashlib.sha256(
        json.dumps(b, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

led = [json.loads(l) for l in open(LEDGER) if l.strip()]
for path in ARTIFACTS:
    blob = open(path, "rb").read()
    effect = {"size": len(blob), "sha256": "sha256:" + hashlib.sha256(blob).hexdigest()}
    pc = len(blob) > 0
    prev = led[-1]["receipt_hash"]; seq = led[-1]["seq"] + 1
    body = {"receipt_id": "rcpt_" + uuid.uuid4().hex[:12], "seq": seq,
            "prev_hash": prev, "env_generation": GEN, "nonce": uuid.uuid4().hex,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "actor": {"principal": "agent", "session": "lab1-r2-finalize"},
            "request": {"tool": "fs.observe_file", "authority_ref": "demo:self:R1",
                        "params": {"path": path}},
            "outcome": {"status": "executed", "effect": effect,
                        "postcondition": {"id": "pc.file_nonempty_and_hashed", "passed": pc}}}
    h = body_hash(body)
    body["receipt_hash"] = h
    body["mac"] = "hmac-sha256:" + hmac.new(key, h.encode(), hashlib.sha256).hexdigest()
    with open(LEDGER, "a") as f:
        f.write(json.dumps(body, ensure_ascii=False) + "\n")
    led.append(body)
    print(f"seq {seq}: {os.path.basename(path)}  {effect['size']} B  {effect['sha256'][:26]}…  pc={pc}")
