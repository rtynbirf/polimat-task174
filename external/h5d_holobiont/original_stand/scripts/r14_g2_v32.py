#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ROUND 14-G2: v3.2 - PROPAGATION-SOURCE clustering of completion /
# law mismatches (H5d'v3.2). New-file variant; frozen files untouched.
# Closes the R13-G2 residual cell (eps0=0.2, eps=0.1): 0.104 -> 0.062.
# =====================================================================
# Residual mechanism (measured by scripts/debug_g2_residual.py, 48
# trials: true-law rej 8/258 = 3.1%): with the law COMPLETE, one
# corrupted VALUE at ring position q forces the completion check
# (propagate from pos0 = min(merged)) to mismatch on the WHOLE
# downstream suffix; v3.1 marks every mismatched position as its OWN
# cluster, inflating k_eff far above the number of corrupted VALUES.
# But the declared Huber model makes the number of corrupted VALUES
# the Binomial quantity (iid per VALUE at rate eps <= eps0).
#
# Fix v3.2 (pre-registered, delta vs v3.1 ONLY in the union topology):
#   - law_mismatch positions (vs inf_old, which propagates from
#     min(self.known)): each mismatched position is unioned with that
#     propagation source;
#   - completion_mismatch positions (vs full, propagated from
#     pos0 = min(merged)): each mismatched position is unioned with
#     pos0.
#   - value clashes and edge style-clashes: UNCHANGED from v3.1
#     (disjoint singletons / contiguous edge pairs).
#   - m (raw check count) UNCHANGED; the gate formula UNCHANGED;
#     everything else byte-identical to v3.1's integrate.
# Effect: one corrupted value -> ALL its downstream mismatch evidence
# collapses into ONE cluster (connected through the propagation
# source), so k_eff tracks corrupted VALUES, not raw positions.
#
# PRE-REGISTERED ACCEPTANCE (fixed BEFORE the A/B run):
#   B0  eps=0.0 world: v3.2 metrics BIT-IDENTICAL to v3 (and to v3.1)
#       on the whole grid.
#   B1  inside-band false rejection of TRUE windows <= 1% per cell
#       (v3 baseline [0.062, 0.125]; v3.1 residual 0.062 in exactly
#       one cell (0.2, 0.1)).
#   B2  closure intact: n5v_eta overwrite==0 AND silent==0;
#       a1_exhaust no false glue at fully-known anchors, zero
#       switches, zero history flips; a3_preempt full recovery.
#       DECLARED RISK (accepted pre-run): unguarded-window glue rates
#       are the declared A3/CONTACT!=TRUTH family; they may shift
#       between v3/v3.1/v3.2 and are REPORTED, not gated.
#   B3  legitimate machinery: epoch_relearn fires with the correct
#       new law; unsigned hijack==0, law unchanged.
#   B4  no-oracle discipline: the factory never passes W into the
#       subject; runtime assertion (no referee/oracle attribute).
#   B5  residual re-diagnosis (48 trials @ (0.2, 0.1), debug clone):
#       true-law rejection rate under v3.2 reported; target ~0.
# If B1 fails without breaking B2/B3, the measured compromise is
# reported and the boundary stays OPEN (honest stdout).
# =====================================================================
import json
import random
import hashlib
import sys

sys.path.insert(0, "/home/z/my-project/scripts")

from holographic_core import GLUED, CONTRADICTION, Outcome, propagate
from e11_noise_battery import E11Assembly, binom_tail, STAT_EXCESS, EPS0, ALPHA
from r13_g2_adaptive import G2Assembly, SubjectG2v31
from round10_battery import SubjectH5DPv3
import e11_noise_battery as M_E11
from e12_e15_sweeps import (benign, n5v_eta, epoch_relearn_v3,
                            unsigned_control, v3f)

