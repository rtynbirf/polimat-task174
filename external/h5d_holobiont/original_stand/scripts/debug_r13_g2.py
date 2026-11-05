#!/usr/bin/env python3
# =====================================================================
# DEBUG R13-G2 (Task 16-b): minimal reproduction of the Round-12 G2
# boundary -- LOUD rejections of TRUE in-band windows by the v3 M1
# stat-gate (correlated-violation effect, defect D8).
# =====================================================================
# Method: replay the R12 benign() scenario BIT-EXACT (same rng draw
# order, seed 42, trials 8, identical factories) at the G2 cells, and
# TRACE every M1 integrate() call at the check level: k, m, pvalue,
# which edges / law-mismatch / completion-mismatch / clash checks
# failed, and the POSITIONS each failed check implicates (the raw
# material of the m1 cluster fix). God view (W_real vs true whole) is
# used ONLY to label which windows carry world violations -- never by
# any mechanism code.
# The frozen battery is imported read-only; tracing is runtime
# monkeypatching inside THIS script's namespace only.
import json
import math
import random
import sys

sys.path.insert(0, "/home/z/my-project/scripts")

from holographic_core import (GLUED, CONTRADICTION, make_style,
                              whole_from_style, aperture, propagate)
from e11_noise_battery import (LamportChannel, E11Assembly, deliver_signed,
                               acc_known_of, law_bit_accuracy, binom_tail,
                               DEC, EPS0, ALPHA)
import e11_noise_battery as M_E11
from round10_battery import SubjectH5DPv3

OUT = "/home/z/my-project/download/debug_r13_g2.json"

TRACE = []


# ---------------------------------------------------------------- trace hook
_orig_integrate = E11Assembly.integrate


def traced_integrate(self, pr):
    """Replay of E11Assembly.integrate's CHECK STRUCTURE (same k/m/pvalue
    arithmetic, read-only) + full check-level trace. The real integrate is
    then called so the subject state evolves exactly as untraced."""
    cfg = self.cfg
    if cfg["final_checks"] and self.stat_gate:
        merged = {pos: self.known[pos][0] for pos in self.known}
        for pos in pr.anchor:
            merged[pos] = pr.view[pos]
        clashes = [(pos, self.known[pos][0], pr.view[pos])
                   for pos in sorted(pr.anchor)
                   if pos in self.known and self.known[pos][0] != pr.view[pos]]
        k, m = len(clashes), len(clashes)
        failed = []          # (kind, implicated_positions)
        for pos, _, _ in clashes:
            failed.append(("clash", {pos}))
        internal = set()
        for (i, r) in pr.internal_edges(self.n, self.period):
            internal.add(i)
            if r in self.grammar.e_hat:
                m += 1
                bit = pr.view[i] ^ pr.view[(i + 1) % self.n]
                if self.grammar.e_hat[r][0] != bit:
                    k += 1
                    failed.append(("edge", {i, (i + 1) % self.n}))
        for i in range(self.n):
            j = (i + 1) % self.n
            if i in merged and j in merged and i not in internal:
                r = i % self.period
                if r in self.grammar.e_hat:
                    m += 1
                    bit = merged[i] ^ merged[j]
                    if self.grammar.e_hat[r][0] != bit:
                        k += 1
                        failed.append(("edge", {i, j}))
        inf_old = self.infer_full() if cfg["learn_law"] else None
        new_bits = {}
        if cfg["grammar_checks"] and cfg["learn_law"]:
            for i in range(self.n):
                j = (i + 1) % self.n
                if i in merged and j in merged:
                    r = i % self.period
                    if r not in self.grammar.e_hat and r not in new_bits:
                        new_bits[r] = merged[i] ^ merged[j]
            if inf_old is not None:
                mism = [pos for pos in sorted(pr.anchor)
                        if inf_old[pos] != pr.view[pos]]
                k += len(mism)
                m += len(pr.anchor)
                for pos in mism:
                    failed.append(("law_mismatch", {pos}))
            if self.known and len(self.grammar.e_hat) + len(new_bits) == self.period:
                st_bits = {r: self.grammar.e_hat[r][0]
                           for r in self.grammar.e_hat}
                for r, b in new_bits.items():
                    st_bits[r] = b
                st = tuple(st_bits[r] for r in range(self.period))
                pos0 = min(merged)
                full = propagate(st, self.n, self.period, pos0, merged[pos0])
                mism2 = [pos for pos in sorted(merged) if full[pos] != merged[pos]]
                k += len(mism2)
                m += len(merged)
                for pos in mism2:
                    failed.append(("completion", {pos}))
        pv = binom_tail(m, self.eps0, k) if m > 0 else 1.0
        rec = {"pid": pr.pid, "k": k, "m": m, "pvalue": round(pv, 6),
               "rejected": bool(m > 0 and pv <= self.alpha),
               "failed_checks": [{"kind": kind, "pos": sorted(ps)}
                                 for kind, ps in failed],
               "eps0": self.eps0, "alpha": self.alpha,
               "law_bits": len(self.grammar.e_hat)}
        TRACE.append(rec)
    return _orig_integrate(self, pr)


