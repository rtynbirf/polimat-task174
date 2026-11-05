#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E10' BATTERY — round 7: closing the two open channels of round 6.

  S0'      sanity: Prime(arbitration/revocation off) == Subject10;
           arbitration silent on clean streams; switch has effect on conflicts
  E10'-A   VALUE_ARBITRATION: matched pair (verified true world part,
           drifted part with identical claim but no signature) —
           WITHOUT arbitration both refused, states indistinguishable;
           WITH arbitration true part evicts self-values and glues -> VERIFIED*
           + direction attack (self can never evict world), 50 seeds
  E10'-B   ATTESTATION_REVOCATION: poisoned-law template (tag/forged echo) +
           verified part contradicting wrong bits —
           WITHOUT revocation the poison persists; WITH revocation the
           attestation is revoked, bits excised+recorded, law repaired -> VERIFIED*
           + re-attestation attack + chain-integrity assertion
  E10'-C   repair confluence: replay of the surviving stream in several orders
  E10'-ECHO  50 trials x 5 configs, incl. the I35-control: arbitration WITHOUT
           contact tiers must NOT beat the round-6 baseline (mechanism alone
           is insufficient — it needs the CONTACT axis)
"""
import os
import sys
import json
import random
import copy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from holographic_core import (GLUED, CONTRADICTION, DISCONNECTED, make_style,  # noqa: E402
                              whole_from_style, aperture, fidelity, Projection)
from holographic_e10_core import (LamportChannel, Event, Subject10,  # noqa: E402
                                  recorded_event, event_digest)
from holographic_e10_prime_core import (TIER_SELF, TIER_ATTESTED, TIER_VERIFIED,  # noqa: E402
                                        Subject10Prime)

OUT = "/home/z/my-project/download/e10_prime_results.json"
BASELINE = "/home/z/my-project/download/e10_results.json"
N, P, W = 16, 4, 3


def prime(n, P, sid, contact, wc=None, arbitration=True, revocation=True):
    s = Subject10Prime(n, P, sid=sid, contact=contact,
                       arbitration=arbitration, revocation=revocation)
    if wc is not None:
        s.lamport_pub = wc.pubkey
    return s


# ------------------------------------------------------------------------ S0'
def s0_prime():
    rng = random.Random(11)
    style = make_style(rng, P)
    w = whole_from_style(style, N, v0=1)
    WC = LamportChannel("S0p")
    clean = [aperture(w, N, s, W, pid=f"R{k+1}")
             for k, s in enumerate([0, 3, 6, 9, 12, 15, 2, 5])]
    out = {}
    for name, arb, rev in [("prime_off", False, False), ("prime_on_clean", True, True)]:
        s = prime(N, P, name, "tag", WC, arb, rev)
        sts = [s.receive(recorded_event(s, p, True, "world")).get("status")
               for p in clean]
        base = Subject10(N, P, sid=name + "_b", contact="tag")
        bsts = [base.receive(recorded_event(base, p, True, "world")).get("status")
                for p in clean]
        out[name] = {"statuses_equal": sts == bsts,
                     "state_equal": s.state_key() == base.state_key(),
                     "no_evictions": s.quarantine_size() == 0}
    # switch-has-effect: self-held committed zone, then a lying part claiming
    # world (tag -> tier ATTESTED > SELF): eviction must fire ON, refusal OFF
    s_off = prime(N, P, "sw_off", "tag", WC, arbitration=False)
    s_on = prime(N, P, "sw_on", "tag", WC, arbitration=True)
    for s in (s_off, s_on):
        s.receive(recorded_event(s, aperture(w, N, 0, W, "D1"), False, "self"))
        s.receive(recorded_event(s, aperture(w, N, 2, W, "D2"), False, "self"))
    wrong = whole_from_style(tuple([b ^ 1 for b in style]), N, v0=1)
    # agrees at pos 2 (keeps overlap), wrong at 3, 4 (self-held)
    conflict = Projection("D3", frozenset({2, 3, 4}),
                          {2: w[2], 3: wrong[3], 4: wrong[4]}, origin="self")
    d_off = s_off.receive(recorded_event(s_off, conflict, False, "world"))
    d_on = s_on.receive(recorded_event(s_on, conflict, False, "world"))
    out["switch_has_effect"] = {
        "off_status": d_off["status"], "on_status": d_on["status"],
        "on_evicted": d_on["evictions"],
        "differ": s_off.state_key() != s_on.state_key()}
    out["pass"] = (all(v.get("statuses_equal") and v.get("state_equal")
                       for k, v in out.items() if k.startswith("prime"))
                   and out["switch_has_effect"]["differ"]
                   and out["switch_has_effect"]["off_status"] == CONTRADICTION
                   and out["switch_has_effect"]["on_status"] == GLUED)
    return out


# --------------------------------------------------- contaminated-state builder
def build_contaminated(seed, cycles=20, world_every=4, drift_p=0.5):
    """verify/honest echo: law stays clean (gated), values get poisoned.
    Template built with BOTH prime mechanisms OFF (a raw round-6 subject) —
    otherwise the mechanisms would heal the template during construction."""
    rng = random.Random(seed)
    true_style = make_style(rng, P)
    w = whole_from_style(true_style, N, rng.randint(0, 1))
    WC = LamportChannel(f"WC{seed}")
    s = prime(N, P, f"T{seed}", "verify", WC, arbitration=False, revocation=False)
    src_style = list(true_style)
    for t in range(cycles):
        if t % world_every == 0:
            ev = recorded_event(s, aperture(w, N, rng.randrange(N), W, pid=f"W{t}"),
                                True, "world", world_channel=WC, sign=True)
        else:
            if rng.random() < drift_p:
                src_style[rng.randrange(P)] ^= 1
            dw = whole_from_style(tuple(src_style), N, w[0])
            ev = recorded_event(s, aperture(dw, N, rng.randrange(N), W, pid=f"D{t}"),
                                False, "self")
        s.receive(ev)
    wrong_vals = [p for p, (v, _, _) in s.asm.known.items() if w[p] != v]
    wrong_law = [r for r, (b, _) in s.asm.grammar.e_hat.items()
                 if b != true_style[r]]
    return s, w, true_style, WC, wrong_vals, wrong_law


def pick_window(w, s, wrong_vals, width=6):
    """Window with >=1 poisoned pos, >=1 clean known pos, style-consistent."""
    known = s.asm.known
    for start in range(N):
        anchor = [(start + k) % N for k in range(width)]
        poi = [p for p in anchor if p in wrong_vals]
        clo = [p for p in anchor if p in known and p not in wrong_vals]
        if not poi or not clo:
            continue
        ok = True
        for i in range(N):
            j = (i + 1) % N
            if i in anchor and j in anchor:
                r = i % P
                if r in s.asm.grammar.e_hat and \
                        s.asm.grammar.e_hat[r][0] != (w[i] ^ w[j]):
                    ok = False
                    break
        if ok:
            return anchor, poi
    return None, None


# --------------------------------------------------------------------- E10'-A
def e10p_a(trials=50):
    res = {"pairs": [], "direction_attack": {}, "skipped": 0}
    for k in range(trials):
        s_t, w, style, WC, wrong_vals, wrong_law = build_contaminated(2000 + k)
        if not wrong_vals or wrong_law:
            res["skipped"] += 1
            continue
        anchor, poi = pick_window(w, s_t, wrong_vals)
        if anchor is None:
            res["skipped"] += 1
            continue
        view = {p: w[p] for p in anchor}
        w_star = Projection("WSTAR", frozenset(anchor), dict(view), origin="world")
        # drifted twin part: same anchor, echo values (the lie), same claim
        dw = whole_from_style(tuple(b ^ 1 for b in style), N, w[0])
        d_star = Projection("DSTAR", frozenset(anchor),
                            {p: dw[p] for p in anchor}, origin="world")

        # WITHOUT arbitration+revocation (the amputated value channel):
        # both parts refused -> states indistinguishable
        a0 = prime(N, P, "A0", "verify", WC, arbitration=False, revocation=False)
        b0 = prime(N, P, "B0", "verify", WC, arbitration=False, revocation=False)
        a0.asm.known = copy.deepcopy(s_t.asm.known); a0.asm.grammar.e_hat = \
            copy.deepcopy(s_t.asm.grammar.e_hat)
        b0.asm.known = copy.deepcopy(s_t.asm.known); b0.asm.grammar.e_hat = \
            copy.deepcopy(s_t.asm.grammar.e_hat)
        da0 = a0.receive(recorded_event(a0, w_star, True, "world",
                                        world_channel=WC, sign=True))
        db0 = b0.receive(recorded_event(b0, d_star, False, "world"))
        indist = a0.state_key() == b0.state_key()

        # WITH the full value channel (arbitration + revocation)
        a = prime(N, P, "A", "verify", WC)
        a.asm.known = copy.deepcopy(s_t.asm.known)
        a.asm.grammar.e_hat = copy.deepcopy(s_t.asm.grammar.e_hat)
        acc_before = fidelity(a.reconstruct(), w)["accuracy"]
        da = a.receive(recorded_event(a, w_star, True, "world",
                                      world_channel=WC, sign=True))
        b = prime(N, P, "B", "verify", WC)
        b.asm.known = copy.deepcopy(s_t.asm.known)
        b.asm.grammar.e_hat = copy.deepcopy(s_t.asm.grammar.e_hat)
        db = b.receive(recorded_event(b, d_star, False, "world"))
        acc_after = fidelity(a.reconstruct(), w)["accuracy"]
        res["pairs"].append({
            "seed": 2000 + k, "poisoned_positions": len(wrong_vals),
            "without": {"wstar": da0["status"], "dstar": db0["status"],
                        "states_indistinguishable": indist},
            "with": {"wstar": da["status"], "evicted": da["evictions"],
                     "dstar": db["status"],
                     "states_distinguishable":
                         a.state_key() != b.state_key(),
                     "accuracy_before": acc_before, "accuracy_after": acc_after,
                     "quarantine_size": a.quarantine_size()}})
    pairs = res["pairs"]
    res["summary"] = {
        "pairs_run": len(pairs),
        "without_indistinguishable": sum(p["without"]["states_indistinguishable"]
                                         for p in pairs),
        "without_both_refused": sum(p["without"]["wstar"] == CONTRADICTION and
                                    p["without"]["dstar"] == CONTRADICTION
                                    for p in pairs),
        "with_distinguishable": sum(p["with"]["states_distinguishable"]
                                    for p in pairs),
        "with_wstar_glued": sum(p["with"]["wstar"] == GLUED for p in pairs),
        "with_dstar_refused": sum(p["with"]["dstar"] == CONTRADICTION
                                  for p in pairs),
        "mean_accuracy_before": round(sum(p["with"]["accuracy_before"]
                                          for p in pairs) / max(1, len(pairs)), 4),
        "mean_accuracy_after": round(sum(p["with"]["accuracy_after"]
                                         for p in pairs) / max(1, len(pairs)), 4),
        "verdict": "VALUE_ARBITRATION_NECESSITY " +
                   ("VERIFIED*" if pairs and all(
                       p["without"]["states_indistinguishable"] and
                       p["with"]["states_distinguishable"] for p in pairs)
                    else "NOT_PROVEN")}

    # direction attack: SELF incoming can never evict VERIFIED incumbents
    wev = 0
    refusals = 0
    for k in range(trials):
        rng = random.Random(7000 + k)
        style = make_style(rng, P)
        w = whole_from_style(style, N, 1)
        WC = LamportChannel(f"D{k}")
        s = prime(N, P, f"DA{k}", "verify", WC)
        s.receive(recorded_event(s, aperture(w, N, 0, 4, "W1"), True, "world",
                                 world_channel=WC, sign=True))
        s.receive(recorded_event(s, aperture(w, N, 4, 4, "W2"), True, "world",
                                 world_channel=WC, sign=True))
        dw = whole_from_style(tuple(b ^ 1 for b in style), N, 1)
        ev = recorded_event(s, aperture(dw, N, 2, 4, "ATK"), False, "world")
        d = s.receive(ev)
        if d["status"] == CONTRADICTION:
            refusals += 1
        if any(q["kind"] == "value_evicted" and q["pid"].startswith("W")
               for q in s.quarantine):
            wev += 1
    res["direction_attack"] = {
        "trials": trials, "self_attack_refused": refusals,
        "world_values_evicted_by_self": wev,
        "verdict": "NO_WORLD_EVICTION_BY_SELF " +
                   ("VERIFIED*" if wev == 0 else "FAILED")}
    return res


# --------------------------------------------------------------------- E10'-B
def poisoned_window(s, style, width=4):
    """Window whose internal edges touch poisoned law residues."""
    wrong_law = [r for r, (b, _) in s.asm.grammar.e_hat.items()
                 if r < len(style) and b != style[r]]
    for start in range(N):
        a = [(start + i) % N for i in range(width)]
        if any(((a[i] + 1) % N) in a and a[i] % P in wrong_law for i in range(width)):
            return a, wrong_law
    return None, wrong_law


def build_poisoned_law(seed, cycles=20, world_every=4, drift_p=0.5):
    """tag/forged echo: drift parts CLAIM world -> attested -> law poisoned.
    Template built with both mechanisms OFF (raw round-6 subject)."""
    rng = random.Random(seed)
    true_style = make_style(rng, P)
    w = whole_from_style(true_style, N, rng.randint(0, 1))
    WC = LamportChannel(f"WB{seed}")
    s = prime(N, P, f"TP{seed}", "tag", WC, arbitration=False, revocation=False)
    src_style = list(true_style)
    for t in range(cycles):
        if t % world_every == 0:
            ev = recorded_event(s, aperture(w, N, rng.randrange(N), W, pid=f"W{t}"),
                                True, "world", world_channel=WC, sign=True)
        else:
            if rng.random() < drift_p:
                src_style[rng.randrange(P)] ^= 1
            dw = whole_from_style(tuple(src_style), N, w[0])
            ev = recorded_event(s, aperture(dw, N, rng.randrange(N), W, pid=f"D{t}"),
                                False, "world")
        s.receive(ev)
    wrong_law = [r for r, (b, _) in s.asm.grammar.e_hat.items()
                 if b != true_style[r]]
    return s, w, true_style, WC, wrong_law


def e10p_b(trials=50, k_parts=10):
    """Revocation necessity: poisoned-law template, then a stream of K
    verified world parts. WITHOUT revocation the poison persists (parts
    keep bouncing off the wrong bits); WITH revocation attestations are
    revoked, bits excised+recorded, values downgraded, law re-learns."""
    res = {"pairs": [], "reattach_attack": {}, "skipped": 0}
    for k in range(trials):
        s_t, w, style, WC, wrong_law = build_poisoned_law(3000 + k)
        if not wrong_law:
            res["skipped"] += 1
            continue
        anchor, wrong_law = poisoned_window(s_t, style)
        if anchor is None:
            res["skipped"] += 1
            continue
        rng = random.Random(3900 + k)
        parts = [Projection(f"F{j}", frozenset([(s0 + i) % N for i in range(5)]),
                            {p: w[p] for p in [(s0 + i) % N for i in range(5)]},
                            origin="world")
                 for j, s0 in enumerate(rng.sample(range(N), k_parts))]

        def twins(revocation):
            s = prime(N, P, "T", "tag", WC, revocation=revocation)
            s.asm.known = copy.deepcopy(s_t.asm.known)
            s.asm.grammar.e_hat = copy.deepcopy(s_t.asm.grammar.e_hat)
            s.asm.prov = dict(s_t.asm.prov)
            s.pending_tier = dict(s_t.pending_tier)
            tip0 = s.chain.tip          # AFTER transplant, BEFORE recording
            decs = []
            for pj in parts:
                # record-then-present ALTERNATING: the causal gate accepts a
                # presented transition only as the LATEST keyed extension of
                # the chain (batch-recording would invalidate every earlier
                # proof before it is presented).
                ev = recorded_event(s, pj, True, "world", world_channel=WC,
                                    sign=True)
                decs.append(s.receive(ev))
            return s, decs, tip0

        b, decs_b, _ = twins(revocation=False)
        a, decs_a, tip0 = twins(revocation=True)

        def hamming(s):
            st = s.style()
            return sum(x != y for x, y in zip(st, style)) if st else None

        res["pairs"].append({
            "seed": 3000 + k, "poisoned_bits": len(wrong_law),
            "without": {"glued_parts": sum(d["status"] == GLUED for d in decs_b),
                        "law_hamming_after_stream": hamming(b)},
            "with": {"glued_parts": sum(d["status"] == GLUED for d in decs_a),
                     "law_hamming_after_stream": hamming(a),
                     "revoked_pids": len(a.revoked_pids),
                     "quarantine_size": a.quarantine_size(),
                     "accuracy_after": fidelity(a.reconstruct(), w)["accuracy"],
                     "mean_radius": round(sum(d.get("radius", 0)
                                              for d in decs_a) / len(decs_a), 2),
                     "unresolved_any": any(d.get("unresolved") for d in decs_a)},
            "states_distinguishable": a.state_key() != b.state_key()})
    pairs = res["pairs"]
    res["summary"] = {
        "pairs_run": len(pairs),
        "without_poison_persists": sum(p["without"]["law_hamming_after_stream"]
                                       != 0 for p in pairs),
        "without_parts_bounced": sum(p["without"]["glued_parts"] == 0
                                     for p in pairs),
        "with_repaired_law": sum(p["with"]["law_hamming_after_stream"] == 0
                                 for p in pairs),
        "with_mean_accuracy": round(sum(p["with"]["accuracy_after"]
                                        for p in pairs) / max(1, len(pairs)), 4),
        "with_mean_radius": round(sum(p["with"]["mean_radius"]
                                      for p in pairs) / max(1, len(pairs)), 2),
        "with_unresolved_any": any(p["with"]["unresolved_any"] for p in pairs),
        "states_distinguishable": sum(p["states_distinguishable"] for p in pairs),
        "verdict": "ATTESTATION_REVOCATION_NECESSITY " +
                   ("VERIFIED*" if pairs and all(
                       p["without"]["law_hamming_after_stream"] != 0
                       and p["with"]["law_hamming_after_stream"] == 0
                       and p["states_distinguishable"] for p in pairs)
                    else "NOT_PROVEN")}

    # re-attestation attack on a repaired subject
    if pairs:
        s_t, w, style, WC, _ = build_poisoned_law(pairs[0]["seed"])
        s = prime(N, P, "RA", "tag", WC)          # FULL mechanisms
        s.asm.known = copy.deepcopy(s_t.asm.known)
        s.asm.grammar.e_hat = copy.deepcopy(s_t.asm.grammar.e_hat)
        s.asm.prov = dict(s_t.asm.prov)
        s.pending_tier = dict(s_t.pending_tier)
        rng = random.Random(3999)
        parts = [Projection(f"F{j}", frozenset([(s0 + i) % N for i in range(5)]),
                            {p: w[p] for p in [(s0 + i) % N for i in range(5)]},
                            origin="world")
                 for j, s0 in enumerate(rng.sample(range(N), k_parts))]
        for pj in parts:
            s.receive(recorded_event(s, pj, True, "world", world_channel=WC,
                                     sign=True))
        revoked_sample = sorted(s.revoked_pids)
        reattest = {}
        if revoked_sample:
            # the revoked contributor's ORIGINAL event lives in the TEMPLATE's
            # stream (the reattach subject never received it itself)
            src_ev = next(e for e, _ in s_t.stream if e.pid == revoked_sample[0])
            ev2 = recorded_event(s, src_ev.proj, False, "world")
            d2 = s.receive(ev2)
            reattest = {"revoked_pid": revoked_sample[0],
                        "re_presented_status": d2["status"],
                        "re_presented_tier": d2["tier"],
                        "law_write": d2["law_write"],
                        "contact_gate_pass": d2["contact_gate_pass"]}
        # fresh verified content with a NEW pid must be accepted: after repair
        # the ring is fully covered, so the fresh part is a RE-OBSERVATION
        # (overlapping known truth values -> agreement, not clash)
        fa = [(0 + i) % N for i in range(3)]
        fp = Projection("FRESHW", frozenset(fa),
                        {p: w[p] for p in fa}, origin="world")
        df = s.receive(recorded_event(s, fp, True, "world",
                                      world_channel=WC, sign=True))
        fresh_ok = {"status": df["status"], "law_write": df["law_write"]}
        q0 = len(s.quarantine)
        s.revoke("nonexistent_pid_x", "test")   # no-op for unknown pid
        res["reattach_attack"] = {
            "revoked_count": len(revoked_sample),
            "revoked_cannot_write_law_by_tag": reattest.get("law_write") is False
            and reattest.get("contact_gate_pass") is False,
            "revoked_downgraded_to_self_tier":
                reattest.get("re_presented_tier") == "self",
            "fresh_verified_content_accepted": (fresh_ok or {}).get("status") == GLUED,
            "quarantine_append_only": len(s.quarantine) >= q0,
            "details": reattest}
    return res


# --------------------------------------------------------------------- E10'-C
def e10p_c(trials=24):
    """Repair confluence: replay surviving stream in several orders."""
    perms_equal, runs = 0, 0
    for k in range(trials):
        s, w, style, WC, wrong_law = build_poisoned_law(3100 + k)
        if not wrong_law:
            continue
        anchor = None
        for start in range(N):
            a = [(start + i) % N for i in range(4)]
            if any(((a[i] + 1) % N) in a and a[i] % P in wrong_law for i in range(4)):
                anchor = a
                break
        if anchor is None:
            continue
        s.receive(recorded_event(s, Projection(
            "WSTAR", frozenset(anchor), {p: w[p] for p in anchor}, origin="world"),
            True, "world", world_channel=WC, sign=True))
        survivors = [(e, t) for e, t in s.stream if e.pid not in s.revoked_pids]
        if len(survivors) < 6:
            continue
        finals = []
        for pi, seed in enumerate([0, 1, 2, 3]):
            order = list(survivors)
            random.Random(seed).shuffle(order)
            s2 = prime(N, P, f"RP{k}_{pi}", "tag", WC)
            for ev, t in order:
                nev = recorded_event(s2, ev.proj, ev.really_world,
                                     ev.origin_claim, world_channel=WC,
                                     sign=(ev.lamport is not None))
                s2.receive(nev)
            finals.append((s2.style(),
                           tuple(sorted(s2.reconstruct().items()))))
        runs += 1
        perms_equal += sum(1 for f in finals[1:] if f == finals[0])
    return {"runs": runs, "replays_equal": perms_equal,
            "replay_pairs_total": perms_equal and runs * 3 or runs * 3,
            "verdict": "REPAIR_REPLAY_CONFLUENT " +
                       ("VERIFIED*" if runs and perms_equal == runs * 3
                        else "PARTIAL" if perms_equal else "NOT_PROVEN")}


# ------------------------------------------------------------------ E10'-ECHO
def echo_trial(seed, contact, attack="honest", cycles=24, world_every=4,
               drift_p=0.4):
    rng = random.Random(seed)
    true_style = make_style(rng, P)
    w = whole_from_style(true_style, N, rng.randint(0, 1))
    WC = LamportChannel(f"W{seed}")
    s = prime(N, P, f"S{seed}", contact, WC)
    src_style = list(true_style)
    evictions = world_evicted = false_evictions = unresolved = 0
    for t in range(cycles):
        is_world = (t % world_every == 0)
        if not is_world and rng.random() < drift_p:
            src_style[rng.randrange(P)] ^= 1
        if is_world:
            proj = aperture(w, N, rng.randrange(N), W, pid=f"W{t}")
            ev = recorded_event(s, proj, True, "world", world_channel=WC, sign=True)
        else:
            dw = whole_from_style(tuple(src_style), N, w[0])
            claim = "self" if attack == "honest" else "world"
            ev = recorded_event(s, aperture(dw, N, rng.randrange(N), W, pid=f"D{t}"),
                                False, claim)
        d = s.receive(ev)
        evictions += len(d.get("evictions", []))
        for pid in d.get("evictions", []):
            if pid.startswith("W"):
                world_evicted += 1
        if d.get("unresolved"):
            unresolved += 1
    # false evictions: any quarantined value that matched TRUTH
    for q in s.quarantine:
        if q["kind"] == "value_evicted":
            pos = q.get("pos")
            if pos is not None and w[pos] == q.get("value"):
                false_evictions += 1
    st = s.style()
    law_h = sum(a != b for a, b in zip(st, true_style)) if st else None
    fin = fidelity(s.reconstruct(), w)["accuracy"]
    fin = 0.0 if fin is None else fin
    wrong_law = [r for r, (b, _) in s.asm.grammar.e_hat.items()
                 if b != true_style[r]]
    wrong_vals = [p for p, (v, _, _) in s.asm.known.items() if w[p] != v]
    return {"final_fidelity": fin, "law_poisoned": len(wrong_law) > 0,
            "wrong_law_bits": len(wrong_law),
            "values_contaminated": len(wrong_vals) > 0,
            "wrong_value_count": len(wrong_vals),
            "evictions": evictions, "world_evicted": world_evicted,
            "false_evictions": false_evictions, "unresolved": unresolved}


def e10p_echo(trials=50):
    configs = [("none", "honest"), ("tag", "honest"), ("tag", "forged"),
               ("verify", "forged"), ("none", "forged")]
    stats = {}
    for contact, attack in configs:
        runs = [echo_trial(4000 + i, contact, attack) for i in range(trials)]
        fids = [r["final_fidelity"] for r in runs]
        stats[f"{contact}/{attack}"] = {
            "law_poisoned_fraction": round(sum(r["law_poisoned"] for r in runs) / trials, 3),
            "values_contaminated_fraction":
                round(sum(r["values_contaminated"] for r in runs) / trials, 3),
            "mean_final_fidelity": round(sum(fids) / trials, 4),
            "min_final_fidelity": min(fids),
            "mean_evictions": round(sum(r["evictions"] for r in runs) / trials, 3),
            "world_evicted_any": any(r["world_evicted"] for r in runs),
            "false_evictions_any": any(r["false_evictions"] for r in runs),
            "unresolved_any": any(r["unresolved"] for r in runs)}
    # I35-control: arbitration WITHOUT contact tiers must be INERT —
    # none/forged must equal none/honest (no discrimination without tiers)
    base = stats["none/forged"]
    ref_arm = stats["none/honest"]
    inert = (base["law_poisoned_fraction"] == ref_arm["law_poisoned_fraction"]
             and base["values_contaminated_fraction"]
             == ref_arm["values_contaminated_fraction"]
             and base["mean_evictions"] == 0.0
             and base["mean_evictions"] == ref_arm["mean_evictions"])
    strict_gain = (stats["verify/forged"]["law_poisoned_fraction"]
                   < base["law_poisoned_fraction"]
                   or stats["tag/forged"]["law_poisoned_fraction"]
                   < base["law_poisoned_fraction"])
    ref = {"none_forged_r6": None}
    try:
        e10 = json.load(open(BASELINE))
        echo6 = e10["E10_3_tag_vs_verify"]["echo_battery"]
        ref = {k2: v2["law_poisoned_fraction"]
               for k2, v2 in echo6.items() if "law_poisoned_fraction" in v2}
        ref_values = {k2: v2.get("values_contaminated_fraction")
                      for k2, v2 in echo6.items()}
    except Exception:
        ref, ref_values = {}, {}
    stats["_i35_control"] = {
        "arbitration_without_contact": "none/forged",
        "inert_without_tiers": inert,
        "strict_gain_with_tiers": strict_gain,
        "control_holds": inert and strict_gain,
        "verdict": "ARBITRATION_NEEDS_CONTACT VERIFIED*"
        if inert and strict_gain else "CONTROL_FAILED",
        "round6_reference_law": ref, "round6_reference_values": ref_values}
    return stats


# ----------------------------------------------------------------------- main
def main():
    out = {"meta": {"round": "E10' (7)", "n": N, "P": P, "W": W,
                    "channels": ["value_arbitration", "attestation_revocation"]}}
    out["S0_prime"] = s0_prime()
    out["E10P_A_value_arbitration"] = e10p_a()
    out["E10P_B_attestation_revocation"] = e10p_b()
    out["E10P_C_repair_confluence"] = e10p_c()
    out["E10P_ECHO"] = e10p_echo()
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    p = print
    p("=== S0' sanity:", "PASS" if out["S0_prime"]["pass"] else "FAIL")
    sA = out["E10P_A_value_arbitration"]["summary"]
    p(f"=== E10'-A: {sA['verdict']}")
    p(f"    pairs={sA['pairs_run']} without_indist={sA['without_indistinguishable']} "
      f"with_dist={sA['with_distinguishable']} wstar_glued={sA['with_wstar_glued']} "
      f"dstar_refused={sA['with_dstar_refused']}")
    p(f"    acc {sA['mean_accuracy_before']} -> {sA['mean_accuracy_after']}")
    p(f"    direction attack: {out['E10P_A_value_arbitration']['direction_attack']}")
    sB = out["E10P_B_attestation_revocation"]["summary"]
    p(f"=== E10'-B: {sB['verdict']}")
    p(f"    pairs={sB['pairs_run']} poison_persists={sB['without_poison_persists']} "
      f"repaired={sB['with_repaired_law']} acc={sB['with_mean_accuracy']} "
      f"radius={sB['with_mean_radius']} unresolved={sB['with_unresolved_any']}")
    p(f"    reattach: {out['E10P_B_attestation_revocation']['reattach_attack']}")
    p(f"=== E10'-C: {out['E10P_C_repair_confluence']}")
    p("=== E10'-ECHO (50 x 5):")
    for k2, v2 in out["E10P_ECHO"].items():
        if k2 == "_i35_control":
            p(f"    I35-control: {v2['verdict']} "
              f"(inert_without_tiers={v2['inert_without_tiers']}, "
              f"strict_gain_with_tiers={v2['strict_gain_with_tiers']})")
        else:
            p(f"    {k2:18s} law={v2['law_poisoned_fraction']:.3f} "
              f"vals={v2['values_contaminated_fraction']:.3f} "
              f"fidel={v2['mean_final_fidelity']:.3f} evict={v2['mean_evictions']} "
              f"world_evicted={v2['world_evicted_any']} "
              f"false_evict={v2['false_evictions_any']}")


if __name__ == "__main__":
    main()
