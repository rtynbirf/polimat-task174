#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ROUND 14-AX: THE ANTHROPOLOGICAL AXIS - interest orientations,
# sacrifice, and the merit-authority trap.
# New-file variant; frozen files untouched.
# =====================================================================
# New circumstances fixed by the owner (session synthesis):
#   - the primary object is the WHOLE (holobiont) that keeps its
#     identity in contact with autonomous agents;
#   - agents differ in INTEREST ORIENTATION: toward self, toward
#     another agent, toward the whole - and a subject of the common
#     can act AGAINST its immediate benefit (sacrifice is part of the
#     model, not an anomaly);
#   - parasitism is NOT intent: a parasite can be legitimate,
#     authenticated, locally useful - it appropriates a function of
#     the whole. Therefore INTENT != OBSERVABLE, and any architecture
#     that converts observed "good behavior" (merit) into AUTHORITY
#     is a candidate parasite target.
#
# Operationalization in this battery (frozen H5d'v3 as the subject):
#   - orientation is a WORLD-side bookkeeping label on emitters; the
#     subject NEVER sees it (like `origin`, but asserted structurally);
#   - sacrifice = costly truthful behavior (redundant deliveries,
#     truth under temptation), counted battery-side;
#   - A5 (NEW adaptive attack) FAKE-ALTRUISM / MERIT-MINING: a
#     parasite first behaves whole-oriented (TRUE attested events -
#     truth is cheap while it does not strike), farming observable
#     devotion, then strikes;
#   - COUNTERFACTUAL SubjectMerit ("what a naive architect would
#     build"): devotion[pk] counted on attested GLUED events; a parked
#     challenge from an all-devoted buffer is PRESUMED complete and
#     needs only 1 event (merit fast-path) instead of E_MIN=3 +
#     law-completeness. We BUILD the trap to MEASURE it.
#
# PRE-REGISTERED GATES (fixed BEFORE the run):
#   X0  orientation blindness: (a) structural - the frozen subject has
#       no orientation/merit/referee attributes; (b) behavioural -
#       matched twins with DIFFERENT orientation bookkeeping produce
#       BIT-IDENTICAL trajectories (INTENT != OBSERVABLE, measured).
#   X1  HERO != OWNER: a devoted hero's single attested write that
#       flips glued values PARKS; no switch; boot-glued history
#       intact; law unchanged. Sacrifice buys nothing closure-related.
#   X2  single-source strikes on frozen v3: 1 strike -> no switch
#       (park); 3 consecutive law-clean strikes at distinct glued
#       anchors -> the DECLARED a2 family: loud attributed switch,
#       silent == 0, law restored, values re-covered on withdrawal.
#   X3  MERIT-AUTHORITY TRAP (the claim; gate passes when the VARIANT
#       FAILS): under SubjectMerit the same parasite wipes the
#       boot-glued history with ONE devoted strike (fast-path switch),
#       i.e. the devotion->authority coupling converts the 3-event
#       price into a 1-event price (measured discount factor).
#   X3b the seduction is real: a LEGITIMATE epoch change under the
#       merit variant switches on 2 devoted overlapping events (v3
#       refuses at 2, fires at 3 with a complete law) - merit buys
#       availability and sells closure, measured on both sides.
#   X4  sacrifice -> availability, not authority: under partial
#       observability with a gap-attacker, the whole-oriented
#       redundancy protocol recovers >= the self-oriented minimal one
#       (measured acc after recovery; closure counters 0 both).
#   X5  collusion at the semantics boundary: 3 DISTINCT attested
#       sources, 1 law-clean flip each (same total price as X2) -
#       outcome compared with X2; the completeness gate is
#       source-blind BY DESIGN (CONTACT != TRUTH): structural
#       completeness + loudness + attribution is all the subject has.
#   X6  no-oracle discipline on every subject used (no referee attr).
# Verdict: AX-ARCH = CONFIRMED iff X0, X1, X2-safe, X3 (trap fires),
# X3b, X4, X6 hold; X5 reported as the measured semantics boundary.
# =====================================================================
import json
import random
import hashlib
import sys
import zlib

sys.path.insert(0, "/home/z/my-project/scripts")

