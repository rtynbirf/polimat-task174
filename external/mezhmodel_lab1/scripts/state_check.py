#!/usr/bin/env python3
"""LAB1: reconciliation demo - LOST vs UNKNOWN vs STATE_OK vs UNTRACKED.
Reads the ledger, finds the last passed receipt for the path,
re-observes the world NOW, and issues a typed state verdict.
Implements the claim grammar from the report:
  STATE_OK / CHANGED / LOST / UNKNOWN / UNTRACKED
"""
import json, hashlib, os, sys, time

LEDGER = "/home/z/my-project/receipts/ledger.jsonl"
path = sys.argv[1]

last = None
if os.path.exists(LEDGER):
    for line in open(LEDGER):
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("request", {}).get("params", {}).get("path") == path \
           and r.get("outcome", {}).get("postcondition", {}).get("passed"):
            last = r

exists = os.path.exists(path)
now_hash = None
if exists:
    now_hash = "sha256:" + hashlib.sha256(open(path, "rb").read()).hexdigest()

if last is None and not exists:
    verdict = "UNKNOWN"      # no evidence either way - cannot even claim absence
elif last is None and exists:
    verdict = "UNTRACKED"    # exists, but we have no provenance for it
elif last is not None and not exists:
    verdict = "LOST"         # was evidenced, now absent: contradiction between observations
elif last["outcome"]["effect"]["sha256"] == now_hash:
    verdict = "STATE_OK"     # fresh check matches last evidenced content
else:
    verdict = "CHANGED"

print(json.dumps({
    "claim_type": "STATE",
    "path": path,
    "verdict": verdict,
    "last_receipt_seq": last["seq"] if last else None,
    "last_receipt_hash": (last["outcome"]["effect"]["sha256"][:24] + "...") if last else None,
    "now_hash": (now_hash[:24] + "...") if now_hash else None,
    "checked_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}, ensure_ascii=False))
