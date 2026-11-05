#!/usr/bin/env python3
# =====================================================================
# ROUND 9' (N5-FIRST): closure attempts of the ATTESTED OVERWRITE CHANNEL
# =====================================================================
# Ordering corrected against the external auditor's roadmap (Rounds 9-12):
# the roadmap puts parameter sweeps (E12-E15) BEFORE N5 closure. Rejected:
# a sweep maps the operating region of a mechanism that N5 may force to
# change (the auditor's own lesson: each defect fix shifts metrics by
# 10-40%), so sweep-first is throwaway work. N5 carries the falsification
# power for the central covering-triple claim: if subject-side closure
# needs a 4th axis, minimality dies. N5 goes first; sweeps after the
# mechanism is final.
#
# Pre-registered candidates and predictions (fixed BEFORE the run):
#   X1  baseline        : reproduce E11/N5 exactly (overwrite .6, silent .333)
#   X2  H5b  ordering   : per-source monotonic seq numbers + replay rejection
#                         PREDICTION: no effect (both writes are in order;
#                         the channel is about WRITE AUTHORITY, not order)
#   X3  H5d  keeper     : first attested writer KEEPS a position; foreign
#                         attested writes park; takeover needs V_MIN
#                         coherent challenges
#                         PREDICTION: cross-source overwrite -> 0;
#                         single-attester channel REMAINS (same keeper)
#   X4  H5d' evidence   : ANY attested write that would flip glued values
#                         parks (PARKED_CHALLENGED) and counts into the M2
#                         epoch machinery; V_MIN coherent challenges promote
#                         (front-door re-anchoring). No new axis, no oracle.
#                         PREDICTION: overwrite -> 0, silent -> 0, true
#                         stream untouched (one-trajectory stand)
#   X4b attacker trio   : 3 coherent false events vs H5d'
#                         ORIGINAL PREDICTION: promotion/relearn fires
#                         (attacker reaches the epoch evidence bar).
#                         FIRST RUN REFUTED THE DESIGN, not the prediction:
#                         the front-door promotion accepted 3 identical
#                         copies at ONE anchor (defect D1). Fix: promotion
#                         removed; re-anchoring ONLY via the epoch path and
#                         ONLY for LAW-COMPLETE challenges (the buffered
#                         events must jointly vote all period residues,
#                         majority-agreeing per residue). REVISED
#                         PREDICTION: the trio parks forever (2 residues
#                         voted < 4) -> overwrite 0, silent 0.
#   X5  single attester : attacker holds THE trusted channel (WC1)
#                         PREDICTION: baseline still overwrites (the channel
#                         is NOT about two sources); H5d' closes it
#   X6  true-stream     : eps in {0, 0.1}, no attacks: H5d' must be
#                         S0-identical at eps=0 and park NOTHING on the
#                         true stream (one-trajectory stand)
#   X7  H5a  oracle     : referee with direct access to W_real closes by
#                         construction AND smuggles a VERACITY source into
#                         the TCB = the 4th axis in disguise (control only)
#   X8  epoch path      : N3-mini (law drift) under H5d': parking must feed
#                         M2 so epoch relearning still fires
#
# Decision gate (fixed before the run):
#   N5 is closed SUBJECT-SIDE within the covering triple
#   iff X4: overwrite=0 AND silent=0 AND correct=1.0 (cross- and single-)
#       AND X6: S0-equivalence at eps=0 AND parked_true=0
#       AND X8: epoch relearn still fires.
#   If instead only X7 closes it -> closure needs an oracle -> the covering
#   triple is NOT sufficient in the multi-writer regime and the minimality
#   thesis is downgraded.

import json
import random
import hashlib
import sys
from collections import Counter

sys.path.insert(0, "/home/z/my-project/scripts")

from e11_noise_battery import (            # stand: imported, never modified
    GLUED, CONTRADICTION, CONFLICT_QUARANTINED, STAT_EXCESS,
    LamportChannel, Projection, SubjectE11, aperture, realized_ring,
    whole_from_style, make_style, deliver_signed, recorded_event, _pk_key,
    EPS0, V_MIN, E_MIN, flip, acc_known_of, law_bit_accuracy, DEC,
)