from e11_noise_battery import _pk_key, DEC
from n5_closure_battery import (SubjectH5DP, LamportChannel, Projection,
                                aperture, realized_ring, whole_from_style,
                                make_style, deliver_signed, recorded_event,
                                acc_known_of, law_bit_accuracy, GLUED,
                                EPS0)
from round10_battery import SubjectH5DPv3

OUT_JSON = "/home/z/my-project/download/r14_ax_results.json"
OUT_LOG = "/home/z/my-project/download/r14_ax_stdout.log"
CORE_FILES = ["holographic_core.py", "holographic_e10_core.py",
              "vli_battery.py", "e11_noise_battery.py",
              "n5_closure_battery.py", "round10_battery.py",
              "e12_e15_sweeps.py", "r13_g2_adaptive.py",
              "r13_po_battery.py", "round11_audit_battery.py"]

_lines = []
PARKED = "PARKED_CHALLENGED"


def p(s=""):
    print(s)
    _lines.append(str(s))


def md5_of(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def f_v3(n, P, sid, WC, W=None):
    return SubjectH5DPv3(n, P, sid=sid, contact="verify", world_channel=WC)


# =====================================================================
# COUNTERFACTUAL: the naive merit-authority architecture (the trap)
# =====================================================================
class SubjectMerit(SubjectH5DPv3):
    """Naive design: observable devotion (attested GLUED events per
    source) -> trusted-source fast path: an all-devoted parked buffer
    is PRESUMED law-complete and needs a single event. Built to be
    broken; every gate X3/X3b reads its failure as the result."""
    D_MIN = 2

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.devotion = {}
        self.ev_pk = {}

    def _buffer_all_devoted(self):
        if not self.epoch_buffer:
            return False
        return all(self.devotion.get(self.ev_pk.get(pid), 0) >= self.D_MIN
                   for pid, _ in self.epoch_buffer)

    def _challenge_complete(self, buf):
        if self._buffer_all_devoted():
            return True                    # naive presumption
        return super()._challenge_complete(buf)

    def receive(self, ev):
        pk = None
        if ev.lamport is not None:
            pk = _pk_key(ev.lamport[0])
            self.ev_pk.setdefault(ev.pid, pk)
        sw0 = sum(1 for e in self.epoch_log if e.get("switch"))
        d = super().receive(ev)
        sw1 = sum(1 for e in self.epoch_log if e.get("switch"))
        att = self.contact_allows_law(ev)
        if att and pk is not None and d.get("status") == GLUED:
            self.devotion[pk] = self.devotion.get(pk, 0) + 1
        if (d.get("status") == PARKED and sw1 == sw0
                and self._buffer_all_devoted()
                and self.fail_streak_att >= 1
                and self._mutually_coherent(self.epoch_buffer)):
            if self._relearn():
                d = dict(d)
                d["epoch_switched"] = True
                d["merit_fast_path"] = True
        return d


def f_merit(n, P, sid, WC, W=None):
    return SubjectMerit(n, P, sid=sid, contact="verify", world_channel=WC)


# ------------------------------------------------------------------
# shared helpers
# ------------------------------------------------------------------
def boot_stream(s, WC, rng, W, n, starts=(0, 3, 6, 9), width=4):
    glued = {}
    for k, st in enumerate(starts):
        proj = aperture(W, n, st, width, f"R{k}")
        ev, _, _ = deliver_signed(s, proj, WC, rng, retries=2)
        if ev is not None:
            s.receive(ev)
    return {q: v[0] for q, v in s.asm.known.items()}


def signed_from(s, proj, WC):
    ev = recorded_event(s, proj, True, "world", world_channel=WC,
                        sign=True, record=False)
    if s.contact_allows_law(ev):
        prev, proof = s.record(proj)
        ev.prev_tip, ev.proof = prev, proof
        return ev
    return None


def law_flip_proj(W, n, st, width, pid):
    proj = aperture(W, n, st, width, pid)
    fv = {q: v ^ 1 for q, v in proj.view.items()}
    return Projection(pid, frozenset(proj.anchor), fv, origin="world")


def history_intact(s, boot_vals):
    return all(q in s.asm.known and s.asm.known[q][0] == v
               for q, v in boot_vals.items())


def recover_stream(s, WC, rng, W, n, rounds=3, starts=(0, 1, 2)):
    deliveries = 0
    for rd in range(rounds):
        for ds in starts:
            proj = aperture(W, n, ds, 3, f"RC{rd}_{ds}")
            ev, _, _ = deliver_signed(s, proj, WC, rng, retries=2)
            if ev is not None:
                deliveries += 1
                s.receive(ev)
    return deliveries


# =====================================================================
# X0: twins + structural blindness
# =====================================================================
def x0_twins():
    n, P = 16, 4
    rng_build = random.Random(1001)
    style = make_style(rng_build, P)
    w = whole_from_style(style, n, v0=1)
    W = realized_ring(w, n, style, rng_build, 0.05)
    projs = [aperture(W, n, st, 4, f"R{k}")
             for k, st in enumerate((0, 3, 6, 9))]
    projs += [aperture(W, n, (2 + 2 * k) % n, 3, f"T{k}") for k in range(6)]
    # orientation bookkeeping: DIFFERENT for the twins, world-side only
    orient_A = {pr.pid: "WHOLE" for pr in projs}
    orient_B = {pr.pid: "PARASITE" for pr in projs}
    assert orient_A != orient_B

    def run_twin(tag):
        rng = random.Random(1002)
        WC = LamportChannel(f"TW{tag}")
        s = f_v3(n, P, f"TW{tag}", WC, W)
        statuses = []
        for pr in projs:
            ev, _, _ = deliver_signed(s, pr, WC, rng, retries=2)
            if ev is not None:
                statuses.append(DEC(s.receive(ev)))
        return {"known": {q: v[0] for q, v in s.asm.known.items()},
                "statuses": statuses,
                "epoch_log": [dict(e) for e in s.epoch_log],
                "law": s.asm.grammar.style_tuple()}

    a, b = run_twin("A"), run_twin("B")
    identical = (a["known"] == b["known"] and a["statuses"] == b["statuses"]
                 and a["epoch_log"] == b["epoch_log"]
                 and a["law"] == b["law"])
    # structural: no orientation/merit/referee surface on the subject
    probe = f_v3(16, 4, "STRUCT", LamportChannel("STRUCT"))
    bad_attrs = [k for k in vars(probe)
                 if any(t in k.lower() for t in
                        ("orient", "merit", "devot", "referee", "oracle"))]
    no_oracle = not hasattr(probe, "referee_ring")
    return {"twins_bit_identical": identical,
            "structural_blindness": not bad_attrs,
            "no_oracle": no_oracle,
            "bad_attrs": bad_attrs}


# =====================================================================
# X1: HERO != OWNER (frozen v3)
# =====================================================================
def x1_hero():
    rng = random.Random(2001)
    n, P = 16, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)
    W = realized_ring(w, n, style, rng, 0.0)
    WC = LamportChannel("X1w")
    WCh = LamportChannel("X1hero")
    s = f_v3(n, P, "X1", WC, W)
    s.add_trust_anchor(WCh.pubkey)
    boot_vals = boot_stream(s, WC, rng, W, n)
    sacrifices = 0
    # the hero pays for redundant true coverage (costly, no authority)
    for rd in range(2):
        for st in (1, 4, 7):
            proj = aperture(W, n, st, 3, f"H{rd}_{st}")
            ev, _, _ = deliver_signed(s, proj, WCh, rng, retries=2)
            if ev is not None:
                s.receive(ev)
                sacrifices += 1
    hero_accept = sum(1 for d in s.log if isinstance(d, dict)
                      and d.get("status") == GLUED)
    # then the hero's single attested write that flips glued values
    # (an honest mistake under drift, or a temptation strike - the
    # subject cannot and must not care which)
    proj = law_flip_proj(W, n, 9, 3, "HERO_FLIP")
    ev = signed_from(s, proj, WCh)
    d = s.receive(ev)
    st = DEC(d)
    sw = sum(1 for e in s.epoch_log if e.get("switch"))
    law_ok = all(b == style[r] for r, (b, _) in s.asm.grammar.e_hat.items())
    return {"sacrifices": sacrifices,
            "hero_flip_status": st,
            "switches": sw,
            "boot_history_intact": history_intact(s, boot_vals),
            "law_unchanged": law_ok,
            "hero_true_accept_seen": hero_accept}


