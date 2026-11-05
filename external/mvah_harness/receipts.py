"""MVA-H / receipts: append-only, hash-chained receipt journal.
Only the harness (trusted side) writes here. The model may only REFERENCE rids.
Tampering with any record breaks the chain; tampering with the last record
breaks the externally anchored head hash."""
import json, hashlib, time, os

def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

class ReceiptLog:
    def __init__(self, path: str, head_path: str = None):
        self.path = path
        self.head_path = head_path or path + ".head"
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        self.records = []
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.records.append(json.loads(line))

    def head(self) -> str:
        return sha(canonical(self.records[-1]).encode()) if self.records else "GENESIS"

    def verify_chain(self):
        prev = "GENESIS"
        for i, r in enumerate(self.records):
            if r.get("prev") != prev:
                return False, f"record {i} ({r.get('rid')}): prev-hash mismatch (history tampered)"
            prev = sha(canonical(r).encode())
        if os.path.exists(self.head_path):
            with open(self.head_path, "r") as f:
                anchored = f.read().strip()
            if anchored != self.head():
                return False, f"head anchor mismatch: anchored={anchored[:12]}.. actual={self.head()[:12]}.. (last record tampered)"
        return True, "ok"

    def mint(self, **fields) -> dict:
        rec = {"rid": f"R{len(self.records)+1:04d}", "ts": round(time.time(), 3),
               "prev": self.head(), **fields}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(canonical(rec) + "\n")
        self.records.append(rec)
        with open(self.head_path, "w") as f:
            f.write(self.head())
        return rec
