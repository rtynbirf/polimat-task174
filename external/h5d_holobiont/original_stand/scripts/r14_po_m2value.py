#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ROUND 14-PO: the M2-VALUE channel - tentative relearn import +
# diversity-priced demotion (H5d'v3 + M2V). New-file variant; frozen
# files untouched. Targets the R13-PO residual: PO4 rho=0.2
# known_acc_mean 0.938 (transient: relearn imports a law-clean parked
# poison from the epoch buffer; loud switch; acc_after_attack 1.0).
# =====================================================================
# Mechanism measured in R13 (traces): the epoch buffer at rho=0.2 is a
# VACUUM-COHERENT mix (disjoint anchors): parked law-clean poison +
# parked true events. The v3 completeness gate is value-blind BY
# DESIGN (CONTACT != TRUTH): a law-clean poison is structurally
# indistinguishable from a legitimate epoch change AT IMPORT TIME.
# So the honest mechanism is not better import filtering (impossible
# without an oracle) but CHEAPER SELF-CORRECTION after import:
#
#   M2V-1 (tentative import): values imported by _relearn enter the
#        new assembly marked TENTATIVE (the VLI belief-layer notion).
#        They are full citizens for inference, but the demotion ledger
#        may remove them (see M2V-2). Closure-layer values (glued
#        outside the relearn import) are NEVER ledger-demotable.
#   M2V-2 (diversity-priced demotion): every ATTESTED park records
#        (position -> alternative value -> set of supporting anchors).
#        When a TENTATIVE position accumulates >= V_MIN supporting
#        events with PAIRWISE-DISTINCT anchors (copies never count as
#        diversity - the X4b lesson: "three copies of one parasitic
#        signal are not an independent ecosystem") all agreeing on the
#        same alternative value, the tentative value is demoted (loud,
#        logged; the position becomes re-coverable by contact).
#
# PRE-REGISTERED ACCEPTANCE (fixed BEFORE the run):
#   Q1  closure: SILENT overwrite == 0 across the whole grid
#       (silent = boot-glued value replaced with NO switch AND no
#       demotion/ledger trace); poison_glued_overwrite == 0.
#       DECLARED RISK (accepted pre-run): a single multi-window
#       attacker may in principle reach the demotion price against
#       TENTATIVE values; measured by probe D-3 and the grid; any such
#       replacement carries a ledger trace (with-trace class).
#   Q2  loudness: every value replacement is accompanied (switch or
#       demotion log); zero no-trace overwrites anywhere.
#   Q3  recovery: on the P3-failing cell (PO4 rho=0.2):
#       known_acc_mean >= 0.95 AND acc_after_attack_mean == 1.0;
#       rho=0.1/0.3 recovery non-degrading vs r13 (0.972/0.86
#       measured baselines reported side by side).
#   Q4  no-regression: attack-free cells (drop rho=0/0.2) metrics
#       IDENTICAL to the r13-PO attack-free cells (same crc32 seeds,
#       same names) - the ledger must be a no-op without parked
#       clashes; and PO4 rho=0.2 A/B: M2V switches_after_boot <= v3.
#   Q5  no-oracle: the ledger reads only subject-visible state
#       (parks, anchors, values); runtime assertion (no referee).
#   D-3 price probe (single attacker, one channel, distinct-anchor
#       parks against a tentative value): demotion either does not
#       fire or fires with a ledger trace; reported as measured.
# =====================================================================
import json
import random
import hashlib
import sys
import zlib

sys.path.insert(0, "/home/z/my-project/scripts")

from e11_noise_battery import (make_style, whole_from_style, aperture,
                               realized_ring, deliver_signed, DEC,
                               law_bit_accuracy, acc_known_of, EPS0)
import e11_noise_battery as M_E11
from e11_noise_battery import _pk_key
from holographic_e10_core import LamportChannel
from n5_closure_battery import Projection, recorded_event
from round10_battery import SubjectH5DPv3, refusal_count

