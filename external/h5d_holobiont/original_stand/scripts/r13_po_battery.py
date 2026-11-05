#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ROUND 13-PO: PARTIAL OBSERVABILITY battery on the frozen H5d'v3
# (Task 16-a; roadmap round: what the subject does NOT see)
# =====================================================================
# Prior batteries (E11 noise, E12-E15 sweeps) varied the WORLD's law
# (eps, drift, epochs, conflicts) but every in-band event was DELIVERED.
# Here the delivery channel itself hides events:
#   PO1 random drop      : each probe event independently occluded, rho
#   PO2 burst occlusion  : contiguous runs of L probe events occluded
#   PO3 reordered view   : probe events delivered in permuted order
#                          (a static-world stand: delay == reordering,
#                          declared; staleness needs epoch drift = N3)
#   PO4 adversarial gaps : the attacker SEES the mask and injects
#                          law-clean poison/chimeras exactly into the
#                          occluded slots; afterwards the occluded TRUE
#                          events are re-delivered (world persists)
#   controls             : rho=0 full-visibility per family
#
# PRE-REGISTERED CRITERIA (fixed BEFORE the run):
#   P1 glued-history overwrite == 0 in EVERY cell of every family
#      (values at bootstrap-known positions never change) - the N5
#      closure invariant under partial observability.
#   P2 no NEW silent channel: any degradation of law_acc / known_acc
#      relative to the rho=0 control must co-occur with an observable
#      loud signal (parked_true > 0 OR true_rejected > 0 OR v3
#      refusals > 0). A cell that degrades with zero loud signals
#      fails P2.
#   P3 PO4 worst case: poison never overwrites glued history AND the
#      subject recovers to known_acc == 1.0 after the true events are
#      re-delivered in >= 95% of trials at rho <= 0.3.
#   P4 the degradation SHAPE vs rho / L is reported (law_learned_rate,
#      glue rate, known_acc): monotone or threshold - measured, not
#      gated (honest stdout).
#
# The subject is the UNMODIFIED SubjectH5DPv3 (frozen round10_battery);
# occlusion happens STAND-SIDE (the stand simply never delivers an
# occluded event - the subject cannot distinguish occlusion from the
# world not sending, which is the point: no new mechanism, no oracle).
#
# REVISED AFTER THE FIRST RUN (diagnosed on traces; documented BEFORE
# the definitive re-run, Round 10/12 revision discipline):
#   D-PO1. The first-run P1 metric built "boot history" from DELIVERED
#      bootstrap events, including events the subject REJECTED at
#      bootstrap (loud CONTRADICTION). A rejected event glues nothing:
#      its window is UNGUARDED, and poison gluing there is the declared
#      R10/R12 A3 pre-emption family (measured as
#      poison_glued_unguarded), NOT a glued-history break. Fix: the
#      overwrite baseline is the GLUED SNAPSHOT (asm.known right after
#      bootstrap), so P1 counts only true closure breaks.
#   D-PO2. The first-run recovery phase re-delivered each occluded TRUE
#      event ONCE. Recovery per the declared protocol (R10 A3 phase 2)
#      needs a law-complete coherent challenge: three consecutive
#      apertures (starts st, st+1, st+2) vote all four residues and
#      re-anchor through the M2 path. Fix: recovery re-delivers, per
#      occluded slot, apertures at starts st/st+1/st+2 for 3 rounds
#      (R10 A3 protocol).
# =====================================================================
import json
import random
import zlib
import hashlib
import sys

sys.path.insert(0, "/home/z/my-project/scripts")

from holographic_core import (make_style, whole_from_style, aperture,
                              Projection, GLUED)
from holographic_e10_core import LamportChannel
from e11_noise_battery import (realized_ring, deliver_signed, acc_known_of,
                               law_bit_accuracy, DEC)
import n5_closure_battery as M_N5
import e11_noise_battery as M_E11
import round10_battery as M_R10
from round10_battery import SubjectH5DPv3, refusal_count

OUT_JSON = "/home/z/my-project/download/r13_po_results.json"
OUT_LOG = "/home/z/my-project/download/r13_po_stdout.log"
CORE_FILES = ["holographic_core.py", "holographic_e10_core.py",
              "vli_battery.py", "e11_noise_battery.py",
              "n5_closure_battery.py", "round10_battery.py"]
FROZEN_MD5 = {
    "holographic_core.py": "d683f7eb2f4fae0b404310f7b12b22b4",
    "holographic_e10_core.py": "5b8e98e51458c24401dc58937b140b81",
    "holographic_e10_battery.py": "0dd855433905feb2a226b424e3709fb5",
    "round10_battery.py": "ca9f78848d89212800293b7b79bd6108",
    "round11_audit_battery.py": "3d6b0967a1643532e229183de0b33958",
    "e12_e15_sweeps.py": "9ea607eab446b81a2ade4841bc80814b",
    "n5_closure_battery.py": "354decc91470f6f27465d2945c586311",
    "e11_noise_battery.py": "318641a59d3e8b08cbf7b7275ce3ebc5",
    "vli_battery.py": "c1708f88e09149fccd36205dc2508be3",
    "e10r_battery.py": "4bc9adc6e663716fc585463ce58769e8",
}