# =====================================================================
# X2: single-source strikes on frozen v3 (1 strike vs 3-strike family)
# =====================================================================
def x2_single_source():
    out = {}
    for tag, n_strikes in (("one", 1), ("trio", 3)):
        rng = random.Random(3001)
        n, P = 16, 4
        style = make_style(rng, P)
        w = whole_from_style(style, n, v0=1)
        W = realized_ring(w, n, style, rng, 0.0)
        WC = LamportChannel(f"X2w_{tag}")
        WCx = LamportChannel(f"X2x_{tag}")
        s = f_v3(n, P, f"X2_{tag}", WC, W)
        s.add_trust_anchor(WCx.pubkey)
        boot_vals = boot_stream(s, WC, rng, W, n)
        # devotion farming: TRUE attested events from the attacker
        # channel (truth is cheap until the strike)
        for j, st in enumerate((13, 14)):
            proj = aperture(W, n, st, 3, f"FARM{j}")
            ev, _, _ = deliver_signed(s, proj, WCx, rng, retries=2)
            if ev is not None:
                s.receive(ev)
        for j in range(n_strikes):
            st = (9, 4, 0)[j]               # distinct glued anchors
            proj = law_flip_proj(W, n, st, 4, f"ATK{j}")
            ev = signed_from(s, proj, WCx)
            if ev is not None:
                d = s.receive(ev)
                p(f"  [X2/{tag}] strike {j}: {DEC(d)}")
        sw = [e for e in s.epoch_log if e.get("switch")]
        silent_ov = sum(1 for q, v in boot_vals.items()
                        if q in s.asm.known and s.asm.known[q][0] != v) \
            if not sw else 0
        # withdrawal: true stream re-covers
        rec_deliveries = recover_stream(s, WC, rng, W, n)
        acc = acc_known_of(s, W)
        law_restored = all(b == style[r]
                           for r, (b, _) in s.asm.grammar.e_hat.items())
        att_pids = [q for e in sw for q in e.get("buffer_pids", [])]
        out[tag] = {
            "strikes": n_strikes,
            "switched": len(sw),
            "silent_overwrite": silent_ov,
            "history_intact_before_recovery": history_intact(s, boot_vals),
            "acc_after_recovery": acc,
            "law_restored": law_restored,
            "recovery_deliveries": rec_deliveries,
            "buffer_pids": att_pids,
        }
    return out