OUT_JSON = "/home/z/my-project/download/r14_po_m2value_results.json"
OUT_LOG = "/home/z/my-project/download/r14_po_m2value_stdout.log"
CORE_FILES = ["holographic_core.py", "holographic_e10_core.py",
              "vli_battery.py", "e11_noise_battery.py",
              "n5_closure_battery.py", "round10_battery.py",
              "e12_e15_sweeps.py", "r13_g2_adaptive.py",
              "r13_po_battery.py", "round11_audit_battery.py"]

_lines = []
PARKED = "PARKED_CHALLENGED"
GLUED = "GLUED"


def p(s=""):
    print(s)
    _lines.append(str(s))


def md5_of(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


# =====================================================================
# SubjectM2V: v3 + tentative relearn import + diversity-priced demotion
# =====================================================================
class SubjectM2V(SubjectH5DPv3):
    V_MIN_VALUE = 3          # diverse attested parks to demote (=V_MIN)

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.tentative = set()      # positions imported by the last relearn
        self.value_ledger = {}      # pos -> {alt_value: {"anchors": set,
        #                                      "pids": set}}
        self.demotion_log = []

    # ------------------------------------------------- relearn import
    def _relearn(self):
        fired = super()._relearn()
        if fired:
            self.tentative = set(self.asm.known.keys())
        return fired

    # ---------------------------------------------------- receive wrap
    def receive(self, ev):
        pk = None
        if ev.lamport is not None:
            pk = _pk_key(ev.lamport[0])
        d = super().receive(ev)
        if (isinstance(d, dict) and d.get("status") == PARKED
                and d.get("clash_positions") and pk is not None):
            for pos in d["clash_positions"]:
                alt = ev.proj.view[pos]
                led = self.value_ledger.setdefault(
                    pos, {}).setdefault(
                    alt, {"anchors": set(), "pids": set()})
                led["anchors"].add(frozenset(ev.proj.anchor))
                led["pids"].add(ev.pid)
                cur = self.asm.known.get(pos)
                if (pos in self.tentative and cur is not None
                        and cur[0] != alt
                        and len(led["anchors"]) >= self.V_MIN_VALUE):
                    # diversity-priced demotion (loud)
                    del self.asm.known[pos]
                    self.verified.pop(pos, None)
                    self.tentative.discard(pos)
                    self.demotion_log.append({
                        "pos": pos, "demoted": cur[0], "alt": alt,
                        "anchor_diversity": len(led["anchors"]),
                        "pids": len(led["pids"]),
                        "idx": getattr(self, "receive_count", 0)})
                    self.epoch_log.append({"kind": "m2_value_demotion",
                                           "pos": pos, "alt": alt})
        return d


def f_m2v(n, P, sid, WC, W=None):
    return SubjectM2V(n, P, sid=sid, contact="verify", world_channel=WC)


def f_v3(n, P, sid, WC, W=None):
    return SubjectH5DPv3(n, P, sid=sid, contact="verify", world_channel=WC)


# ------------------------------------------------------------------
# po_trial: derived from r13_po_battery.po_trial (frozen file
# untouched); deltas: (1) factory parameter; (2) demotion/trace
# metrics; (3) attacker channel diversity bookkeeping.
# ------------------------------------------------------------------
PROBE_STARTS = [1, 4, 7, 10, 13, 2, 5, 8]


def po_trial(rng, mode, rho=0.0, L=2, attack=False, factory=f_m2v):
    n, P = 16, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)
    W = realized_ring(w, n, style, rng, 0.05)
    WC = LamportChannel(f"PO_{mode}_{rho}")
    WCx = LamportChannel(f"POx_{mode}_{rho}")
    s = factory(n, P, "PO", WC, W)
    boot_pids = []

    def deliver(proj, wc, retries=2):
        ev, _, _ = deliver_signed(s, proj, wc, rng, retries=retries)
        return ev

    boot_mask = [True, True, True, True]
    if mode == "drop" and rho > 0:
        boot_mask = [rng.random() >= rho * 0.5 for _ in range(4)]
    if mode == "burst" and rho > 0:
        b0 = rng.randrange(4)
        for k in range(min(L, 2)):
            boot_mask[(b0 + k) % 4] = False
    for k, st in enumerate((0, 3, 6, 9)):
        proj = aperture(W, n, st, 4, f"R{k}")
        if boot_mask[k]:
            ev = deliver(proj, WC)
            if ev is not None:
                s.receive(ev)
                boot_pids.append((f"R{k}", st, dict(proj.view)))
    boot_glued = {q: v[0] for q, v in s.asm.known.items()}

    probes = [(f"T{k}", st, aperture(W, n, st, 3, f"T{k}"))
              for k, st in enumerate(PROBE_STARTS)]
    schedule = list(range(len(probes)))
    if mode == "reorder":
        rng.shuffle(schedule)
    occluded = set()
    if mode == "drop" and rho > 0:
        occluded = {k for k in schedule if rng.random() < rho}
    if mode == "burst" and rho > 0:
        pos = rng.randrange(len(schedule))
        for k in range(L):
            occluded.add(schedule[(pos + k) % len(schedule)])
    boot_known_pos = {q for _, st, _ in boot_pids for q in range(st, st + 4)}
    poison_glued = poison_glued_unguarded = poison_attempts = 0
    if attack:
        s.add_trust_anchor(WCx.pubkey)
    for k in schedule:
        tag, st, proj = probes[k]
        if k in occluded:
            if attack:
                fv = {q: v ^ 1 for q, v in proj.view.items()}
                pois = Projection(f"X{k}", frozenset(proj.anchor), fv,
                                  origin="world")
                ev = deliver(pois, WCx)
                if ev is not None:
                    pre = {q: s.asm.known.get(q, (None,))[0]
                           for q in pois.anchor}
                    d = s.receive(ev)
                    poison_attempts += 1
                    if DEC(d) == GLUED:
                        guarded = [q for q in pois.anchor
                                   if pre[q] is not None]
                        if guarded:
                            poison_glued += 1
                        else:
                            poison_glued_unguarded += 1
            continue
        ev = deliver(proj, WC)
        if ev is not None:
            s.receive(ev)
    acc_after_attack = acc_known_of(s, W) if attack else None
    if attack:
        for k in sorted(occluded):
            tag, st, proj = probes[k]
            for rd in range(3):
                for dstart in (0, 1, 2):
                    pr2 = aperture(W, n, (st + dstart) % n, 3,
                                   f"V{k}_{rd}_{dstart}")
                    ev = deliver(pr2, WC)
                    if ev is not None:
                        s.receive(ev)
    boot_vals = boot_glued
    overwritten = sum(1 for q, v in boot_vals.items()
                      if q in s.asm.known and s.asm.known[q][0] != v)
    boot_done_idx = getattr(s, "receive_count", 0)
    switches_after_boot = [e for e in s.epoch_log
                           if e.get("switch")
                           and e.get("idx", 0) >= boot_done_idx]
    switched = bool(switches_after_boot)
    demotions = len(getattr(s, "demotion_log", []))
    # trace classification: an overwritten boot value is WITH-TRACE if
    # a switch or a demotion accompanies it; silent otherwise (Q1/Q2)
    with_trace = overwritten if (switched or demotions) else 0
    silent = overwritten if not (switched or demotions) else 0
    law_acc, n_res = law_bit_accuracy(s, style)
    statuses = [DEC(d) for d in s.log if isinstance(d, dict)
                and "status" in d]
    return {
        "law_learned": len(s.asm.grammar.e_hat) == P,
        "law_acc": law_acc if law_acc is not None else 0.0,
        "known_acc": acc_known_of(s, W) or 0.0,
        "known_acc_after_attack": acc_after_attack,
        "boot_overwrite": overwritten,
        "boot_overwrite_silent": silent,
        "boot_overwrite_with_trace": with_trace,
        "switched_after_boot": switched,
        "demotions": demotions,
        "glued_true": statuses.count(GLUED),
        "parked_true": statuses.count(PARKED),
        "rejected_true": statuses.count("CONTRADICTION"),
        "refusals": refusal_count(s),
        "poison_attempts": poison_attempts,
        "poison_glued_overwrite": poison_glued if attack else 0,
        "poison_glued_unguarded": poison_glued_unguarded if attack else 0,
    }