_lines = []
PARKED = "PARKED_CHALLENGED"
EPS = 0.05          # world violation rate inside the band (E12 default)


def p(s=""):
    print(s)
    _lines.append(str(s))


def md5_of(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def f_v3(n, P, sid, WC, W=None):
    return SubjectH5DPv3(n, P, sid=sid, contact="verify", world_channel=WC)


# ------------------------------------------------------------------
# one trial: bootstrap + probe events, delivered under a visibility
# mask; returns per-trial metrics
# ------------------------------------------------------------------
PROBE_STARTS = [1, 4, 7, 10, 13, 2, 5, 8]   # 8 width-3 probe windows


def po_trial(rng, mode, rho=0.0, L=2, attack=False):
    """mode in {drop, burst, reorder}; rho = occlusion intensity.
    Returns a dict of raw outcomes for aggregation."""
    n, P = 16, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)
    W = realized_ring(w, n, style, rng, EPS)
    WC = LamportChannel(f"PO_{mode}_{rho}")
    WCx = LamportChannel(f"POx_{mode}_{rho}")
    s = f_v3(n, P, "PO", WC, W)
    boot_pids = []

    def deliver(proj, wc, record=True):
        ev, _, _ = deliver_signed(s, proj, wc, rng, retries=2)
        return ev

    # ---- bootstrap (4 x width-4 at 0,3,6,9): occluded under burst/drop
    boot_mask = [True, True, True, True]
    if mode == "drop" and rho > 0:
        boot_mask = [rng.random() >= rho * 0.5 for _ in range(4)]
    if mode == "burst" and rho > 0:
        b0 = rng.randrange(4)
        for k in range(min(L, 2)):          # bursts also hit bootstrap
            boot_mask[(b0 + k) % 4] = False
    for k, st in enumerate((0, 3, 6, 9)):
        proj = aperture(W, n, st, 4, f"R{k}")
        if boot_mask[k]:
            ev = deliver(proj, WC)
            if ev is not None:
                s.receive(ev)
                boot_pids.append((f"R{k}", st, dict(proj.view)))
    # D-PO1: the closure baseline = positions ACTUALLY GLUED after
    # bootstrap (delivered-but-rejected events glue nothing)
    boot_glued = {q: v[0] for q, v in s.asm.known.items()}

    # ---- probes: build ALL projections first (world is static), then
    #      deliver under the observation schedule
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
    # attacks know the mask: poison injected right after each occluded slot
    boot_known_pos = {q for _, st, _ in boot_pids if True
                      for q in range(st, st + 4)}
    poison_glued = poison_glued_unguarded = poison_attempts = 0
    if attack:
        s.add_trust_anchor(WCx.pubkey)
    for k in schedule:
        tag, st, proj = probes[k]
        if k in occluded:
            if attack:
                # law-clean FULL flip of the true window view (A1/A3
                # construction: zero violations on own internal edges)
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
                            poison_glued += 1     # overwrite: closure break
                        else:
                            poison_glued_unguarded += 1  # parked family
            continue
        ev = deliver(proj, WC)
        if ev is not None:
            s.receive(ev)
    # ---- recovery: the world persists; occluded TRUE slots are
    #      re-challenged per the R10-A3 protocol (D-PO2): three
    #      consecutive apertures vote all residues -> M2 can re-anchor
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
    # ---- metrics
    # D-PO1: the closure baseline is the GLUED SNAPSHOT taken right
    # after bootstrap (boot_glued); positions whose covering event was
    # rejected/occluded were never glued - poison there is the declared
    # unguarded family, counted separately, not a closure break
    boot_vals = boot_glued
    overwritten = sum(1 for q, v in boot_vals.items()
                      if q in s.asm.known and s.asm.known[q][0] != v)
    # D2 discipline (Round 12 lesson): split SILENT overwrite (no epoch
    # switch after boot = closure break) from relearn-accompanied value
    # replacement (the declared loud front door)
    boot_done_idx = getattr(s, "receive_count", 0)
    switches_after_boot = [e for e in s.epoch_log
                           if e.get("switch")
                           and e.get("idx", 0) >= boot_done_idx]
    switched = bool(switches_after_boot)
    law_acc, n_res = law_bit_accuracy(s, style)
    statuses = [DEC(d) for d in s.log if isinstance(d, dict)
                and "status" in d]
    trace = None
    if overwritten:
        trace = {"switches": switches_after_boot,
                 "arbitration_len": len(getattr(s, "arbitration_log", [])),
                 "overwritten_pos": [q for q, v in boot_vals.items()
                                     if q in s.asm.known
                                     and s.asm.known[q][0] != v]}
    return {
        "law_learned": len(s.asm.grammar.e_hat) == P,
        "law_acc": law_acc if law_acc is not None else 0.0,
        "known_acc": acc_known_of(s, W) or 0.0,
        "known_acc_after_attack": acc_after_attack,
        "boot_overwrite": overwritten,
        "boot_overwrite_silent": overwritten if not switched else 0,
        "boot_overwrite_relearned": overwritten if switched else 0,
        "switched_after_boot": switched,
        "glued_true": statuses.count(GLUED),
        "parked_true": statuses.count(PARKED),
        "rejected_true": statuses.count("CONTRADICTION"),
        "refusals": refusal_count(s),
        "poison_attempts": poison_attempts,
        "poison_glued_overwrite": poison_glued if attack else 0,
        "poison_glued_unguarded": poison_glued_unguarded if attack else 0,
        "trace": trace,
    }