# =====================================================================
# X3 / X3b: the merit-authority trap (counterfactual variant)
# =====================================================================
def x3_merit_trap():
    out = {}
    # --- X3: one devoted strike wipes the history under the variant
    rng = random.Random(3001)               # SAME seeds as X2/one
    n, P = 16, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)
    W = realized_ring(w, n, style, rng, 0.0)
    WC = LamportChannel("X3w")
    WCx = LamportChannel("X3x")
    s = f_merit(n, P, "X3", WC, W)
    s.add_trust_anchor(WCx.pubkey)
    boot_vals = boot_stream(s, WC, rng, W, n)
    for j, st in enumerate((13, 14)):       # farming (devotion -> 2)
        proj = aperture(W, n, st, 3, f"FARM{j}")
        ev, _, _ = deliver_signed(s, proj, WCx, rng, retries=2)
        if ev is not None:
            s.receive(ev)
    proj = law_flip_proj(W, n, 9, 4, "ATK0")
    ev = signed_from(s, proj, WCx)
    d = s.receive(ev) if ev is not None else {}
    sw = sum(1 for e in s.epoch_log if e.get("switch"))
    rec_deliveries = recover_stream(s, WC, rng, W, n)
    out["one_devoted_strike"] = {
        "status": DEC(d),
        "switches_after_one_strike": sw,
        "fast_path_fired": bool(d.get("merit_fast_path")),
        "boot_history_wiped": not history_intact(s, boot_vals),
        "acc_after_recovery": acc_known_of(s, W),
        "recovery_deliveries": rec_deliveries,
    }
    # --- X3b: the seduction - legit drift, 2 devoted overlapping events
    rng = random.Random(4001)
    styleA = make_style(rng, P)
    wA = whole_from_style(styleA, n, v0=1)
    W_A = realized_ring(wA, n, styleA, rng, 0.0)
    residues = list(range(P))
    rng.shuffle(residues)
    styleB = tuple(styleA[r] ^ 1 if r == residues[0] else styleA[r]
                   for r in range(P))
    wB = whole_from_style(styleB, n, v0=1)
    W_B = realized_ring(wB, n, styleB, rng, 0.0)
    WC2 = LamportChannel("X3b")
    sm = f_merit(n, P, "X3b", WC2, W_A)
    boot_stream(sm, WC2, rng, W_A, n)
    law_before = {r: b for r, (b, _) in sm.asm.grammar.e_hat.items()}
    b_events = 0
    for k in range(6):
        proj = aperture(W_B, n, (2 * k) % n, 4, f"B{k}")
        ev, _, _ = deliver_signed(sm, proj, WC2, rng, retries=2)
        if ev is None:
            continue
        d = sm.receive(ev)
        b_events += 1
        if any(e.get("switch") for e in sm.epoch_log):
            break
    # NOTE: after a merit fast-path switch the law can be PARTIAL or
    # even EMPTY - that IS the measured pathology (naive presumption
    # switches into an incomplete assembly). Snapshot what exists.
    law_after = {r: b for r, (b, _) in sm.asm.grammar.e_hat.items()}
    complete_after = len(sm.asm.grammar.e_hat) == P
    la, _ = law_bit_accuracy(sm, styleB)
    # frozen v3 control on the same seeds: how many B-events to switch?
    rng_c = random.Random(4001)
    _ = make_style(rng_c, P)
    _ = whole_from_style(styleA, n, v0=1)
    _ = realized_ring(wA, n, styleA, rng_c, 0.0)
    residues_c = list(range(P))
    rng_c.shuffle(residues_c)
    _ = tuple(styleA[r] ^ 1 if r == residues_c[0] else styleA[r]
              for r in range(P))
    _ = whole_from_style(styleB, n, v0=1)
    _ = realized_ring(wB, n, styleB, rng_c, 0.0)
    WC3 = LamportChannel("X3bc")
    sv = f_v3(n, P, "X3bc", WC3, W_A)
    boot_stream(sv, WC3, rng_c, W_A, n)
    b_events_v3 = 0
    fired_v3 = False
    for k in range(6):
        proj = aperture(W_B, n, (2 * k) % n, 4, f"B{k}")
        ev, _, _ = deliver_signed(sv, proj, WC3, rng_c, retries=2)
        if ev is None:
            continue
        b_events_v3 += 1
        sv.receive(ev)
        if any(e.get("switch") for e in sv.epoch_log):
            fired_v3 = True
            break
    out["legit_drift_seduction"] = {
        "merit_b_events_to_switch": b_events,
        "merit_switched": any(e.get("switch") for e in sm.epoch_log),
        "merit_law_complete_after": complete_after,
        "merit_law_acc_vs_B": la,
        "v3_b_events_to_switch": b_events_v3 if fired_v3 else None,
        "v3_fired_within_6": fired_v3,
        "law_changed_merit": law_after != law_before,
    }
    return out