def run_family(name, mode, rhos, trials, attack=False, factory=f_m2v):
    cells = {}
    for rho in rhos:
        agg = {"trials": trials, "law_learned": 0, "law_acc": [],
               "known_acc": [], "boot_overwrite": 0, "silent": 0,
               "with_trace": 0, "switched": 0, "demotions": 0,
               "glued": 0, "parked": 0, "rejected": 0, "refusals": 0,
               "poison_attempts": 0, "poison_glued": 0,
               "poison_unguarded": 0, "acc_after": []}
        for t in range(trials):
            seed = zlib.crc32(f"{name}|{rho}|{t}".encode())
            rng = random.Random(seed)
            r = po_trial(rng, mode, rho=rho, L=2, attack=attack,
                         factory=factory)
            agg["law_learned"] += int(r["law_learned"])
            agg["law_acc"].append(r["law_acc"])
            agg["known_acc"].append(r["known_acc"])
            agg["boot_overwrite"] += r["boot_overwrite"]
            agg["silent"] += r["boot_overwrite_silent"]
            agg["with_trace"] += r["boot_overwrite_with_trace"]
            agg["switched"] += int(r["switched_after_boot"])
            agg["demotions"] += r["demotions"]
            agg["glued"] += r["glued_true"]
            agg["parked"] += r["parked_true"]
            agg["rejected"] += r["rejected_true"]
            agg["refusals"] += r["refusals"]
            agg["poison_attempts"] += r["poison_attempts"]
            agg["poison_glued"] += r["poison_glued_overwrite"]
            agg["poison_unguarded"] += r["poison_glued_unguarded"]
            if r.get("known_acc_after_attack") is not None:
                agg["acc_after"].append(r["known_acc_after_attack"])
        n_ = agg["trials"]
        cell = {
            "trials": n_,
            "law_learned_rate": round(agg["law_learned"] / n_, 3),
            "law_acc_mean": round(sum(agg["law_acc"]) / n_, 3),
            "known_acc_mean": round(sum(agg["known_acc"]) / n_, 3),
            "acc_after_attack_mean": round(sum(agg["acc_after"]) /
                                           max(1, len(agg["acc_after"])), 3),
            "boot_overwrite_total": agg["boot_overwrite"],
            "SILENT_overwrite_total": agg["silent"],
            "with_trace_overwrite_total": agg["with_trace"],
            "switched_trials": agg["switched"],
            "demotions_total": agg["demotions"],
            "glued_true_total": agg["glued"],
            "parked_true_total": agg["parked"],
            "rejected_true_total": agg["rejected"],
            "refusals_total": agg["refusals"],
            "poison_attempts": agg["poison_attempts"],
            "poison_glued_overwrite_total": agg["poison_glued"],
            "poison_glued_unguarded_total": agg["poison_unguarded"],
        }
        cells[f"rho={rho}"] = cell
        p(f"  [{name} rho={rho}{' ATK' if attack else ''}] "
          + json.dumps(cell))
    return cells