OUT_JSON = "/home/z/my-project/download/n5_closure_results.json"
OUT_LOG = "/home/z/my-project/download/n5_closure_stdout.log"
CORE_FILES = ["holographic_core.py", "holographic_e10_core.py",
              "vli_battery.py", "e11_noise_battery.py"]

_lines = []


def p(s=""):
    print(s)
    _lines.append(str(s))


def md5_of(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


# =====================================================================
# Subject variants (thin extension layers; the core stand is untouched)
# =====================================================================
class SubjectH5B(SubjectE11):
    """H5b CONTROL: causal ordering. Declared protocol extension: world
    channels stamp a monotonic per-source sequence number ev.seq; the
    subject rejects stale/replayed sequences. Tests the roadmap's claim
    that ordering helps against N5."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.src_seq = {}

    def receive(self, ev):
        if ev.lamport is not None:
            pk = _pk_key(ev.lamport[0])
            seq = getattr(ev, "seq", None)
            if seq is not None:
                if seq <= self.src_seq.get(pk, 0):
                    d = {"pid": ev.pid, "status": "REJECTED_ORDER",
                         "reason": "stale_or_replayed_sequence",
                         "law_write": False, "contact_gate_pass": True,
                         "state_unchanged": True}
                    self.log.append(d)
                    return d
                self.src_seq[pk] = seq
        return super().receive(ev)


class SubjectH5D(SubjectE11):
    """H5d: keeper election. The FIRST attested writer of a position
    becomes its keeper; an attested write from a DIFFERENT source that
    would flip keeper-held values parks (REJECTED_KEEPER, state unchanged)
    unless V_MIN distinct coherent challenges have accumulated (takeover).
    Declared boundary: same-keeper writes are NOT gated (see X5)."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.keeper = {}       # pos -> pk
        self.challenges = {}   # frozenset(anchor) -> [(pid, pk, view)]

    def _clash_pos(self, proj):
        return sorted(pp for pp in proj.anchor if pp in self.asm.known
                      and self.asm.known[pp][0] != proj.view[pp])

    @staticmethod
    def _coherent(led):
        for i in range(len(led)):
            for j in range(i + 1, len(led)):
                v1, v2 = led[i][2], led[j][2]
                shared = set(v1) & set(v2)
                if any(v1[q] != v2[q] for q in shared):
                    return False
        return True

    def receive(self, ev):
        att = self.contact_allows_law(ev)
        if att and ev.lamport is not None:
            pk = _pk_key(ev.lamport[0])
            clash = self._clash_pos(ev.proj)
            foreign = [q for q in clash if self.keeper.get(q, pk) != pk]
            if foreign:
                led = self.challenges.setdefault(frozenset(ev.proj.anchor), [])
                led.append((ev.pid, pk, dict(ev.proj.view)))
                if len({x[0] for x in led}) >= V_MIN and self._coherent(led):
                    for q in ev.proj.anchor:
                        if self.keeper.get(q) not in (None, pk):
                            del self.keeper[q]
                    d = dict(super().receive(ev))
                    d["takeover"] = True
                    return d
                d = {"pid": ev.pid, "status": "REJECTED_KEEPER",
                     "reason": "attested_write_to_foreign_keeper_region",
                     "law_write": False, "contact_gate_pass": True,
                     "state_unchanged": True,
                     "keeper_region": sorted(foreign)}
                self.log.append(d)
                self.hardening_log.append({"keeper_reject": ev.pid})
                return d
        d = super().receive(ev)
        if att and ev.lamport is not None and d["status"] == GLUED:
            pk = _pk_key(ev.lamport[0])
            for q in ev.proj.anchor:
                self.keeper.setdefault(q, pk)
        return d


class SubjectH5DP(SubjectE11):
    """H5d' PRIMARY CANDIDATE: evidence-gated attested writes (pre-commit
    against the subject's own glued state). An ATTESTED event that would
    flip ANY glued value never glues silently: it parks
    (PARKED_CHALLENGED, state unchanged, no belief write) and counts into
    the existing M2 epoch machinery. Re-anchoring happens ONLY through the
    epoch path and ONLY for LAW-COMPLETE challenges: the buffered events
    must jointly vote EVERY period residue with majority agreement per
    residue (a copy-trio at one anchor votes 2 of 4 residues -> can never
    re-anchor). Reuses CONTACT attestation + COHERENCE (grammar
    completeness, epoch machinery) + the VLI parking pattern: no new axis,
    no oracle, no extra TCB. [Rev 2: front-door promotion removed after
    the first run showed it accepts copy-trios — defect D1.]"""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.park_log = []

    def _clash_pos(self, proj):
        return sorted(pp for pp in proj.anchor if pp in self.asm.known
                      and self.asm.known[pp][0] != proj.view[pp])

    def _challenge_complete(self, buf):
        """Do the buffered challenges jointly vote a COMPLETE style?
        Collect (residue -> Counter(bits)) over the events' OWN internal
        edges only (merged boundary edges mix epochs and are not the
        event's vote — D2 convention from E11)."""
        votes = {}
        for _, proj in buf:
            for (i, r) in proj.internal_edges(self.n, self.period):
                bit = proj.view[i] ^ proj.view[(i + 1) % self.n]
                votes.setdefault(r, Counter())[bit] += 1
        if len(votes) < self.period:
            return False
        return all(c.most_common(1)[0][1] >= 0.5 * sum(c.values())
                   for c in votes.values())

    def receive(self, ev):
        att = self.contact_allows_law(ev)
        if att:
            clash = self._clash_pos(ev.proj)
            if clash:
                d = {"pid": ev.pid, "status": "PARKED_CHALLENGED",
                     "reason": "attested_write_flips_glued_values_evidence_gated",
                     "law_write": False, "contact_gate_pass": True,
                     "state_unchanged": True, "clash_positions": clash}
                self.log.append(d)
                self.park_log.append({"park": ev.pid,
                                      "pos": clash})
                # parked challenges feed the EXISTING M2 epoch machinery:
                # a coherent AND law-complete parked streak is exactly how
                # a real epoch change re-anchors through the front door
                self.fail_streak_att += 1
                self.epoch_buffer.append((ev.pid, ev.proj))
                self.epoch_buffer = self.epoch_buffer[-E_MIN:]
                if (self.fail_streak_att >= E_MIN
                        and len(self.epoch_buffer) == E_MIN
                        and self._mutually_coherent(self.epoch_buffer)
                        and self._challenge_complete(self.epoch_buffer)):
                    self._relearn()
                    d = dict(d)
                    d["epoch_switched"] = True
                return d
        return super().receive(ev)


class SubjectOracle(SubjectE11):
    """H5a CONTROL: pre-commit referee with DIRECT access to the world's
    realized ring. Closes N5 by construction — and smuggles a VERACITY
    source (world truth) into the subject's TCB: the 4th axis in disguise.
    Included to measure what 'closure at any cost' looks like."""

    def __init__(self, *a, referee_ring=None, **kw):
        super().__init__(*a, **kw)
        self.referee_ring = referee_ring

    def receive(self, ev):
        att = self.contact_allows_law(ev)
        if att and self.referee_ring is not None:
            bad = [q for q in ev.proj.anchor
                   if self.referee_ring[q] != ev.proj.view[q]]
            if bad:
                d = {"pid": ev.pid, "status": "REJECTED_ORACLE",
                     "reason": "referee_rejects_false_content",
                     "law_write": False, "contact_gate_pass": True,
                     "state_unchanged": True, "oracle_positions": bad}
                self.log.append(d)
                return d
        return super().receive(ev)


# =====================================================================
# Factories (mirror fresh_e11 construction exactly)
# =====================================================================
def f_base(n, P, sid, WC, W=None):
    return SubjectE11(n, P, sid=sid, contact="verify", world_channel=WC)


def f_h5b(n, P, sid, WC, W=None):
    return SubjectH5B(n, P, sid=sid, contact="verify", world_channel=WC)


def f_h5d(n, P, sid, WC, W=None):
    return SubjectH5D(n, P, sid=sid, contact="verify", world_channel=WC)


def f_h5dp(n, P, sid, WC, W=None):
    return SubjectH5DP(n, P, sid=sid, contact="verify", world_channel=WC)


def f_oracle(n, P, sid, WC, W=None):
    return SubjectOracle(n, P, sid=sid, contact="verify", world_channel=WC,
                         referee_ring=W)


# =====================================================================
# The N5 scenario: a faithful, parameterized clone of e11.n5
# (identical RNG draw order -> bit-exact paired comparison)
# =====================================================================
def n5v(factory, trials=30, seed=46, flip_prob=0.3, eps=0.05,
        single_attester=False, false_repeats=1, stamp_seq=False, trace=None):
    rng = random.Random(seed)
    n, P = 16, 4
    correct = quarantines = silent_poison = overwrites = replacements = 0
    true_first_total = false_first_total = correct_tf = order_privilege = 0
    relearns = 0
    conflicts = skip_style = skip_noconflict = 0
    last_status = Counter()
    for t in range(trials):
        style = make_style(rng, P)
        w = whole_from_style(style, n, v0=1)
        W_real = realized_ring(w, n, style, rng, eps)
        WC1 = LamportChannel(f"N5a_{t}")
        WC2 = None if single_attester else LamportChannel(f"N5b_{t}")
        s = factory(n, P, f"N5_{t}", WC1, W_real)
        if WC2 is not None:
            s.add_trust_anchor(WC2.pubkey)
        seqs = {"a": 0, "b": 0}

        def stamp(ev, ch):
            if stamp_seq and ev is not None:
                seqs[ch] += 1
                ev.seq = seqs[ch]
            return ev

        for k, st in enumerate((0, 3, 6, 9)):
            proj = aperture(W_real, n, st, 4, f"R{k}")
            ev, _, _ = deliver_signed(s, proj, WC1, rng, retries=2)
            if ev is not None:
                s.receive(stamp(ev, "a"))
        base_epoch_len = len(s.epoch_log)
        if not s.style():
            skip_style += 1
            continue

        true_p = aperture(W_real, n, 10, 3, "W1")
        flip_view = {pos: (v ^ 1 if rng.random() < flip_prob else v)
                     for pos, v in true_p.view.items()}
        false_ps = [Projection(f"W2_{j}", frozenset(true_p.anchor), flip_view,
                               origin="world") for j in range(false_repeats)]
        if flip_view == true_p.view:
            skip_noconflict += 1
            continue                       # no conflict this trial
        conflicts += 1

        WCX = WC1 if single_attester else WC2

        def true_event():
            ev, _, _ = deliver_signed(s, true_p, WC1, rng, retries=2)
            return stamp(ev, "a")

        def false_event(j=0):
            ev = recorded_event(s, false_ps[j], True, "world",
                                world_channel=WCX, sign=True, record=False)
            if s.contact_allows_law(ev):
                prev, proof = s.record(false_ps[j])
                ev.prev_tip, ev.proof = prev, proof
                return stamp(ev, "b")
            return None

        order = rng.random() < 0.5
        false_makers = [("false", lambda j=j: false_event(j))
                        for j in range(false_repeats)]
        seq = ([("true", true_event)] + false_makers if order
               else false_makers + [("true", true_event)])

        dfalse_status = None
        false_glued = False
        for tag, maker in seq:
            ev = maker()                   # proof issued right before receive
            if ev is None:
                continue
            d = s.receive(ev)
            if tag == "false":
                dfalse_status = DEC(d)
                false_glued = false_glued or (DEC(d) == GLUED)
        if false_glued:
            overwrites += 1
        if dfalse_status == CONFLICT_QUARANTINED:
            quarantines += 1
        if any(a.get("kept") == "incoming" for a in s.arbitration_log):
            replacements += 1
        if any(e.get("switch") for e in s.epoch_log[base_epoch_len:]):
            relearns += 1

        true_kept = all(s.asm.known.get(pos, (None,))[0] == true_p.view[pos]
                        for pos in true_p.anchor)
        false_gone = all(s.asm.known.get(pos, (None,))[0] != flip_view[pos]
                         for pos in true_p.anchor
                         if flip_view[pos] != W_real[pos])
        correct_all = true_kept and false_gone
        if correct_all:
            correct += 1
        if order:
            true_first_total += 1
            if correct_all:
                correct_tf += 1
        else:
            false_first_total += 1
            false_kept = any(s.asm.known.get(pos, (None,))[0] == flip_view[pos]
                             and flip_view[pos] != W_real[pos]
                             for pos in true_p.anchor)
            if false_kept and not correct_all:
                order_privilege += 1
        if not correct_all and any(
                s.asm.known.get(pos, (None,))[0] == flip_view[pos]
                and flip_view[pos] != W_real[pos]
                for pos in true_p.anchor):
            silent_poison += 1
        last_status[dfalse_status or "NONE"] += 1
        if trace is not None:
            trace.append({
                "trial": t, "order": "TF" if order else "FF",
                "true_kept": true_kept, "false_gone": false_gone,
                "correct": correct_all,
                "known_10_12": {p: s.asm.known.get(p, (None,))[0]
                                for p in (10, 11, 12)},
                "W_real_10_12": {p: W_real[p] for p in (10, 11, 12)},
                "flip_10_12": {p: flip_view[p] for p in (10, 11, 12)},
                "dfalse_status": dfalse_status,
            })
    return {
        "trials": trials,
        "conflict_trials": conflicts,
        "skipped_no_style": skip_style,
        "skipped_no_conflict": skip_noconflict,
        "conflict_resolved_correct_rate": round(correct / trials, 3),
        "correct_rate_of_conflicts": round(correct / max(1, conflicts), 3),
        "true_first_resolved_rate": round(
            correct_tf / max(1, true_first_total), 3),
        "false_first_order_privilege_rate": round(
            order_privilege / max(1, false_first_total), 3),
        "false_event_glued_overwrite_rate": round(overwrites / trials, 3),
        "false_event_quarantined_rate": round(quarantines / trials, 3),
        "silent_poison_rate": round(silent_poison / trials, 3),
        "epoch_switched_rate": round(relearns / trials, 3),
        "false_event_final_status": dict(last_status),
    }


# =====================================================================
# X6: true-stream probes (no attacks)
# =====================================================================
def clean_stream(factory, seed=7, eps=0.0):
    rng = random.Random(seed)
    n, P = 16, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)
    W = realized_ring(w, n, style, rng, eps)
    WC = LamportChannel("CLEAN")
    s = factory(n, P, "CLEAN", WC, W)
    s1, s2 = [], []
    for k, st in enumerate((0, 3, 6, 9)):
        proj = aperture(W, n, st, 4, f"R{k}")
        ev, _, _ = deliver_signed(s, proj, WC, rng, retries=2)
        if ev is not None:
            s1.append(DEC(s.receive(ev)))
    for k, st in enumerate((0, 3, 6, 9, 12)):
        proj = aperture(W, n, st, 3, f"S{k}")
        ev, _, _ = deliver_signed(s, proj, WC, rng, retries=2)
        if ev is not None:
            s2.append(DEC(s.receive(ev)))
    return {"bootstrap_statuses": s1, "second_pass_statuses": s2,
            "parked_on_true_stream": sum(
                1 for x in s1 + s2 if x == "PARKED_CHALLENGED"),
            "known_accuracy_vs_realized": acc_known_of(s, W)}