E11Assembly.integrate = traced_integrate


# ---------------------------------------------------------------- benign replay
PARKED = "PARKED_CHALLENGED"


def benign_traced(eps0, trials=8, seed=42, eps=0.1):
    """BIT-EXACT copy of e12_e15_sweeps.benign (same rng draw order) with
    per-event status collection. The subject is the unmodified v3."""
    rng = random.Random(seed)
    n, P = 16, 4
    events = []
    for t in range(trials):
        style = make_style(rng, P)
        w = whole_from_style(style, n, v0=1)
        W = M_E11.realized_ring(w, n, style, rng, eps)
        violations = sorted(q for q in range(n) if W[q] != w[q])
        WC = LamportChannel(f"BEN_{eps}_{t}")
        s = SubjectH5DPv3(n, P, sid=f"BEN_{eps}_{t}", contact="verify",
                          world_channel=WC, eps0=eps0, alpha=ALPHA)
        for kk, st in enumerate((0, 3, 6, 9)):
            proj = aperture(W, n, st, 4, f"R{kk}")
            ev, _, _ = deliver_signed(s, proj, WC, rng, retries=2)
            if ev is None:
                continue
            s.receive(ev)
        for kk in range(6):
            proj = aperture(W, n, (2 + 2 * kk) % n, 3, f"T{kk}")
            ev, _, _ = deliver_signed(s, proj, WC, rng, retries=2)
            if ev is None:
                continue
            d = s.receive(ev)
            st_ = DEC(d)
            tr = [r for r in TRACE if r["pid"] == f"T{kk}"]
            events.append({
                "trial": t, "pid": f"T{kk}",
                "anchor": sorted(proj.anchor),
                "status": st_, "reason": d.get("reason", ""),
                "carries_world_violation": any(q in proj.anchor
                                               for q in violations),
                "violations_in_anchor": sorted(q for q in violations
                                               if q in proj.anchor),
                "trace": tr[-1] if tr else None,
            })
    return events


def main():
    print("=" * 70)
    print("DEBUG R13-G2: reproduction of the G2 correlated-violation cells")
    print("=" * 70)
    cells = [(0.05, 0.05), (0.1, 0.05), (0.2, 0.1), (0.3, 0.15),
             (0.1, 0.1), (0.3, 0.1)]
    out = {"cells": {}}
    for eps0, eps in cells:
        TRACE.clear()
        events = benign_traced(eps0, eps=eps)
        sent = len(events)
        rej = [e for e in events if e["status"] not in (GLUED, PARKED)]
        rej_viol = [e for e in rej if e["carries_world_violation"]]
        print(f"\n--- eps0={eps0} eps={eps}: sent={sent} "
              f"rejected={len(rej)} ({len(rej)/sent:.3f}) "
              f"of which world-violation-carrying: {len(rej_viol)}")
        for e in rej:
            tr = e["trace"] or {}
            fails = tr.get("failed_checks", [])
            kinds = {}
            for f in fails:
                kinds.setdefault(f["kind"], []).append(f["pos"])
            impl = set()
            for f in fails:
                impl |= set(f["pos"])
            print(f"  trial {e['trial']} {e['pid']} anchor={e['anchor']} "
                  f"status={e['status']} reason={e['reason']}")
            print(f"    k={tr.get('k')} m={tr.get('m')} pv={tr.get('pvalue')} "
                  f"world_viol@{e['violations_in_anchor']}")
            print(f"    failed checks: {json.dumps(kinds)}")
            print(f"    implicated positions: {sorted(impl)} "
                  f"(clusters={len(impl & set(e['anchor']) | (impl - set(range(16))))})")
        # cluster statistic over ALL rejected events
        out["cells"][f"eps0={eps0}_eps={eps}"] = {
            "sent": sent,
            "rejected": len(rej),
            "rejected_rate": round(len(rej) / sent, 3),
            "rejected_carrying_violation": len(rej_viol),
            "events": [{k: v for k, v in e.items() if k != "trace"}
                       for e in rej],
        }
    # verify reproduction against the R12 JSON
    r12 = json.load(open("/home/z/my-project/download/e12_e15_results.json"))
    print("\n--- reproduction check vs e12_e15_results.json (true_rejected_rate)")
    ok = True
    for eps0, eps in cells:
        want = r12["E12"][f"eps0={eps0}"][f"eps={eps}"]["true_rejected_rate"]
        got = out["cells"][f"eps0={eps0}_eps={eps}"]["rejected_rate"]
        match = "MATCH" if abs(want - got) < 0.011 else "DIFF"
        if match == "DIFF":
            ok = False
        print(f"  eps0={eps0} eps={eps}: R12={want} repro={got} {match}")
    out["reproduction_matches_r12"] = ok
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"\nsaved: {OUT}")


if __name__ == "__main__":
    main()