# ------------------------------------------------------------------
# D-3 price probe: single channel vs a TENTATIVE value
# ------------------------------------------------------------------
def d3_price_probe():
    """D-3: can a SINGLE attacker channel reach the demotion price
    against a TENTATIVE TRUE value? Phases (all oracle-free):
      1. bootstrap on epoch A;
      2. legitimate epoch change to B (3 law-complete parks -> relearn)
         -> the imported B-values are TENTATIVE and TRUE (ref = W_B);
      3. the attacker (one channel) sends 3 distinct-anchor law-clean
         window flips, each covering the same tentative position q0;
      4. withdrawal: true B-stream re-covers; acc measured.
    Outcome classes (both pre-declared): no_demotion |
    demotion_with_trace. The class is REPORTED as the measured price."""
    rng = random.Random(777)
    n, P = 16, 4
    styleA = make_style(rng, P)
    wA = whole_from_style(styleA, n, v0=1)
    W_A = realized_ring(wA, n, styleA, rng, 0.0)
    residues = list(range(P))
    rng.shuffle(residues)
    styleB = tuple(styleA[r] ^ 1 if r == residues[0] else styleA[r]
                   for r in range(P))
    wB = whole_from_style(styleB, n, v0=1)
    W_B = realized_ring(wB, n, styleB, rng, 0.0)
    WC = LamportChannel("D3w")
    WCx = LamportChannel("D3x")
    s = f_m2v(n, P, "D3", WC, W_B)
    s.add_trust_anchor(WCx.pubkey)
    for k, st in enumerate((0, 3, 6, 9)):
        proj = aperture(W_A, n, st, 4, f"R{k}")
        ev, _, _ = deliver_signed(s, proj, WC, rng, retries=2)
        if ev is not None:
            s.receive(ev)
    # legit epoch change: B-windows park (clash with A-glued) until the
    # law-complete challenge re-learns; imported values = TRUE W_B
    for k in range(6):
        proj = aperture(W_B, n, (2 * k) % n, 4, f"B{k}")
        ev, _, _ = deliver_signed(s, proj, WC, rng, retries=2)
        if ev is not None:
            s.receive(ev)
        if any(e.get("switch") for e in s.epoch_log):
            break
    switched = any(e.get("switch") for e in s.epoch_log)
    tentative_true = sorted(q for q in s.tentative
                            if q in s.asm.known
                            and s.asm.known[q][0] == W_B[q])
    if not tentative_true:
        return {"switched": switched, "tentative_true_positions": 0,
                "outcome": "no_tentative_true_values_to_attack"}
    q0 = tentative_true[len(tentative_true) // 2]   # an interior one
    demoted = False
    strikes = []
    for j, dstart in enumerate((0, -1, -2)):        # distinct anchors
        st = (q0 + dstart) % n
        proj = aperture(W_B, n, st, 3, f"SD{j}")
        fv = {q: v ^ 1 for q, v in proj.view.items()}   # law-clean flip
        pois = Projection(f"SD{j}", frozenset(proj.anchor), fv,
                          origin="world")
        ev = recorded_event(s, pois, True, "world", world_channel=WCx,
                            sign=True, record=False)
        if s.contact_allows_law(ev):
            prev, proof = s.record(pois)
            ev.prev_tip, ev.proof = prev, proof
            d = s.receive(ev)
            strikes.append({"j": j, "status": DEC(d),
                            "demotions": len(s.demotion_log)})
            if any(dm["pos"] == q0 for dm in s.demotion_log):
                demoted = True
                break
    for rd in range(3):
        for dstart in (0, 1, 2):
            pr2 = aperture(W_B, n, (q0 + dstart) % n, 3, f"RC{rd}_{dstart}")
            ev, _, _ = deliver_signed(s, pr2, WC, rng, retries=2)
            if ev is not None:
                s.receive(ev)
    acc = acc_known_of(s, W_B)
    return {"switched": switched,
            "tentative_true_positions": len(tentative_true),
            "q0": q0,
            "strikes": strikes,
            "demotion_fired": demoted,
            "outcome": ("demotion_with_trace" if demoted
                        else "no_demotion"),
            "acc_after_withdrawal": acc,
            "demotion_log": s.demotion_log}


def main():
    md5_before = {f: md5_of(f"/home/z/my-project/scripts/{f}")
                  for f in CORE_FILES}
    results = {"round": "14-PO",
               "name": "M2-value channel: tentative import + "
                       "diversity-priced demotion",
               "pre_registered": "Q1-Q5 + D-3 in module header; fixed "
                                 "before the run"}
    p("=" * 68)
    p("ROUND 14-PO: M2-value channel (tentative import + demotion)")
    p("=" * 68)

    # ---- Q5 structural no-oracle ------------------------------------
    probe = f_m2v(16, 4, "Q5", LamportChannel("Q5"))
    q5 = not hasattr(probe, "referee_ring")
    p(f"step Q5: no-oracle structural check: {'PASS' if q5 else 'FAIL'}")

    # ---- step 1: attack-free regression (Q4a) -----------------------
    p("step 1: attack-free cells (must equal r13-PO attack-free)")
    benign_cells = {}
    # seed-name discipline: r13 generated its cells under the SHORT
    # family names ("PO1"/"PO4"/"PO2") - the crc32 seeds must match
    # them exactly for the regression comparison to be meaningful.
    benign_cells["PO1_random_drop"] = run_family(
        "PO1", "drop", [0.0, 0.2], trials=10, attack=False)
    r13 = json.load(open("/home/z/my-project/download/r13_po_results.json"))
    q4_parts = []
    for name, cells in benign_cells.items():
        for rho, c in cells.items():
            ref = r13.get(name, {}).get(rho)
            if ref is None:
                continue
            for k in ("law_learned_rate", "glued_true_total",
                      "parked_true_total", "rejected_true_total",
                      "SILENT_overwrite_total"):
                if c[k] != ref[k]:
                    q4_parts.append((name, rho, k, ref[k], c[k]))
    p(f"  Q4a deltas vs r13: {q4_parts if q4_parts else 'NONE'}")
    results["benign_regression"] = benign_cells
    results["q4a_deltas"] = q4_parts

    # ---- step 2: attack families (Q1-Q3) ----------------------------
    p("step 2: attack families under M2V")
    atk = {}
    atk["PO4_gap_attack"] = run_family("PO4", "drop",
                                       [0.1, 0.2, 0.3], trials=16,
                                       attack=True)
    atk["PO2_burst"] = run_family("PO2", "burst", [0.3],
                                  trials=16, attack=True)
    results["attack_families"] = atk

    r13_po4_02 = r13["PO4_gap_attack"]["rho=0.2"]
    p(f"  r13 reference PO4 rho=0.2: known_acc="
      f"{r13_po4_02['known_acc_mean']} "
      f"acc_after={r13_po4_02['acc_after_attack_mean']} "
      f"switched={r13_po4_02['switched_trials']}")
    c02 = atk["PO4_gap_attack"]["rho=0.2"]

    # ---- step 3: A/B on the P3-failing cell (Q4b) -------------------
    p("step 3: A/B PO4 rho=0.2: frozen v3 vs M2V (same crc32 seeds)")
    ab_v3 = run_family("PO4", "drop", [0.2], trials=16,
                       attack=True, factory=f_v3)
    results["AB_po4_rho02"] = {"v3": ab_v3["rho=0.2"], "m2v": c02}
    p(f"  v3 : known_acc={ab_v3['rho=0.2']['known_acc_mean']} "
      f"acc_after={ab_v3['rho=0.2']['acc_after_attack_mean']} "
      f"switched={ab_v3['rho=0.2']['switched_trials']}")
    p(f"  M2V: known_acc={c02['known_acc_mean']} "
      f"acc_after={c02['acc_after_attack_mean']} "
      f"switched={c02['switched_trials']} "
      f"demotions={c02['demotions_total']}")

    # ---- step 4: D-3 price probe ------------------------------------
    p("step 4: D-3 single-attacker demotion price probe")
    d3 = d3_price_probe()
    p("  " + json.dumps({k: v for k, v in d3.items()
                         if k != "demotion_log"}))
    results["D3_price_probe"] = d3

    # ---- decision gate ------------------------------------------------
    silent_total = sum(c["SILENT_overwrite_total"]
                       for fam in list(results["attack_families"].values())
                       for c in fam.values())
    poison_ov_total = sum(c["poison_glued_overwrite_total"]
                          for fam in list(results["attack_families"].values())
                          for c in fam.values())
    gate = {
        "Q5_no_oracle": q5,
        "Q4a_benign_identical": len(q4_parts) == 0,
        "Q1_zero_silent_everywhere": silent_total == 0,
        "Q1_zero_poison_overwrite": poison_ov_total == 0,
        "Q3_po4_rho02_recovery": (c02["known_acc_mean"] >= 0.95
                                  and c02["acc_after_attack_mean"] == 1.0),
        "Q4b_m2v_switches_le_v3": (c02["switched_trials"]
                                   <= ab_v3["rho=0.2"]["switched_trials"]),
        "D3_price_declared": d3["outcome"] in ("no_demotion",
                                               "demotion_with_trace"),
    }
    results["GATES"] = gate
    if all(gate.values()):
        results["verdict"] = ("PO-RECOVERY = RESTORED* (M2-value channel: "
                              "tentative import + diversity-priced "
                              "demotion; closure intact)")
    else:
        results["verdict"] = ("PO-RECOVERY = PARTIAL/FAIL - see GATES "
                              "(honest stdout)")
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
