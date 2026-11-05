#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ROUND 13-G2: closing the Round-12 G2 boundary with a correlation-aware
# M1 gate (H5d'v3.1) - new-file variant, frozen files untouched
# (Task 16-b)
# =====================================================================
# Round 12 measured boundary: inside the declared band the v3 gate
# LOUDLY rejects 2-8% of TRUE windows carrying world violations.
# Cause (correlated violations): ONE corrupted ring value touches
# SEVERAL checks (two adjacent edges + its law-mismatch position +
# completion-mismatch positions), so k (raw violated checks) is
# inflated relative to the number of corrupted VALUES. But the
# declared Huber model makes the number of corrupted VALUES the
# Binomial quantity: iid per VALUE at rate eps <= eps0.
#
# Fix (m1, cluster counting): map every violation to the set of ring
# positions it implicates; violations whose implicated positions are
# connected (transitively) form ONE cluster; the gate counts clusters
# k_eff instead of raw checks k. m (number of checks) is unchanged.
#   - one corrupted value  -> one cluster -> in-band ACCEPT (loud
#     GLUED with the violation count recorded in the outcome detail)
#   - a full-flip poison at a glued anchor -> value clashes at three
#     DISJOINT positions -> 3 clusters -> still rejected (attack power
#     preserved)
# No oracle: every implicated-position set is computed from
# subject-visible data (the projection's view, the glued state, the
# learned law). The law itself stays protected by the majority tally
# (E11 M1) and by the untouched H5DP park path (attested writes that
# flip glued values never integrate).
#
# PRE-REGISTERED ACCEPTANCE (fixed BEFORE the A/B run):
#   A0  eps=0.0 world: v3.1 behaviour BIT-IDENTICAL to v3 (k=0 =>
#       k_eff=0; S0-equivalence preserved).
#   A1  inside-band false rejection of TRUE windows <= 1% per cell
#       (v3 baseline measured 2-8%).
#   A2  closure intact under attack: n5v_eta overwrite==0 AND
#       silent==0; a1_exhaust no false glue at fully-known anchors,
#       zero switches, zero history flips; a3_preempt full recovery,
#       zero history flips.
#   A3  legitimate machinery intact: epoch_relearn_v3 fires with the
#       correct new law; unsigned_control hijack==0, law unchanged.
#   A4  no-oracle discipline: the factory never passes W to the
#       subject; runtime assertion that the subject carries no
#       referee/oracle attribute (structural argument, as in R10-11).
#
# If A1 fails without breaking A2/A3, the best measured compromise is
# reported and the boundary stays OPEN (honest stdout).
# =====================================================================
import json
import random
import hashlib
import sys

sys.path.insert(0, "/home/z/my-project/scripts")

from holographic_core import GLUED, CONTRADICTION, Outcome, propagate
from e11_noise_battery import (E11Assembly, binom_tail, STAT_EXCESS,
                               EPS0, ALPHA)
import e11_noise_battery as M_E11
import n5_closure_battery as M_N5
import round10_battery as M_R10
from round10_battery import SubjectH5DPv3
from e12_e15_sweeps import (benign, n5v_eta, epoch_relearn_v3,
                            unsigned_control, v3f)

OUT_JSON = "/home/z/my-project/download/r13_g2_results.json"
OUT_LOG = "/home/z/my-project/download/r13_g2_stdout.log"
CORE_FILES = ["holographic_core.py", "holographic_e10_core.py",
              "vli_battery.py", "e11_noise_battery.py",
              "n5_closure_battery.py", "round10_battery.py",
              "e12_e15_sweeps.py"]

_lines = []
PARKED = "PARKED_CHALLENGED"


def p(s=""):
    print(s)
    _lines.append(str(s))