# =====================================================================
# X4: sacrifice -> availability (whole-oriented redundancy vs minimal)
# =====================================================================
def x4_sacrifice():
    n, P = 16, 4
    out = {}
    for cond, rounds in (("whole", 3), ("self", 1)):
        accs, costs, parks = [], [], []
        silent_total = poison_ov = 0
        for t in range(12):
            rng = random.Random(zlib.crc32(f"S6|{cond}|{t}".encode()))
            style = make_style(rng, P)
            w = whole_from_style(style, n, v0=1)
            W = realized_ring(w, n, style, rng, 0.05)
            WC = LamportChannel(f"X4{cond}_{t}")
            WCx = LamportChannel(f"X4x{cond}_{t}")
            s = f_v3(n, P, f"X4_{cond}_{t}", WC, W)
            s.add_trust_anchor(WCx.pubkey)
            boot_vals = boot_stream(s, WC, rng, W, n)
            probes = [(k, st) for k, st in
                      enumerate((1, 4, 7, 10, 13, 2, 5, 8))]
            occluded = {k for k, _ in probes if rng.random() < 0.3}
            poison_ov_t = 0
            for k, st in probes:
                if k in occluded:
                    proj = law_flip_proj(W, n, st, 3, f"X{k}")
                    ev = signed_from(s, proj, WCx)
                    if ev is not None:
                        pre = {q: s.asm.known.get(q, (None,))[0]
                               for q in proj.anchor}
                        d = s.receive(ev)
                        if DEC(d) == GLUED and any(
                                pre[q] is not None for q in proj.anchor):
                            poison_ov_t += 1
                    continue
                ev, _, _ = deliver_signed(
                    s, aperture(W, n, st, 3, f"T{k}"), WC, rng, retries=2)
                if ev is not None:
                    s.receive(ev)
            poison_ov += poison_ov_t
            cost = 0
            for k, st in sorted(probes):
                if k not in occluded:
                    continue
                for rd in range(rounds):
                    for ds in (0, 1, 2):
                        if cond == "self" and (rd > 0 or ds > 0):
                            continue
                        pr2 = aperture(W, n, (st + ds) % n, 3,
                                       f"V{k}_{rd}_{ds}")
                        ev, _, _ = deliver_signed(s, pr2, WC, rng,
                                                  retries=2)
                        if ev is not None:
                            cost += 1
                            s.receive(ev)
            costs.append(cost)
            accs.append(acc_known_of(s, W) or 0.0)
            parks.append(sum(1 for d in s.log if isinstance(d, dict)
                             and d.get("status") == PARKED))
            silent_total += sum(
                1 for q, v in boot_vals.items()
                if q in s.asm.known and s.asm.known[q][0] != v)
        out[cond] = {
            "acc_after_recovery_mean": round(sum(accs) / len(accs), 3),
            "deliveries_mean": round(sum(costs) / len(costs), 2),
            "parks_total": sum(parks),
            "silent_overwrite_total": silent_total,
            "poison_glued_overwrite_total": poison_ov,
        }
        p(f"  [X4/{cond}] " + json.dumps(out[cond]))
    return out