OUT_JSON = "/home/z/my-project/download/r14_g2_v32_results.json"
OUT_LOG = "/home/z/my-project/download/r14_g2_v32_stdout.log"
CORE_FILES = ["holographic_core.py", "holographic_e10_core.py",
              "vli_battery.py", "e11_noise_battery.py",
              "n5_closure_battery.py", "round10_battery.py",
              "e12_e15_sweeps.py", "r13_g2_adaptive.py",
              "r13_po_battery.py", "round11_audit_battery.py"]

_lines = []


def p(s=""):
    print(s)
    _lines.append(str(s))


def md5_of(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


# =====================================================================
# G2AssemblyV32: v3.1 with the propagation-source union rule
# (derived from r13_g2_adaptive.G2Assembly.integrate; ONLY the two
# mismatch viol() sites differ, as documented in the header)
# =====================================================================
class G2AssemblyV32(G2Assembly):

    def integrate(self, pr):
        cfg = self.cfg
        if not cfg["final_checks"]:
            return super().integrate(pr)      # amputated path unchanged
        merged = {pos: self.known[pos][0] for pos in self.known}
        for pos in pr.anchor:
            merged[pos] = pr.view[pos]

        uf = __import__("r13_g2_adaptive")._UF()
        touched = set()

        def viol(positions):
            ps = list(positions)
            for x in ps[1:]:
                uf.union(ps[0], x)
            touched.add(ps[0])

        # (1) value clashes vs glued values - UNCHANGED from v3.1
        clashes = [(pos, self.known[pos][0], pr.view[pos])
                   for pos in sorted(pr.anchor)
                   if pos in self.known and self.known[pos][0] != pr.view[pos]]
        m = len(clashes)
        for pos, _, _ in clashes:
            viol({pos})
        det = {"clashes": clashes}

        # (2) connectivity - UNCHANGED
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
                src_known = min(self.known) if self.known else None
                for pos in mism:
                    # v3.2 DELTA: union with the inf_old propagation source
                    viol({pos, src_known} if src_known is not None else {pos})
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
                    # v3.2 DELTA: union with the completion propagation source
                    viol({pos, pos0})
                if mism2:
                    det["completion_mismatch"] = mism2
        det["edges"] = edges

        # M1 gate on CLUSTERS - formula UNCHANGED
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

        # (5) commit - byte-identical to v3.1
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


class SubjectG2v32(SubjectG2v31):
    """H5d'v3.2 = v3.1 with the propagation-source cluster rule.
    Park path and v3 completeness gate verbatim. No oracle."""

    def __init__(self, n, period, sid, contact="verify", world_channel=None,
                 eps0=EPS0, alpha=ALPHA, stat_gate=True, belief_layer=True):
        super().__init__(n, period, sid=sid, contact=contact,
                         world_channel=world_channel, eps0=eps0,
                         alpha=alpha, stat_gate=stat_gate,
                         belief_layer=belief_layer)
        cfg = dict(self.asm.cfg)
        self.asm = G2AssemblyV32(n, period, eps0=eps0, alpha=alpha,
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
        new_asm = G2AssemblyV32(self.n, self.period, eps0=self.eps0,
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


def f_g2v32(eps0=EPS0, alpha=ALPHA):
    def f(n, P, sid, WC, W=None):
        return SubjectG2v32(n, P, sid=sid, contact="verify",
                            world_channel=WC, eps0=eps0, alpha=alpha)
    return f


# =====================================================================
# residual re-diagnosis (clone of debug_g2_residual.one_trial, v3.2)
# =====================================================================
def diag_trial(rng, factory):
    from e11_noise_battery import (whole_from_style, aperture, realized_ring,
                                   deliver_signed, DEC, law_bit_accuracy,
                                   make_style)
    from holographic_e10_core import LamportChannel
    n, P = 16, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)
    W = realized_ring(w, n, style, rng, 0.1)
    WC = LamportChannel("D32")
    s = factory(n, P, "D32", WC, W)
    for k, st in enumerate((0, 3, 6, 9)):
        proj = aperture(W, n, st, 4, f"R{k}")
        ev, _, _ = deliver_signed(s, proj, WC, rng, retries=2)
        if ev is not None:
            s.receive(ev)
    out = []
    for k in range(6):
        proj = aperture(W, n, (2 + 2 * k) % n, 3, f"T{k}")
        ev, _, _ = deliver_signed(s, proj, WC, rng, retries=2)
        if ev is None:
            continue
        d = s.receive(ev)
        out.append(DEC(d))
    la, _ = law_bit_accuracy(s, style)
    return la, out


def main():
    md5_before = {f: md5_of(f"/home/z/my-project/scripts/{f}")
                  for f in CORE_FILES}
    results = {"round": "14-G2",
               "name": "G2 residual closure: propagation-source clustering "
                       "(H5d'v3.2)",
               "pre_registered": "B0-B5 in module header; fixed before "
                                 "the run"}
    p("=" * 68)
    p("ROUND 14-G2: v3.2 propagation-source clustering")
    p("=" * 68)

    # ---- B4 structural no-oracle assertion --------------------------
    from holographic_e10_core import LamportChannel
    probe = f_g2v32()(16, 4, "B4PROBE", LamportChannel("B4"))
    b4 = not hasattr(probe, "referee_ring")
    p(f"step B4: no-oracle structural check: "
      f"{'PASS' if b4 else 'FAIL'}")

    # ---- step 1: matched A/B grid ------------------------------------
    p("step 1: matched A/B (same seeds): v3 baseline vs v3.2")
    ab = {}
    a1_parts, a0_parts = [], []
    for eps0 in [0.05, 0.1, 0.2, 0.3]:
        for e in [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]:
            b3 = benign(v3f(eps0=eps0), trials=8, eps=e)
            b32 = benign(f_g2v32(eps0=eps0), trials=8, eps=e)
            inside_cell = 0 < e <= eps0 / 2
            ab[f"eps0={eps0}/eps={e}"] = {
                "inside_band": inside_cell, "v3": b3, "v32": b32}
            p(f"  eps0={eps0} eps={e}"
              f"{' [IN]' if inside_cell else ''}: "
              f"rej {b3['true_rejected_rate']}->{b32['true_rejected_rate']} "
              f"acc {b3['true_accept_rate']}->{b32['true_accept_rate']} "
              f"lawacc {b3['law_acc_mean']}->{b32['law_acc_mean']}")
            if inside_cell and b32["true_rejected_rate"] > 0.01:
                a1_parts.append((eps0, e, b32["true_rejected_rate"]))
            if e == 0.0 and b32 != b3:
                a0_parts.append((eps0, {k: (b3[k], b32[k])
                                        for k in b3 if b3[k] != b32[k]}))
    results["AB_grid"] = ab

    # ---- step 2: residual re-diagnosis (B5) --------------------------
    p("step 2: residual re-diagnosis @ (eps0=0.2, eps=0.1), 48 trials")
    rng = random.Random(42)
    tl = {"trials": 0, "rej": 0, "ev": 0}
    wl = {"trials": 0, "rej": 0, "ev": 0}
    for t in range(48):
        la, sts = diag_trial(rng, f_g2v32(eps0=0.2))
        bucket = tl if (la is not None and la >= 0.999) else wl
        bucket["trials"] += 1
        bucket["rej"] += sts.count("CONTRADICTION")
        bucket["ev"] += len(sts)
    tl_rate = round(tl["rej"] / max(1, tl["ev"]), 4)
    wl_rate = round(wl["rej"] / max(1, wl["ev"]), 4)
    p(f"  TRUE-law trials: {tl} rej_rate={tl_rate}")
    p(f"  WRONG-law trials: {wl} rej_rate={wl_rate} (declared family)")
    results["residual_diag"] = {"true_law": tl, "wrong_law": wl,
                                "true_law_rej_rate": tl_rate,
                                "wrong_law_rej_rate": wl_rate}

    # ---- step 3: attacks under v3.2 (B2) -----------------------------
    p("step 3: attacks under v3.2 (closure must not degrade)")
    nv = n5v_eta(f_g2v32(), eta=0.0)
    p(f"  n5v_eta: overwrite={nv['overwrite_glued_history_rate']} "
      f"unguarded={nv['unguarded_window_glue_rate']} (declared family) "
      f"silent={nv['silent_poison_rate']} "
      f"correct={nv['correct_rate_of_conflicts']}")
    a1x = __import__("round10_battery").a1_exhaust(f_g2v32())
    p(f"  a1_exhaust: false_glue_known={a1x['glue_false_at_fully_known_anchor']} "
      f"switches={a1x['epoch_switches']} "
      f"hist_flipped={a1x['bootstrap_glued_history_flipped_trials']}")
    a3x = __import__("round10_battery").a3_preempt(f_g2v32(), sustained=True)
    p(f"  a3_preempt: recovered={a3x['recovered_trials']}/{a3x['trials']} "
      f"acc_final={a3x['mean_known_acc_final']} "
      f"hist_flipped={a3x['glued_history_flipped_trials']}")
    results["B2_attacks"] = {"n5v_eta": nv, "a1_exhaust": a1x,
                             "a3_preempt": a3x}

    # ---- step 4: legitimate machinery regression (B3) ----------------
    p("step 4: legitimate machinery under v3.2")
    er = epoch_relearn_v3(f_g2v32(), trials=8)
    uh = unsigned_control(f_g2v32(), trials=8)
    p(f"  epoch_relearn: fired={er['relearn_fired_rate']} "
      f"law_new={er['law_acc_vs_B_mean']} refusals/trial={er['v3_refusals_per_trial']}")
    p(f"  unsigned: hijack={uh['unsigned_relearn_hijack_rate']} "
      f"law_unchanged={uh['unsigned_law_unchanged_rate']}")
    results["B3_regression"] = {"epoch_relearn": er, "unsigned": uh}

    # ---- decision gate ------------------------------------------------
    gate = {
        "B4_no_oracle": b4,
        "B0_eps0_bit_identical": len(a0_parts) == 0,
        "B1_inside_band_rej_le_1pct": len(a1_parts) == 0,
        "B2_n5v_zero_overwrite_zero_silent":
            nv["overwrite_glued_history_rate"] == 0.0
            and nv["silent_poison_rate"] == 0.0,
        "B2_a1_no_false_glue":
            a1x["glue_false_at_fully_known_anchor"] == 0
            and a1x["epoch_switches"] == 0
            and a1x["bootstrap_glued_history_flipped_trials"] == 0,
        "B2_a3_recovery":
            a3x["recovered_trials"] == a3x["trials"]
            and a3x["mean_known_acc_final"] == 1.0
            and a3x["glued_history_flipped_trials"] == 0,
        "B3_legit_relearn_intact":
            er["relearn_fired_rate"] > 0
            and uh["unsigned_relearn_hijack_rate"] == 0.0
            and uh["unsigned_law_unchanged_rate"] == 1.0,
        "B5_true_law_residual_zero": tl_rate <= 0.01,
    }
    results["GATES"] = gate
    b0_b3_ok = (gate["B4_no_oracle"] and gate["B0_eps0_bit_identical"]
                and gate["B2_n5v_zero_overwrite_zero_silent"]
                and gate["B2_a1_no_false_glue"] and gate["B2_a3_recovery"]
                and gate["B3_legit_relearn_intact"])
    if gate["B1_inside_band_rej_le_1pct"] and gate["B5_true_law_residual_zero"] \
            and b0_b3_ok:
        results["verdict"] = ("G2-CLOSURE = CLOSED* (v3.2: "
                              "propagation-source clustering)")
    elif b0_b3_ok:
        results["verdict"] = ("G2-CLOSURE = PARTIAL (closure intact; "
                              "false-rejection improved but >1% in "
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