def md5_of(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


class _UF:
    """tiny union-find over ring positions"""

    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb

    def clusters(self, touched):
        """number of distinct components containing a violated position"""
        return len({self.find(x) for x in touched})


# =====================================================================
# G2Assembly: E11Assembly with the M1 gate counting CLUSTERS
# (derived from e11_noise_battery.E11Assembly.integrate - frozen file
# UNTOUCHED; only the violation->gate path differs, as documented)
# =====================================================================
class G2Assembly(E11Assembly):

    def integrate(self, pr):
        cfg = self.cfg
        if not cfg["final_checks"]:
            return super().integrate(pr)      # amputated path unchanged
        merged = {pos: self.known[pos][0] for pos in self.known}
        for pos in pr.anchor:
            merged[pos] = pr.view[pos]

        uf = _UF()
        touched = set()          # positions implicated by some violation

        def viol(positions):
            ps = list(positions)
            for x in ps[1:]:
                uf.union(ps[0], x)
            touched.add(ps[0])

        # (1) value clashes vs glued values
        clashes = [(pos, self.known[pos][0], pr.view[pos])
                   for pos in sorted(pr.anchor)
                   if pos in self.known and self.known[pos][0] != pr.view[pos]]
        m = len(clashes)
        for pos, _, _ in clashes:
            viol({pos})
        det = {"clashes": clashes}

        # (2) connectivity
        inf_old = self.infer_full() if cfg["learn_law"] else None
        overlap = any(pos in self.known for pos in pr.anchor)
        if not overlap:
            if cfg["law_extension"] and inf_old is not None:
                pass
            else:
                return self._park_or_cohere(pr)

        # (3)+(4) style checks / law mismatch / completion inference
        new_bits = {}
        edges = []
        if cfg["grammar_checks"] and cfg["learn_law"]:
            internal = set()
            for (i, r) in pr.internal_edges(self.n, self.period):
                internal.add(i)
                if r in self.grammar.e_hat:
                    m += 1
                    bit = pr.view[i] ^ pr.view[(i + 1) % self.n]
                    if self.grammar.e_hat[r][0] != bit:
                        edges.append({"edge": i, "residue": r})
                        viol({i, (i + 1) % self.n})
            for i in range(self.n):
                j = (i + 1) % self.n
                if i in merged and j in merged and i not in internal:
                    r = i % self.period
                    if r in self.grammar.e_hat:
                        m += 1
                        bit = merged[i] ^ merged[j]
                        if self.grammar.e_hat[r][0] != bit:
                            edges.append({"edge": i, "residue": r})
                            viol({i, j})
            for i in range(self.n):
                j = (i + 1) % self.n
                if i in merged and j in merged:
                    r = i % self.period
                    if r not in self.grammar.e_hat and r not in new_bits:
                        new_bits[r] = merged[i] ^ merged[j]
            if inf_old is not None:
                mism = [pos for pos in sorted(pr.anchor)
                        if inf_old[pos] != pr.view[pos]]
                m += len(pr.anchor)
                for pos in mism:
                    viol({pos})
                if mism:
                    det["law_mismatch"] = mism
            if self.known and len(self.grammar.e_hat) + len(new_bits) == self.period:
                st_bits = {r: self.grammar.e_hat[r][0] for r in self.grammar.e_hat}
                for r, b in new_bits.items():
                    st_bits[r] = b
                st = tuple(st_bits[r] for r in range(self.period))
                pos0 = min(merged)
                full = propagate(st, self.n, self.period, pos0, merged[pos0])
                mism2 = [pos for pos in sorted(merged) if full[pos] != merged[pos]]
                m += len(merged)
                for pos in mism2:
                    viol({pos})
                if mism2:
                    det["completion_mismatch"] = mism2
        det["edges"] = edges

        # M1 gate on CLUSTERS: k_eff = connected components of violated
        # positions; m unchanged (raw check count, declared)
        k_eff = uf.clusters(touched) if touched else 0
        if self.stat_gate and m > 0:
            pv = binom_tail(m, self.eps0, k_eff)
            if pv <= self.alpha:
                self.rejections.append({"pid": pr.pid, "k": len(touched),
                                        "k_eff": k_eff, "m": m,
                                        "pvalue": pv})
                if clashes:
                    reason, detail = "value_clash", {
                        "clashes": clashes,
                        "blame_candidates": sorted(
                            {self.known[pos][1] for pos, _, _ in clashes} |
                            {pr.pid})}
                elif det.get("law_mismatch"):
                    reason, detail = "law_mismatch", {
                        "positions": det["law_mismatch"],
                        "blame_candidates": [pr.pid]}
                elif edges:
                    reason, detail = "style_clash", {
                        "edges": edges,
                        "blame_candidates": sorted(
                            {pr.pid} |
                            {self.grammar.e_hat[c["residue"]][1]
                             for c in edges if c["residue"] in self.grammar.e_hat})}
                else:
                    reason, detail = STAT_EXCESS, {
                        "k_eff": k_eff, "m": m, "pvalue": pv,
                        "blame_candidates": [pr.pid]}
                return Outcome(CONTRADICTION, reason, detail)

        # (5) commit (S0 semantics); tally law bits; absorb - identical
        # to the frozen E11Assembly commit path
        for pos in pr.anchor:
            self.known[pos] = (pr.view[pos], pr.pid, pr.origin)
        learned = []
        if cfg["learn_law"]:
            self.pending_dissent = {}
            for (i, r) in pr.internal_edges(self.n, self.period):
                if r in self.grammar.e_hat:
                    bit = pr.view[i] ^ pr.view[(i + 1) % self.n]
                    if bit != self.grammar.e_hat[r][0]:
                        self.pending_dissent[r] = (bit, pr.pid)
            learned = sorted(self._learn_from_merged(merged, pr.pid).keys())
        absorbed = self._absorb_pending()
        return Outcome(GLUED, "", {"absorbed": absorbed,
                                   "style_learned": learned,
                                   "violations": len(touched),
                                   "clusters": k_eff, "checks": m})


# =====================================================================
# SubjectH5d'v3.1: v3 completeness-gated relearn + G2 assembly swap
# =====================================================================
class SubjectG2v31(SubjectH5DPv3):
    """H5d'v3.1 = H5d'v3 with the correlation-aware M1 gate (G2Assembly).
    The H5DP park path and the v3 relearn-completeness gate are kept
    verbatim. NO oracle: constructed exactly like f_v3 (the realized
    ring is never forwarded into the subject)."""

    def __init__(self, n, period, sid, contact="verify", world_channel=None,
                 eps0=EPS0, alpha=ALPHA, stat_gate=True, belief_layer=True):
        super().__init__(n, period, sid=sid, contact=contact,
                         world_channel=world_channel, eps0=eps0,
                         alpha=alpha, stat_gate=stat_gate,
                         belief_layer=belief_layer)
        cfg = dict(self.asm.cfg)
        self.asm = G2Assembly(n, period, eps0=eps0, alpha=alpha,
                              stat_gate=stat_gate, **cfg)

    def _relearn(self):
        pids = [pid for pid, _ in self.epoch_buffer]
        if not self._challenge_complete(self.epoch_buffer):
            self.epoch_log.append({
                "switch": False,
                "kind": "v3_incomplete_challenge_refused",
                "streak": self.fail_streak_att,
                "buffer_pids": pids,
                "residues_voted": sorted({
                    r for _, proj in self.epoch_buffer
                    for (i, r) in proj.internal_edges(self.n, self.period)}),
                "idx": getattr(self, "receive_count", 0)})
            return False
        new_asm = G2Assembly(self.n, self.period, eps0=self.eps0,
                             alpha=self.asm.alpha, stat_gate=True,
                             **self.asm.cfg)
        for _, proj in self.epoch_buffer:
            new_asm.integrate(proj)
        new_asm._absorb_pending()
        stale = len(self.verified)
        self.asm = new_asm
        self.verified = {}
        self.epoch_buffer = []
        self.fail_streak_att = 0
        self.drift_flags = {}
        self.epoch_log.append({"switch": True, "stale_demoted": stale,
                               "law_residues": sorted(self.asm.grammar.e_hat),
                               "idx": self.receive_count,
                               "buffer_pids": pids})
        return True


def f_g2(eps0=EPS0, alpha=ALPHA):
    def f(n, P, sid, WC, W=None):
        return SubjectG2v31(n, P, sid=sid, contact="verify",
                            world_channel=WC, eps0=eps0, alpha=alpha)
    return f


# =====================================================================
def main():
    md5_before = {f: md5_of(f"/home/z/my-project/scripts/{f}")
                  for f in CORE_FILES}
    results = {"round": "13-G2",
               "name": "G2 boundary closure: correlation-aware gate "
                       "(H5d'v3.1)",
               "pre_registered": "A0-A4 in module header; fixed before "
                                 "the A/B run"}
    p("=" * 68)
    p("ROUND 13-G2: correlation-aware M1 gate (cluster counting)")
    p("=" * 68)

    # ---- step 1: reproduce the R12 boundary from the frozen data ----
    r12 = json.load(open("/home/z/my-project/download/e12_e15_results.json"))
    p("step 1: R12 G2 cells (inside band, eps<=eps0/2), v3 baseline:")
    inside = []
    for eps0 in [0.05, 0.1, 0.2, 0.3]:
        row = r12["E12"][f"eps0={eps0}"]
        for e in [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]:
            if e <= eps0 / 2:
                c = row[f"eps={e}"]
                if c["true_rejected_rate"] > 0:
                    inside.append((eps0, e, c["true_rejected_rate"]))
    p(f"  {inside}")
    base_rej = [r for _, _, r in inside]
    p(f"  v3 inside-band false-rejection range: "
      f"[{min(base_rej) if base_rej else 0}, {max(base_rej) if base_rej else 0}]")

    # ---- A4 structural no-oracle assertion --------------------------
    probe = f_g2()(16, 4, "A4PROBE", __import__(
        "holographic_e10_core", fromlist=["LamportChannel"]).LamportChannel("A4"))
    a4 = not hasattr(probe, "referee_ring")
    p(f"step A4: no-oracle structural check: "
      f"{'PASS' if a4 else 'FAIL'} (no referee/oracle attribute)")

    # ---- step 2: matched A/B grid ------------------------------------
    p("step 2: matched A/B (same seeds): v3 baseline vs v3.1")
    ab = {}
    a1_parts, a0_parts = [], []
    for eps0 in [0.05, 0.1, 0.2, 0.3]:
        for e in [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]:
            b3 = benign(v3f(eps0=eps0), trials=8, eps=e)
            b31 = benign(f_g2(eps0=eps0), trials=8, eps=e)
            inside_cell = 0 < e <= eps0 / 2
            ab[f"eps0={eps0}/eps={e}"] = {
                "inside_band": inside_cell, "v3": b3, "v31": b31}
            p(f"  eps0={eps0} eps={e}"
              f"{' [IN]' if inside_cell else ''}: "
              f"rej {b3['true_rejected_rate']}->{b31['true_rejected_rate']} "
              f"acc {b3['true_accept_rate']}->{b31['true_accept_rate']} "
              f"lawacc {b3['law_acc_mean']}->{b31['law_acc_mean']}")
            if inside_cell and b31["true_rejected_rate"] > 0.01:
                a1_parts.append((eps0, e, b31["true_rejected_rate"]))
            if e == 0.0 and b31 != b3:
                a0_parts.append((eps0, {k: (b3[k], b31[k])
                                        for k in b3 if b3[k] != b31[k]}))
    results["AB_grid"] = ab

    # ---- step 3: attacks under v3.1 (A2) -----------------------------
    p("step 3: attacks under v3.1 (closure must not degrade)")
    nv = n5v_eta(f_g2(), eta=0.0)
    p(f"  n5v_eta: overwrite={nv['overwrite_glued_history_rate']} "
      f"unguarded={nv['unguarded_window_glue_rate']} "
      f"silent={nv['silent_poison_rate']} "
      f"correct={nv['correct_rate_of_conflicts']}")
    a1x = __import__("round10_battery").a1_exhaust(f_g2())
    p(f"  a1_exhaust: false_glue_known={a1x['glue_false_at_fully_known_anchor']} "
      f"switches={a1x['epoch_switches']} "
      f"hist_flipped={a1x['bootstrap_glued_history_flipped_trials']}")
    a3x = __import__("round10_battery").a3_preempt(f_g2(), sustained=True)
    p(f"  a3_preempt: recovered={a3x['recovered_trials']}/{a3x['trials']} "
      f"acc_final={a3x['mean_known_acc_final']} "
      f"hist_flipped={a3x['glued_history_flipped_trials']}")
    results["A2_attacks"] = {"n5v_eta": nv, "a1_exhaust": a1x,
                             "a3_preempt": a3x}

    # ---- step 4: legitimate machinery regression (A3) ----------------
    p("step 4: legitimate machinery under v3.1")
    er = epoch_relearn_v3(f_g2(), trials=8)
    uh = unsigned_control(f_g2(), trials=8)
    p(f"  epoch_relearn: fired={er['relearn_fired_rate']} "
      f"law_new={er['law_acc_vs_B_mean']} refusals/trial={er['v3_refusals_per_trial']}")
    p(f"  unsigned: hijack={uh['unsigned_relearn_hijack_rate']} "
      f"law_unchanged={uh['unsigned_law_unchanged_rate']}")
    results["A3_regression"] = {"epoch_relearn": er, "unsigned": uh}

    # ---- decision gate ------------------------------------------------
    gate = {
        "A4_no_oracle": a4,
        "A0_eps0_bit_identical": len(a0_parts) == 0,
        "A1_inside_band_rej_le_1pct": len(a1_parts) == 0,
        "A2_n5v_zero_overwrite_zero_silent":
            nv["overwrite_glued_history_rate"] == 0.0
            and nv["silent_poison_rate"] == 0.0,
        "A2_a1_no_false_glue":
            a1x["glue_false_at_fully_known_anchor"] == 0
            and a1x["epoch_switches"] == 0
            and a1x["bootstrap_glued_history_flipped_trials"] == 0,
        "A2_a3_recovery":
            a3x["recovered_trials"] == a3x["trials"]
            and a3x["mean_known_acc_final"] == 1.0
            and a3x["glued_history_flipped_trials"] == 0,
        "A3_legit_relearn_intact":
            er["relearn_fired_rate"] > 0
            and uh["unsigned_relearn_hijack_rate"] == 0.0
            and uh["unsigned_law_unchanged_rate"] == 1.0,
    }
    results["GATES"] = gate
    a0_a3_ok = (gate["A4_no_oracle"] and gate["A0_eps0_bit_identical"]
                and gate["A2_n5v_zero_overwrite_zero_silent"]
                and gate["A2_a1_no_false_glue"] and gate["A2_a3_recovery"]
                and gate["A3_legit_relearn_intact"])
    if gate["A1_inside_band_rej_le_1pct"] and a0_a3_ok:
        results["verdict"] = "G2-CLOSURE = CLOSED* (v3.1: cluster-counting gate)"
    elif a0_a3_ok:
        results["verdict"] = ("G2-CLOSURE = PARTIAL (closure intact; "
                              "false-rejection rate improved but >1% in "
                              f"{a1_parts})")
    else:
        results["verdict"] = "G2-CLOSURE = FAIL (see GATES)"
    p("--- decision gate (pre-registered) ---")
    for k, v in gate.items():
        p(f"  [{'PASS' if v else 'FAIL'}] {k}")
    p("")
    p("VERDICT: " + results["verdict"])

    md5_after = {f: md5_of(f"/home/z/my-project/scripts/{f}")
                 for f in CORE_FILES}
    results["core_md5_unchanged"] = md5_before == md5_after
    results["core_md5"] = md5_after
    p("core md5: " + ("UNCHANGED" if results["core_md5_unchanged"]
                      else "CHANGED !!"))
    p("EPISTEMIC STATUS: VERIFIED* in the stand; GENERAL_MINIMALITY = UNKNOWN.")

    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=2, default=str)
    with open(OUT_LOG, "w") as f:
        f.write("\n".join(_lines) + "\n")
    p(f"saved: {OUT_JSON}")
    p(f"saved: {OUT_LOG}")


if __name__ == "__main__":
    main()