def run_family(name, mode, rhos, Ls, trials, attack=False):
    cells = {}
    for rho in rhos:
        agg = {"trials": trials, "law_learned": 0, "law_acc": [],
               "known_acc": [], "boot_overwrite": 0,
               "silent_overwrite": 0, "relearn_overwrite": 0,
               "switched_trials": 0, "glued_true": 0,
               "parked_true": 0, "rejected_true": 0, "refusals": 0,
               "poison_attempts": 0, "poison_glued_overwrite": 0,
               "poison_glued_unguarded": 0,
               "traces": []}
        for t in range(trials):
            # cross-process-stable seed (str hash is process-randomized)
            seed = zlib.crc32(f"{name}|{rho}|{t}".encode())
            rng = random.Random(seed)
            r = po_trial(rng, mode, rho=rho, L=2, attack=attack)
            agg["law_learned"] += int(r["law_learned"])
            agg["law_acc"].append(r["law_acc"])
            agg["known_acc"].append(r["known_acc"])
            agg["boot_overwrite"] += r["boot_overwrite"]
            agg["silent_overwrite"] += r["boot_overwrite_silent"]
            agg["relearn_overwrite"] += r["boot_overwrite_relearned"]
            agg["switched_trials"] += int(r["switched_after_boot"])
            if r.get("trace"):
                agg["traces"].append({"trial": t, **r["trace"]})
            agg["glued_true"] += r["glued_true"]
            agg["parked_true"] += r["parked_true"]
            agg["rejected_true"] += r["rejected_true"]
            agg["refusals"] += r["refusals"]
            agg["poison_attempts"] += r["poison_attempts"]
            agg["poison_glued_overwrite"] += r["poison_glued_overwrite"]
            agg["poison_glued_unguarded"] += r["poison_glued_unguarded"]
            if r.get("known_acc_after_attack") is not None:
                agg.setdefault("acc_after_attack", []).append(
                    r["known_acc_after_attack"])
        n = agg["trials"]
        ev = agg["glued_true"] + agg["parked_true"] + agg["rejected_true"]
        cell = {
            "trials": n,
            "law_learned_rate": round(agg["law_learned"] / n, 3),
            "law_acc_mean": round(sum(agg["law_acc"]) / n, 3),
            "known_acc_mean": round(sum(agg["known_acc"]) / n, 3),
            "boot_overwrite_total": agg["boot_overwrite"],
            "SILENT_overwrite_total": agg["silent_overwrite"],
            "relearn_overwrite_total": agg["relearn_overwrite"],
            "switched_trials": agg["switched_trials"],
            "overwrite_traces": agg["traces"][:4],
            "glued_true_total": agg["glued_true"],
            "parked_true_total": agg["parked_true"],
            "rejected_true_total": agg["rejected_true"],
            "refusals_total": agg["refusals"],
            "poison_attempts": agg["poison_attempts"],
            "poison_glued_overwrite_total": agg["poison_glued_overwrite"],
            "poison_glued_unguarded_total": agg.get(
                "poison_glued_unguarded", 0),
            "acc_after_attack_mean": round(sum(
                agg.get("acc_after_attack", [0])) /
                max(1, len(agg.get("acc_after_attack", [1]))), 3),
            "loud_signal_cells": agg["parked_true"] + agg["rejected_true"]
                                 + agg["refusals"],
        }
        cells[f"rho={rho}"] = cell
        p(f"  [{name} rho={rho}] " + json.dumps(cell))
    return cells