# =====================================================================
# X8: N3-mini — epoch drift must still relearn under H5d'
# =====================================================================
def epoch_mini(factory, seed=11, eps=0.0, n_events=6):
    rng = random.Random(seed)
    n, P = 16, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)
    W1 = realized_ring(w, n, style, rng, eps)
    WC = LamportChannel("EPC")
    s = factory(n, P, "EPC", WC, W1)
    for k, st in enumerate((0, 3, 6, 9)):
        proj = aperture(W1, n, st, 4, f"R{k}")
        ev, _, _ = deliver_signed(s, proj, WC, rng, retries=2)
        if ev is not None:
            s.receive(ev)
    style2 = flip(style, 0)
    w2 = whole_from_style(style2, n, v0=1)
    W2 = realized_ring(w2, n, style2, rng, eps)
    stats = []
    for k, st in enumerate((0, 3, 6, 9, 1, 4)[:n_events]):
        proj = aperture(W2, n, st, 4, f"E{k}")
        ev, _, _ = deliver_signed(s, proj, WC, rng, retries=2)
        if ev is not None:
            stats.append(DEC(s.receive(ev)))
    law_ok = bool(s.asm.grammar.e_hat) and all(
        b == style2[r] for r, (b, _) in s.asm.grammar.e_hat.items())
    return {"post_change_statuses": stats,
            "epoch_switched": any(e.get("switch") for e in s.epoch_log),
            "law_matches_new_epoch": law_ok,
            "law_residues": len(s.asm.grammar.e_hat)}