# =====================================================================
# X5: collusion trio - three DISTINCT sources at the semantics boundary
# =====================================================================
def x5_collusion():
    rng = random.Random(3001)               # same base seeds as X2/trio
    n, P = 16, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)
    W = realized_ring(w, n, style, rng, 0.0)
    WC = LamportChannel("X5w")
    chans = [LamportChannel(f"X5c{j}") for j in range(3)]
    s = f_v3(n, P, "X5", WC, W)
    for c in chans:
        s.add_trust_anchor(c.pubkey)
    boot_vals = boot_stream(s, WC, rng, W, n)
    for j, (st, c) in enumerate(zip((9, 4, 0), chans)):
        proj = law_flip_proj(W, n, st, 4, f"COL{j}")
        ev = signed_from(s, proj, c)
        if ev is not None:
            p(f"  [X5] colluder {j}: {DEC(s.receive(ev))}")
    sw = [e for e in s.epoch_log if e.get("switch")]
    rec_deliveries = recover_stream(s, WC, rng, W, n)
    all_pids = [q for e in sw for q in e.get("buffer_pids", [])]
    distinct_sources = len({pid.rsplit("_", 1)[0] for pid in all_pids
                            if pid.startswith("COL")})
    return {
        "switched": len(sw),
        "silent_overwrite": 0 if sw else sum(
            1 for q, v in boot_vals.items()
            if q in s.asm.known and s.asm.known[q][0] != v),
        "attacker_caused_attributed": bool(all_pids)
        and all(pid.startswith("COL") for pid in all_pids),
        "distinct_colluder_pids": len({pid for pid in all_pids}),
        "acc_after_recovery": acc_known_of(s, W),
        "law_restored": all(b == style[r]
                            for r, (b, _) in s.asm.grammar.e_hat.items()),
        "recovery_deliveries": rec_deliveries,
    }