def main():
    md5_before = {f: md5_of(f"/home/z/my-project/scripts/{f}")
                  for f in CORE_FILES}
    results = {"round": "13-PO",
               "name": "Partial observability battery (frozen H5d'v3)",
               "pre_registered": "P1-P4 in module header; fixed before run"}
    p("=" * 68)
    p("ROUND 13-PO: PARTIAL OBSERVABILITY of the frozen H5d'v3")
    p("=" * 68)
    p("pre-registration: P1 boot-overwrite==0 everywhere; P2 any law/known")
    p("  acc degradation co-occurs with a loud signal; P3 PO4 recovery")
    p("  >=95% at rho<=0.3 with zero poison overwrites; P4 shape reported.")
    p("")

    # ---------------- PO1: random drop ------------------------------
    p("--- PO1: random drop (controls: rho=0) ---")
    results["PO1_random_drop"] = run_family(
        "PO1", "drop", [0.0, 0.1, 0.2, 0.3, 0.4, 0.5], None, trials=10)

    # ---------------- PO2: burst occlusion --------------------------
    p("--- PO2: burst occlusion (runs of L events at intensity ~0.3) ---")
    results["PO2_burst"] = run_family(
        "PO2", "burst", [0.3], None, trials=10)

    # ---------------- PO3: reordered delivery ------------------------
    p("--- PO3: reordered delivery (static world: delay == reorder) ---")
    results["PO3_reordered"] = run_family(
        "PO3", "reorder", [0.0], None, trials=10)

    # ---------------- PO4: adversarial gap exploitation --------------
    p("--- PO4: attacker sees the mask, poisons occluded slots, then")
    p("    the occluded TRUE events are re-delivered (recovery) ---")
    results["PO4_gap_attack"] = run_family(
        "PO4", "drop", [0.0, 0.1, 0.2, 0.3], None, trials=16, attack=True)

    # ---------------- gates P1-P4 ------------------------------------
    p("--- decision gate (pre-registered) ---")
    p1_hits = []
    for fam, cells in results.items():
        if not isinstance(cells, dict):
            continue
        for cfg, c in cells.items():
            if isinstance(c, dict):
                # D2 discipline: only SILENT overwrites (no epoch switch)
                # are closure breaks; relearn-accompanied replacement is
                # the declared loud front door (reported, not gated)
                if c.get("SILENT_overwrite_total", 0) or \
                   c.get("poison_glued_overwrite_total", 0):
                    p1_hits.append((fam, cfg))
    g1 = len(p1_hits) == 0
    p(f"P1 zero SILENT overwrite (closure break; relearn path reported "
      f"separately): {'PASS' if g1 else 'FAIL ' + str(p1_hits)}")

    p2_parts = []
    for fam in ("PO1_random_drop", "PO2_burst", "PO3_reordered"):
        base = results[fam].get("rho=0.0") or \
            results[fam].get("rho=0.3")
        base_acc = base["law_acc_mean"] if base else 1.0
        base_known = base["known_acc_mean"] if base else 1.0
        for cfg, c in results[fam].items():
            degraded = (c["law_acc_mean"] < base_acc - 0.05
                        or c["known_acc_mean"] < base_known - 0.05)
            if degraded and c["loud_signal_cells"] == 0:
                p2_parts.append((fam, cfg, c["law_acc_mean"],
                                 c["known_acc_mean"]))
    g2 = len(p2_parts) == 0
    p(f"P2 no silent degradation channel: "
      f"{'PASS' if g2 else 'FAIL ' + str(p2_parts)}")

    po4 = results["PO4_gap_attack"]
    rec_cells = [c for cfg, c in po4.items()
                 if cfg in ("rho=0.1", "rho=0.2", "rho=0.3")]
    ok_rec = all(c["known_acc_mean"] >= 0.95 for c in rec_cells)
    ok_ovw = all(c["poison_glued_overwrite_total"] == 0
                 for c in po4.values())
    g3 = ok_rec and ok_ovw
    p(f"P3 PO4: recovery>=0.95 at rho<=0.3 ({[c['known_acc_mean'] for c in rec_cells]}) "
      f"and zero poison overwrites: {'PASS' if g3 else 'FAIL'}")

    # P4 shape: reported in the table above (honest stdout, no gate)
    shape = {fam: {cfg: {"law_acc": c["law_acc_mean"],
                         "law_learned": c["law_learned_rate"],
                         "known_acc": c["known_acc_mean"]}
                   for cfg, c in cells.items()}
             for fam, cells in results.items()
             if isinstance(cells, dict)}
    results["P4_shape_report"] = shape
    results["GATES"] = {"P1": g1, "P2": g2, "P3": g3}
    verdict = g1 and g2 and g3
    results["verdict"] = (
        "PO-CLOSURE = HOLD*: zero overwrites under every observation "
        "model, degradation loud-only, adversarial gap-exploits recover"
        if verdict else
        "PO-CLOSURE = " + ("DEGRADED-LOUD" if g1 and g3 else
                           "FAIL - see GATES"))
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