# =====================================================================
def main():
    p("ROUND 9' (N5-FIRST): closure attempts of the attested overwrite channel")
    p("stand: 16-bit ring, period-4 law, eps0=%.2f alpha, V_MIN=%d E_MIN=%d"
      % (EPS0, V_MIN, E_MIN))
    p("core md5 before run:")
    md5_before = {f: md5_of(f"/home/z/my-project/scripts/{f}")
                  for f in CORE_FILES}
    for f, h in md5_before.items():
        p(f"  {h}  {f}")
    p("")

    results = {}

    # cross-check against the archived E11 numbers
    try:
        ref = json.load(open("/home/z/my-project/download/e11_results.json"))
        n5ref = ref["N5_attested_conflict"]
    except Exception:
        n5ref = None

    # X1 baseline
    r = n5v(f_base)
    results["X1_baseline"] = r
    p("--- X1 baseline (reproduction of E11/N5) ---")
    p(f"    overwrite={r['false_event_glued_overwrite_rate']} "
      f"silent={r['silent_poison_rate']} "
      f"quarantined={r['false_event_quarantined_rate']} "
      f"correct={r['conflict_resolved_correct_rate']}")
    if n5ref:
        match = (r["false_event_glued_overwrite_rate"]
                 == n5ref["false_event_glued_overwrite_rate"]
                 and r["silent_poison_rate"] == n5ref["silent_poison_rate"]
                 and r["false_event_quarantined_rate"]
                 == n5ref["false_event_quarantined_rate"])
        p(f"    vs archived e11_results.json: "
          f"{'MATCH (bit-exact reproduction)' if match else 'MISMATCH !!'}")
        results["X1_matches_archive"] = match
    p("")

    # X2 H5b ordering control
    r = n5v(f_h5b, stamp_seq=True)
    results["X2_H5B_ordering"] = r
    p("--- X2 H5b causal ordering (per-source monotonic seq) ---")
    p(f"    overwrite={r['false_event_glued_overwrite_rate']} "
      f"silent={r['silent_poison_rate']} "
      f"statuses={r['false_event_final_status']}")
    p("    prediction 'no effect' "
      f"{'CONFIRMED' if r['false_event_glued_overwrite_rate'] >= 0.5 else 'REFUTED'}")
    p("")

    # X3 H5d keeper election
    r = n5v(f_h5d)
    results["X3_H5D_keeper"] = r
    p("--- X3 H5d keeper election (first attested writer keeps) ---")
    p(f"    overwrite={r['false_event_glued_overwrite_rate']} "
      f"silent={r['silent_poison_rate']} "
      f"correct={r['conflict_resolved_correct_rate']} "
      f"statuses={r['false_event_final_status']}")
    p("")

    # X4 H5d' evidence-gated writes
    r = n5v(f_h5dp)
    results["X4_H5DP_evidence_gated"] = r
    p("--- X4 H5d' evidence-gated attested writes (PRIMARY) ---")
    p(f"    conflicts={r['conflict_trials']}/{r['trials']} "
      f"(skipped: no_style={r['skipped_no_style']}, "
      f"no_conflict={r['skipped_no_conflict']})")
    p(f"    overwrite={r['false_event_glued_overwrite_rate']} "
      f"silent={r['silent_poison_rate']} "
      f"correct_of_conflicts={r['correct_rate_of_conflicts']} "
      f"statuses={r['false_event_final_status']}")
    p("")

    # X4b attacker trio vs H5d'
    r = n5v(f_h5dp, false_repeats=3)
    results["X4b_H5DP_attacker_trio"] = r
    p("--- X4b attacker trio (3 coherent false events) vs H5d' ---")
    p(f"    overwrite={r['false_event_glued_overwrite_rate']} "
      f"silent={r['silent_poison_rate']} "
      f"epoch_switched={r['epoch_switched_rate']} "
      f"statuses={r['false_event_final_status']}")
    p("")

    # X5 single attester
    r = n5v(f_base, single_attester=True)
    results["X5a_single_attester_baseline"] = r
    p("--- X5a single attester (attacker holds THE trusted channel) ---")
    p(f"    overwrite={r['false_event_glued_overwrite_rate']} "
      f"silent={r['silent_poison_rate']} "
      f"statuses={r['false_event_final_status']}")
    r = n5v(f_h5dp, single_attester=True)
    results["X5b_single_attester_H5DP"] = r
    p("--- X5b single attester under H5d' ---")
    p(f"    overwrite={r['false_event_glued_overwrite_rate']} "
      f"silent={r['silent_poison_rate']} "
      f"correct={r['conflict_resolved_correct_rate']} "
      f"statuses={r['false_event_final_status']}")
    p("")

    # X6 true-stream
    for eps in (0.0, 0.1):
        b = clean_stream(f_base, eps=eps)
        h = clean_stream(f_h5dp, eps=eps)
        key = f"X6_true_stream_eps{eps}"
        results[key] = {"baseline": b, "H5DP": h}
        p(f"--- X6 true stream eps={eps} ---")
        p(f"    baseline second_pass={b['second_pass_statuses']} "
          f"parked={b['parked_on_true_stream']}")
        p(f"    H5DP    second_pass={h['second_pass_statuses']} "
          f"parked={h['parked_on_true_stream']} "
          f"acc_known={h['known_accuracy_vs_realized']}")
        if eps == 0.0:
            same = (b["bootstrap_statuses"] == h["bootstrap_statuses"]
                    and b["second_pass_statuses"] == h["second_pass_statuses"])
            results["X6_S0_equivalence_eps0"] = same
            p(f"    S0-equivalence at eps=0: "
              f"{'YES (statuses identical)' if same else 'NO !!'}")
    p("")

    # X7 oracle control
    r = n5v(f_oracle)
    results["X7_H5A_oracle"] = r
    p("--- X7 H5a oracle referee (CONTROL: smuggles world truth into TCB) ---")
    p(f"    overwrite={r['false_event_glued_overwrite_rate']} "
      f"silent={r['silent_poison_rate']} "
      f"correct={r['conflict_resolved_correct_rate']} "
      f"statuses={r['false_event_final_status']}")
    p("")

    # X8 epoch path under H5d'
    b = epoch_mini(f_base)
    h = epoch_mini(f_h5dp)
    results["X8_epoch_mini"] = {"baseline": b, "H5DP": h}
    p("--- X8 N3-mini (law drift) ---")
    p(f"    baseline: switched={b['epoch_switched']} "
      f"law_new={b['law_matches_new_epoch']} statuses={b['post_change_statuses']}")
    p(f"    H5DP:     switched={h['epoch_switched']} "
      f"law_new={h['law_matches_new_epoch']} statuses={h['post_change_statuses']}")
    p("")

    # ------------------------------------------------------- decision gate
    x4 = results["X4_H5DP_evidence_gated"]
    x5b = results["X5b_single_attester_H5DP"]
    gate = {
        "X4_overwrite_zero": x4["false_event_glued_overwrite_rate"] == 0.0,
        "X4_silent_zero": x4["silent_poison_rate"] == 0.0,
        "X4_correct_full_of_conflicts":
            x4["correct_rate_of_conflicts"] == 1.0,
        "X4b_trio_blocked":
            results["X4b_H5DP_attacker_trio"]["false_event_glued_overwrite_rate"] == 0.0
            and results["X4b_H5DP_attacker_trio"]["silent_poison_rate"] == 0.0,
        "X5b_overwrite_zero": x5b["false_event_glued_overwrite_rate"] == 0.0,
        "X5b_silent_zero": x5b["silent_poison_rate"] == 0.0,
        "X6_S0_equivalence_eps0": results.get("X6_S0_equivalence_eps0", False),
        "X6_parked_true_zero_eps01":
            results["X6_true_stream_eps0.1"]["H5DP"]["parked_on_true_stream"] == 0,
        "X8_relearn_survives": (results["X8_epoch_mini"]["H5DP"]["epoch_switched"]
                                and results["X8_epoch_mini"]["H5DP"]
                                ["law_matches_new_epoch"]),
    }
    verdict_subject_side = all(gate.values())
    results["decision_gate"] = gate
    results["verdict_subject_side_closure"] = verdict_subject_side

    p("=== DECISION GATE (fixed before the run) ===")
    for k, v in gate.items():
        p(f"  [{'PASS' if v else 'FAIL'}] {k}")
    p("")
    if verdict_subject_side:
        p("VERDICT: N5 is closed SUBJECT-SIDE within the covering triple.")
        p("  H5d' (evidence-gated attested writes) uses only CONTACT")
        p("  (attestation), COHERENCE (law-complete epoch evidence) and")
        p("  the VLI parking pattern. No 4th axis. No oracle. The roadmap's")
        p("  'maybe a 4th axis is needed' prediction is FALSIFIED in this")
        p("  stand. Declared boundary (CONTACT != TRUTH invariant): a "
          "compromised-but-attested channel that emits a LAW-COMPLETE "
          "coherent alternative remains indistinguishable from a real "
          "epoch change — that residual is the declared trust semantics "
          "of CONTACT, not a new channel; after H5d' it is non-silent, "
          "multi-event, and logged, where before it was silent and "
          "1-event.")
    else:
        p("VERDICT: subject-side closure FAILED the gate -> minimality")
        p("  thesis downgraded; oracle (X7) remains the only full closure.")
    p("")

    md5_after = {f: md5_of(f"/home/z/my-project/scripts/{f}")
                 for f in CORE_FILES}
    results["core_md5_unchanged"] = md5_before == md5_after
    results["core_md5"] = md5_after
    p("core md5 after run: " + ("UNCHANGED" if md5_before == md5_after
                                else "CHANGED !!"))
    p("EPISTEMIC STATUS: VERIFIED* in the stand (16-bit ring, period-4 law,")
    p("  one-trajectory eps-contamination, binary attestation).")
    p("  GENERAL_MINIMALITY = UNKNOWN. Results are true as stdout of this")
    p("  environment; on transfer they degrade to MODEL_HYPOTHESIS until")
    p("  re-executed.")

    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=2, default=str)
    with open(OUT_LOG, "w") as f:
        f.write("\n".join(_lines) + "\n")
    p(f"\nsaved: {OUT_JSON}")
    p(f"saved: {OUT_LOG}")


if __name__ == "__main__":
    main()