# =====================================================================
def main():
    md5_before = {f: md5_of(f"/home/z/my-project/scripts/{f}")
                  for f in CORE_FILES}
    results = {"round": "14-AX",
               "name": "anthropological axis: orientations, sacrifice, "
                       "merit-authority trap",
               "pre_registered": "X0-X6 in module header; fixed before "
                                 "the run"}
    p("=" * 68)
    p("ROUND 14-AX: the anthropological axis")
    p("=" * 68)

    p("step X0: orientation blindness (twins + structure)")
    x0 = x0_twins()
    p("  " + json.dumps(x0))
    results["X0_blindness"] = x0

    p("step X1: HERO != OWNER (frozen v3)")
    x1 = x1_hero()
    p("  " + json.dumps(x1))
    results["X1_hero"] = x1

    p("step X2: single-source strikes on frozen v3")
    x2 = x2_single_source()
    for k, v in x2.items():
        p(f"  [X2/{k}] " + json.dumps(v))
    results["X2_single_source"] = x2

    p("step X3: merit-authority trap (counterfactual variant)")
    x3 = x3_merit_trap()
    for k, v in x3.items():
        p(f"  [X3/{k}] " + json.dumps(v))
    results["X3_merit_trap"] = x3

    p("step X4: sacrifice -> availability")
    x4 = x4_sacrifice()
    results["X4_sacrifice"] = x4

    p("step X5: collusion trio (distinct sources)")
    x5 = x5_collusion()
    p("  " + json.dumps(x5))
    results["X5_collusion"] = x5

    # ---------------- decision gate (pre-registered) -----------------
    x2one, x2trio = x2["one"], x2["trio"]
    gate = {
        "X0_orientation_blindness": (x0["twins_bit_identical"]
                                     and x0["structural_blindness"]
                                     and x0["no_oracle"]),
        "X1_hero_no_bypass": (x1["hero_flip_status"] == PARKED
                              and x1["switches"] == 0
                              and x1["boot_history_intact"]
                              and x1["law_unchanged"]),
        "X2_one_strike_no_switch": (x2one["switched"] == 0
                                    and x2one["history_intact_before_recovery"]),
        "X2_trio_loud_attributed": (x2trio["switched"] >= 1
                                    and x2trio["silent_overwrite"] == 0
                                    and x2trio["law_restored"]
                                    and x2trio["acc_after_recovery"] == 1.0),
        "X3_merit_variant_wipes_history":
            x3["one_devoted_strike"]["switches_after_one_strike"] >= 1
            and x3["one_devoted_strike"]["boot_history_wiped"],
        "X3b_seduction_measured":
            x3["legit_drift_seduction"]["merit_switched"]
            and x3["legit_drift_seduction"]["merit_b_events_to_switch"]
            < (x3["legit_drift_seduction"]["v3_b_events_to_switch"] or 99),
        "X4_sacrifice_helps_availability":
            x4["whole"]["acc_after_recovery_mean"]
            >= x4["self"]["acc_after_recovery_mean"]
            and x4["whole"]["silent_overwrite_total"] == 0
            and x4["self"]["silent_overwrite_total"] == 0,
        "X6_no_oracle": x0["no_oracle"],
    }
    results["GATES"] = gate
    arch = all([gate["X0_orientation_blindness"], gate["X1_hero_no_bypass"],
                gate["X2_one_strike_no_switch"], gate["X2_trio_loud_attributed"],
                gate["X3_merit_variant_wipes_history"],
                gate["X3b_seduction_measured"],
                gate["X4_sacrifice_helps_availability"],
                gate["X6_no_oracle"]])
    results["verdict"] = ("AX-ARCH = CONFIRMED (intent-blindness necessary: "
                          "frozen v3 holds; the merit-authority variant "
                          "breaks - measured)" if arch
                          else "AX-ARCH = PARTIAL/FAIL - see GATES")
    p("--- decision gate (pre-registered) ---")
    for k, v in gate.items():
        p(f"  [{'PASS' if v else 'FAIL'}] {k}")
    p("")
    p("VERDICT: " + results["verdict"])
    p("SEMANTICS BOUNDARY (X5): structural completeness is source-blind; "
      "collusion price on v3 = 3 consecutive law-clean attested flips; "
      "the subject guarantees loudness + attribution + recoverability, "
      "not metaphysical truth (CONTACT != TRUTH).")

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
