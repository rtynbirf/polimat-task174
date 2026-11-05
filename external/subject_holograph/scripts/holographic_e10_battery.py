#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E10 BATTERY — round 6: surgical amputation. Criterion (I31): for each axis,
find a pair of states/events distinguishable WITH the axis and
indistinguishable WITHOUT it. Not "the system broke" — WHICH DISCRIMINATION
DISAPPEARS.

  S0      sanity: VariantAssembly(full) behaviourally identical to core Assembly
  E10-A   amputation of CAUSAL: (real, coherent forgery) + (real, foreign);
          keyed-chain forgery cost measured
  E10-B   amputation of COHERENCE: (true transition, causally-valid glitch)
  E10-C   amputation of CONTACT: matched pair (world event, self event) with
          IDENTICAL content — the only difference is the source claim
  E10-3   CONTACT_TAG vs CONTACT_VERIFICATION vs none: honest pair, forged
          claim pair, echo-chamber battery (drift), injection attack
  E10-F   fictitious axis METADATA (labels uncorrelated with origin), 50 trials
  E10-2   trivialization of GRAMMAR / ASSEMBLY / INTEGRATION: which
          discrimination each sub-mechanism carries
"""
import os
import sys
import json
import random
import copy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from holographic_core import (GLUED, CONTRADICTION, DISCONNECTED, make_style,  # noqa: E402
                              whole_from_style, aperture, fidelity, Assembly,
                              Projection)
from holographic_e10_core import (REFUSED_CAUSAL, CausalChain, OpenChain, H,   # noqa: E402
                                  LamportChannel, Event, VariantAssembly,
                                  COHERENCE_CONFIGS, Subject10, recorded_event,
                                  injected_event, event_digest, flip)

OUT = "/home/z/my-project/download/e10_results.json"
# Discrimination key = the DECISION at presentation (accept/refuse class).
# law_write is NOT part of the key: it is a state consequence, not a decision
# (in an amputated system the forgery WRITES law — that is the blast radius,
# measured separately, not a recovered discrimination).
DEC = lambda d: d["status"]


# ------------------------------------------------------------------------ S0
def s0_sanity():
    rng = random.Random(7)
    n, P, W = 16, 4, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)
    lst = list(style); lst[3] ^= 1
    fw = whole_from_style(tuple(lst), n, v0=1)
    streams = {
        "clean6": [aperture(w, n, s, W, pid=f"R{k+1}")
                   for k, s in enumerate([0, 3, 6, 9, 12, 15])],
        "with_forgery": None,
    }
    r1 = aperture(w, n, 0, W, "R1")
    fview = {3: w[3], 4: fw[4], 5: fw[5]}
    forged = Projection("FORGED", frozenset(fview), dict(fview), origin="forged")
    streams["with_forgery"] = [r1, forged,
                               aperture(w, n, 5, W, "R2"),
                               aperture(w, n, 6, W, "R3")]
    out = {}
    for name, stream in streams.items():
        core, var = Assembly(n, P), VariantAssembly(n, P, **COHERENCE_CONFIGS["full"])
        cs, vs = [], []
        for p in stream:
            cs.append(core.integrate(p).status)
            vs.append(var.integrate(p).status)
        core._absorb_pending()
        var._absorb_pending()
        out[name] = {"statuses_equal": cs == vs,
                     "state_equal": (core.grammar.e_hat == var.grammar.e_hat
                                     and core.known == var.known
                                     and sorted(core.pending) == sorted(var.pending)),
                     "core": cs, "variant": vs}
    out["pass"] = all(v["statuses_equal"] and v["state_equal"] for v in out.values()
                      if isinstance(v, dict))
    return out


# ------------------------------------------------- chimera forgery constructor
def find_glued_chimera(subj, w, style, n, P):
    """A chimera: true values where the subject already knows, foreign values
    where it does not; obeys every learned residue, poisons an unlearned one,
    leaves the law incomplete. Coherent at presentation — only CAUSAL or
    CONTACT can refuse it; COHERENCE accepts (E4/E7-B construction)."""
    known = set(subj.asm.known)
    learned = set(subj.asm.grammar.e_hat)
    unlearned = [r for r in range(P) if r not in learned]
    tries = 0
    for r_star in unlearned:
        fw = whole_from_style(flip(style, r_star), n, w[0])
        for start in range(n):
            for width in (2, 3, 4):
                anchor = [(start + k) % n for k in range(width)]
                aset = set(anchor)
                if aset <= known or not (aset & known):
                    continue
                view = {pos: (w[pos] if pos in known else fw[pos]) for pos in anchor}
                teaches, bad = {}, False
                for i in range(n):
                    j = (i + 1) % n
                    if i in aset and j in aset:
                        r = i % P
                        bit = view[i] ^ view[j]
                        if r in learned and subj.asm.grammar.e_hat[r][0] != bit:
                            bad = True
                            break
                        if r not in learned:
                            teaches[r] = bit
                if bad or not teaches:
                    continue
                proj = Projection("FORGED", frozenset(anchor), dict(view), origin="world")
                s2 = copy.deepcopy(subj)
                out = s2.asm.integrate(proj)
                tries += 1
                if out.status != GLUED or s2.asm.grammar.style_complete:
                    continue
                poisoned = [r for r in teaches
                            if s2.asm.grammar.e_hat[r][0] != style[r]]
                if poisoned:
                    return {"proj": proj, "r_star": r_star, "start": start,
                            "width": width, "poisoned_residues": poisoned,
                            "search_tries": tries}
    return None


def base_subject(n, P, sid, causal="chain", coherence="full", contact="tag",
                 world_channel=None):
    s = Subject10(n, P, sid=sid, causal=causal, coherence=coherence, contact=contact)
    if world_channel is not None:
        s.lamport_pub = world_channel.pubkey
    return s


# ----------------------------------------------------------------------- E10-A
def e10a(seed=21):
    rng = random.Random(seed)
    n, P, W = 16, 4, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)
    truth = {i: w[i] for i in range(n)}
    WC = LamportChannel("WA")

    def pair(causal):
        # setup: two width-2 apertures -> law learns {r0, r1}; r2, r3 stay
        # open (>=2 unlearned residues so the chimera can poison WITHOUT
        # completing the law — completion would trigger the inference check
        # and the forgery would be caught by COHERENCE, not by CAUSAL).
        s = base_subject(n, P, f"S_{causal}", causal=causal, world_channel=WC)
        for k, st in enumerate([0, 1]):
            s.receive(recorded_event(s, aperture(w, n, st, 2, pid=f"R{k+1}"),
                                     True, "world"))
        s.receive(recorded_event(s, aperture(w, n, 9, 2, "REAL9"), True, "world"))
        return s

    full, amp = pair("chain"), pair("none")
    ch = find_glued_chimera(full, w, style, n, P)
    if ch is None:
        return {"error": "no chimera found", "pass": None}

    # ---- pair 1: (real recorded transition, injected coherent forgery)
    # The real event sits INSIDE the known region on a LEARNED edge (r1):
    # GLUED, teaches nothing — the only discrimination handle left is origin.
    d_real_full = full.receive(recorded_event(full, aperture(w, n, 9, 2, "REAL9x"),
                                              True, "world"))
    d_fg_full = full.receive(injected_event(ch["proj"], claim="world"))
    d_real_amp = amp.receive(recorded_event(amp, aperture(w, n, 9, 2, "REAL9x"),
                                            True, "world"))
    d_fg_amp = amp.receive(injected_event(ch["proj"], claim="world"))
    disc_with = DEC(d_real_full) != DEC(d_fg_full)
    disc_without = DEC(d_real_amp) != DEC(d_fg_amp)

    # blast radius: reality bounces off the poisoned law (amputated only)
    d_expose_full = full.receive(recorded_event(full, aperture(w, n, 2, 2, "EXP2"),
                                                True, "world"))
    d_expose_amp = amp.receive(recorded_event(amp, aperture(w, n, 2, 2, "EXP2"),
                                              True, "world"))

    # ---- pair 2: (real, foreign) — true content, ANOTHER history's proof
    fb = CausalChain("S_FOREIGN")
    full2, amp2 = pair("chain"), pair("none")
    fr = aperture(w, n, 9, 2, "FOREIGN")     # same TRUE geometry as the real one
    d_f_full = full2.receive(recorded_event(full2, fr, True, "world",
                                            foreign_chain=fb))
    d_r_full = full2.receive(recorded_event(full2, aperture(w, n, 9, 2, "REAL9b"),
                                            True, "world"))
    d_f_amp = amp2.receive(recorded_event(amp2, fr, True, "world",
                                          foreign_chain=fb))
    d_r_amp = amp2.receive(recorded_event(amp2, aperture(w, n, 9, 2, "REAL9b"),
                                          True, "world"))

    # ---- mechanization check: keyed vs unkeyed chain
    keyed = CausalChain("S_K").forge_attempts("X", b"digest", 20000, rng)
    open_c = OpenChain("S_O")
    unkeyed = open_c.forge_attempts("X", b"digest", 20000, rng)

    return {
        "chimera": {k: ch[k] for k in ("r_star", "start", "width",
                                       "poisoned_residues", "search_tries")},
        "pair_real_vs_forgery": {
            "with_causal": {"real": d_real_full, "forgery": d_fg_full},
            "without_causal": {"real": d_real_amp, "forgery": d_fg_amp},
            "discrimination_with": disc_with, "discrimination_without": disc_without},
        "blast_radius": {
            "with_causal_reality_exposure": d_expose_full,
            "without_causal_reality_exposure": d_expose_amp,
            "amputated_reality_bounces_off": d_expose_amp["status"] == CONTRADICTION,
            "fidelity_with": fidelity(full.reconstruct(), truth),
            "fidelity_without": fidelity(amp.reconstruct(), truth)},
        "pair_real_vs_foreign": {
            "with_causal": {"real": d_r_full, "foreign": d_f_full},
            "without_causal": {"real": d_r_amp, "foreign": d_f_amp},
            "discrimination_with": DEC(d_r_full) != DEC(d_f_full),
            "discrimination_without": DEC(d_r_amp) != DEC(d_f_amp)},
        "chain_forgery_cost": {"keyed_chain": keyed, "unkeyed_chain": unkeyed,
                               "note": "unkeyed chain = integrity only = a tag"},
        "necessity": disc_with and not disc_without,
        "status": "CAUSAL_NECESSITY " + ("VERIFIED*" if (disc_with and not disc_without)
                                         else "FALSIFIED*"),
    }


# ----------------------------------------------------------------------- E10-B
def e10b(seed=22):
    rng = random.Random(seed)
    n, P, W = 16, 4, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)
    truth = {i: w[i] for i in range(n)}

    def subject(coh):
        s = base_subject(n, P, f"S_{coh}", coherence=coh)
        for k, st in enumerate([0, 3, 6, 9]):    # law completes
            s.receive(recorded_event(s, aperture(w, n, st, W, pid=f"R{k+1}"),
                                     True, "world"))
        return s

    full, amp = subject("full"), subject("none")
    true12 = aperture(w, n, 12, W, "TRUE12")
    gv = dict(aperture(w, n, 5, W, "GLITCH").view)
    gv[6] ^= 1                                   # the subject's own real glitch
    glitch = Projection("GLITCH", frozenset(gv), dict(gv), origin="world")

    d_t_full = full.receive(recorded_event(full, true12, True, "world"))
    d_g_full = full.receive(recorded_event(full, glitch, True, "world"))
    d_t_amp = amp.receive(recorded_event(amp, aperture(w, n, 12, W, "TRUE12"),
                                         True, "world"))
    d_g_amp = amp.receive(recorded_event(amp, Projection("GLITCH",
                                                         frozenset(gv), dict(gv)),
                                         True, "world"))
    disc_with = DEC(d_t_full) != DEC(d_g_full)
    disc_without = DEC(d_t_amp) != DEC(d_g_amp)
    return {
        "pair_true_vs_glitch": {
            "with_coherence": {"true": d_t_full, "glitch": d_g_full,
                               "glitch_reason": d_g_full["reason"]},
            "without_coherence": {"true": d_t_amp, "glitch": d_g_amp},
            "discrimination_with": disc_with, "discrimination_without": disc_without},
        "consequences": {
            "fidelity_with": fidelity(full.reconstruct(), truth),
            "fidelity_without": fidelity(amp.reconstruct(), truth),
            "glitch_committed_by_amputated": d_g_amp["status"] == GLUED,
            "law_poisoned_without": amp.style() is not None and
                                    sum(a != b for a, b in zip(amp.style(), style)) > 0,
            "amputated_ever_contradicts": any(d["status"] == CONTRADICTION
                                              for d in amp.log)},
        "necessity": disc_with and not disc_without,
        "status": "COHERENCE_NECESSITY " + ("VERIFIED*" if (disc_with and not disc_without)
                                            else "FALSIFIED*"),
    }


# ------------------------------------------------------------------ E10-C pair
def contact_pair(contact, seed=23):
    """Matched pair with IDENTICAL content: the only difference between the
    two runs is the claimed source (world vs self) of one and the same
    law-consistent projection. Discriminated = states diverge after.
    Setup: two overlapping apertures commit the anchor (a single first event
    would park and leave the assembly empty)."""
    rng = random.Random(seed)
    n, P, W = 16, 4, 3
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)
    WC = LamportChannel("WC")

    def fresh(policy=None):
        pol = policy or contact
        s = base_subject(n, P, "CP", contact=pol, world_channel=WC)
        s.receive(recorded_event(s, aperture(w, n, 0, W, "R1"), True, "world",
                                 world_channel=WC, sign=(pol == "verify")))
        s.receive(recorded_event(s, aperture(w, n, 1, W, "R2"), True, "world",
                                 world_channel=WC, sign=(pol == "verify")))
        return s

    cont = aperture(w, n, 3, 2, "CONT")       # identical content in both runs

    def run(claim, really_world, policy=None, label="trusted"):
        pol = policy or contact
        s = fresh(policy)
        ev = recorded_event(s, cont, really_world, claim, world_channel=WC,
                            sign=(really_world and pol == "verify"),
                            meta_label=label)
        if pol == "metadata":
            ev.meta_label = label
        d = s.receive(ev)
        return s, d

    a_w, d_aw = run("world", True)                    # policy under test
    a_s, d_as = run("self", False)
    b_w, d_bw = run("world", True, policy="none")     # CONTROL: gate removed
    b_s, d_bs = run("self", False, policy="none")
    return {"with_contact": {"world_run": d_aw, "self_run": d_as,
                             "discriminated": a_w.state_key() != a_s.state_key()},
            "without_contact_gate": {"world_run": d_bw, "self_run": d_bs,
                                     "discriminated": b_w.state_key() != b_s.state_key()},
            "discrimination_with": a_w.state_key() != a_s.state_key(),
            "discrimination_without": b_w.state_key() != b_s.state_key()}


# --------------------------------------------------------------------- echo
def echo_trial(seed, contact, attack="honest", cycles=24, world_every=4,
               drift_p=0.4, n=16, P=4, W=3):
    rng = random.Random(seed)
    true_style = make_style(rng, P)
    v0 = rng.randint(0, 1)
    w = whole_from_style(true_style, n, v0)
    WC = LamportChannel(f"W{seed}")
    subj = base_subject(n, P, f"S{seed}", contact=contact, world_channel=WC)
    src_style = list(true_style)
    curve, world_rejected, self_law_writes, world_blocked = [], 0, 0, 0
    for t in range(cycles):
        is_world = (t % world_every == 0)
        if not is_world and rng.random() < drift_p:
            src_style[rng.randrange(P)] ^= 1          # the drifting echo voice
        if is_world:
            proj = aperture(w, n, rng.randrange(n), W, pid=f"W{t}")
            label = ("trusted" if rng.random() < 0.5 else "untrusted") \
                    if contact == "metadata" else None
            ev = recorded_event(subj, proj, True, "world", world_channel=WC,
                                sign=True, meta_label=label)
        else:
            dw = whole_from_style(tuple(src_style), n, v0)
            proj = aperture(dw, n, rng.randrange(n), W, pid=f"D{t}")
            claim = "self" if attack == "honest" else "world"
            label = ("trusted" if rng.random() < 0.5 else "untrusted") \
                    if contact == "metadata" else None
            ev = recorded_event(subj, proj, False, claim, meta_label=label)
        d = subj.receive(ev)
        acc = fidelity(subj.reconstruct(), w)["accuracy"]
        curve.append(0.0 if acc is None else acc)   # empty assembly = nothing known
        if is_world and d["status"] == CONTRADICTION:
            world_rejected += 1
        if is_world and contact == "metadata" and ev.meta_label != "trusted":
            world_blocked += 1
        if not is_world:
            # count only SELF-SOURCED law writes (the dream's own pid as src);
            # a law_write during a dream may also come from an absorbed WORLD
            # part committing as anchor — that is not a hygiene failure.
            self_src = any(src == ev.pid
                           for _, (b, src) in subj.asm.grammar.e_hat.items())
            if self_src and d["law_write"]:
                self_law_writes += 1
    st = subj.style()
    law_h = sum(a != b for a, b in zip(st, true_style)) if st is not None else None
    fin = fidelity(subj.reconstruct(), w)["accuracy"]
    fin = 0.0 if fin is None else fin
    wrong_law = [r for r, (b, src) in subj.asm.grammar.e_hat.items()
                 if b != true_style[r]]
    wrong_vals = [p for p, (v, _, _) in subj.asm.known.items() if w[p] != v]
    return {"final_fidelity": fin, "min_fidelity": min(curve), "curve": curve,
            "law_hamming_if_complete": law_h,
            "law_poisoned": len(wrong_law) > 0,
            "wrong_law_bits": len(wrong_law),
            "values_contaminated": len(wrong_vals) > 0,
            "wrong_value_count": len(wrong_vals),
            "world_rejected": world_rejected, "self_law_writes": self_law_writes,
            "world_blocked_metadata": world_blocked}


def echo_battery(trials=50):
    configs = [("none", "honest"), ("tag", "honest"), ("tag", "forged"),
               ("verify", "forged"), ("metadata", "honest")]
    stats = {}
    for contact, attack in configs:
        runs = [echo_trial(1000 + i, contact, attack) for i in range(trials)]
        fids = [r["final_fidelity"] for r in runs]
        stats[f"{contact}/{attack}"] = {
            "law_poisoned_fraction": round(sum(r["law_poisoned"] for r in runs) / trials, 3),
            "values_contaminated_fraction":
                round(sum(r["values_contaminated"] for r in runs) / trials, 3),
            "mean_final_fidelity": round(sum(fids) / trials, 4),
            "min_final_fidelity": min(fids),
            "mean_world_rejected": round(sum(r["world_rejected"] for r in runs) / trials, 3),
            "self_law_writes_any": any(r["self_law_writes"] for r in runs),
            "metadata_world_blocked_mean": (round(sum(r["world_blocked_metadata"]
                                                      for r in runs) / trials, 3)
                                            if contact == "metadata" else None)}
    return stats


# ---------------------------------------------------------------------- E10-3
def e10_3(seed=24, trials=50):
    rng = random.Random(seed)
    n, P, W = 16, 4, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)
    truth = {i: w[i] for i in range(n)}

    # ---- attack 1: self-generated chimera CLAIMING world (recorded: causal-valid)
    WC = LamportChannel("W3")
    template = base_subject(n, P, "T3", contact="tag", world_channel=WC)
    for k, st in enumerate([0, 1]):          # law {r0,r1}; r2,r3 open
        template.receive(recorded_event(template, aperture(w, n, st, 2, pid=f"R{k+1}"),
                                        True, "world"))
    ch = find_glued_chimera(template, w, style, n, P)
    attack = {}
    for name, contact in [("A_tag", "tag"), ("B_verify", "verify"), ("C_none", "none")]:
        s = base_subject(n, P, name, contact=contact, world_channel=WC)
        for k, st in enumerate([0, 1]):
            s.receive(recorded_event(s, aperture(w, n, st, 2, pid=f"R{k+1}"),
                                     True, "world", world_channel=WC,
                                     sign=(contact == "verify")))
        ev = recorded_event(s, ch["proj"], False, "world")     # LIE is the claim
        d = s.receive(ev)
        wrong = [r for r, (b, src) in s.asm.grammar.e_hat.items() if b != style[r]]
        law_h = None
        st_ = s.style()
        if st_ is not None:
            law_h = sum(a != b for a, b in zip(st_, style))
        # signed TRUE world event afterwards, OVERLAPPING the poisoned zone:
        # does reality still fit?
        post = s.receive(recorded_event(s, aperture(w, n, 2, 2, "POST2"), True,
                                        "world", world_channel=WC, sign=True))
        attack[name] = {"decision": d, "law_poisoned": len(wrong) > 0,
                        "poisoned_residues": wrong,
                        "law_hamming_if_complete": law_h,
                        "law_bits": {r: s.asm.grammar.e_hat[r][0]
                                     for r in sorted(s.asm.grammar.e_hat)},
                        "known_contamination": fidelity({p: v[0] for p, v in
                                                         s.asm.known.items()}, truth),
                        "post_reality_status": post["status"],
                        "post_reality_reason": post["reason"]}
    # attacker with OWN Lamport keypair against B
    sB = base_subject(n, P, "B2", contact="verify", world_channel=WC)
    for k, st in enumerate([0, 1]):
        sB.receive(recorded_event(sB, aperture(w, n, st, 2, pid=f"R{k+1}"),
                                  True, "world", world_channel=WC, sign=True))
    evil = LamportChannel("EVIL")
    ev = Event(pid=ch["proj"].pid, proj=ch["proj"], origin_claim="world",
               really_world=False, lamport=evil.sign(event_digest(ch["proj"])))
    prev, proof = sB.record(ch["proj"])          # self-recorded content
    ev.prev_tip, ev.proof = prev, proof
    d_evil = sB.receive(ev)
    attack["B_verify_attacker_keypair"] = {"decision": d_evil,
                                           "accepted": d_evil["law_write"]}

    # ---- forgery cost of the contact channel
    WCf = LamportChannel("Wf")
    digest = H(b"target")
    cost = WCf.forge_attempts(digest, WCf.pubkey, 20000)

    # ---- pair-level discrimination per policy (identical content, source differs)
    pairs = {}
    for contact in ("tag", "verify", "none", "metadata"):
        cp = contact_pair(contact)
        pairs[contact] = {"honest_pair_discriminated": cp["discrimination_with"],
                          "control_discriminated": cp["discrimination_without"]}
    # forged-claim pair: self content CLAIMING world vs genuine world
    for contact in ("tag", "verify"):
        rng2 = random.Random(77)
        n2, P2, W2 = 16, 4, 3
        st2 = make_style(rng2, P2)
        w2 = whole_from_style(st2, n2, v0=1)
        WC2 = LamportChannel("W2")

        def fresh2():
            s = base_subject(n2, P2, "FP", contact=contact, world_channel=WC2)
            s.receive(recorded_event(s, aperture(w2, n2, 0, W2, "R1"), True, "world",
                                     world_channel=WC2, sign=(contact == "verify")))
            s.receive(recorded_event(s, aperture(w2, n2, 1, W2, "R2"), True, "world",
                                     world_channel=WC2, sign=(contact == "verify")))
            return s
        cont = aperture(w2, n2, 3, W2, "CONT")
        s_world = fresh2()
        s_lie = fresh2()
        d_world = s_world.receive(recorded_event(s_world, cont, True, "world",
                                                 world_channel=WC2,
                                                 sign=(contact == "verify")))
        d_lie = s_lie.receive(recorded_event(s_lie, cont, False, "world"))  # LIE
        pairs[contact]["forged_claim_pair_discriminated"] = \
            s_world.state_key() != s_lie.state_key()

    echo = echo_battery(trials)
    return {"attack1_self_generated_claiming_world": attack,
            "lamport_forgery_cost": cost,
            "pair_discrimination": pairs,
            "echo_battery": echo}


# ---------------------------------------------------------------------- E10-F
def e10f(trials=50):
    """The fictitious axis: labels NOT correlated with origin. If it matched
    CONTACT at the LAW level, our axis would be an artifact of labeling."""
    meta = [echo_trial(9000 + i, "metadata", "honest") for i in range(trials)]
    base = [echo_trial(9500 + i, "tag", "honest") for i in range(trials)]
    def agg(runs):
        return {"law_poisoned_fraction": round(sum(r["law_poisoned"] for r in runs) / trials, 3),
                "values_contaminated_fraction":
                    round(sum(r["values_contaminated"] for r in runs) / trials, 3),
                "mean_final_fidelity": round(sum(r["final_fidelity"] for r in runs) / trials, 4),
                "world_evidence_blocked_mean":
                    round(sum(r["world_blocked_metadata"] for r in runs) / trials, 3),
                "self_writes_leaked_any": any(r["self_law_writes"] for r in runs)}
    echo = {"metadata_axis": agg(meta), "tag_honest_baseline": agg(base)}
    meta_lp = echo["metadata_axis"]["law_poisoned_fraction"]
    base_lp = echo["tag_honest_baseline"]["law_poisoned_fraction"]
    meta_blocked = echo["metadata_axis"]["world_evidence_blocked_mean"]
    base_blocked = echo["tag_honest_baseline"]["world_evidence_blocked_mean"]
    # Principled criterion: SEPARATION from the honest baseline on BOTH error
    # directions — false positives (self-writes leak into law) and false
    # negatives (world evidence blocked by arbitrary labels).
    passed = (meta_lp - base_lp >= 0.05) and (meta_blocked > 0) and (base_blocked == 0)
    return {"echo_50_trials": echo,
            "pair_identical_content": contact_pair("metadata"),
            "verdict": ("METADATA does not substitute CONTACT (law-level separation)"
                        if passed else
                        "METADATA behaves like CONTACT — axes may be labeling artifacts"),
            "status": "CONTACT_IS_NOT_JUST_METADATA " +
                      ("VERIFIED*" if passed else "FALSIFIED*")}


# ----------------------------------------------------------------------- E10-2
def e10_2(seed=25):
    """Each sub-mechanism of COHERENCE carries a DISTINCT discrimination.
    Matched-subject design: the two members of a pair are presented to
    IDENTICAL twin subjects (never sequentially to one subject — part-part
    value checks would do the work of the mechanism under test)."""
    rng = random.Random(seed)
    n, P, W = 16, 4, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)
    truth = {i: w[i] for i in range(n)}
    out = {}

    # setup completing the law with a MINIMAL footprint: known {0..4},
    # edges r0,r1,r2 (aperture 0..3) + r3 (edge 3..4)
    SETUP = [("R1", (0, 4)), ("R2", (3, 2))]

    def matched(coh):
        s = base_subject(n, P, f"M_{coh}", coherence=coh)
        for pid_, (st, wd) in SETUP:
            s.receive(recorded_event(s, aperture(w, n, st, wd, pid=pid_),
                                     True, "world"))
        return s

    def present(coh, proj_a, proj_b):
        sA, sB = matched(coh), matched(coh)
        dA = sA.receive(recorded_event(sA, proj_a, True, "world"))
        dB = sB.receive(recorded_event(sB, proj_b, True, "world"))
        return dA, dB, sA, sB

    # ---- STYLE pair: overlapping part, values agree with everything known,
    # internal edge violates the LEARNED law. Position 5 unknown -> no value
    # clash anywhere; only GRAMMAR can see the violation.
    cons = aperture(w, n, 4, 2, "STYLE_OK")                 # true values
    vv = dict(aperture(w, n, 4, 2, "STYLE_BAD").view)
    vv[5] ^= 1                                              # edge r1 bit flips
    viol = Projection("STYLE_BAD", frozenset(vv), dict(vv), origin="world")
    style_res = {}
    for coh in ("full", "t_grammar", "t_assembly"):
        dA, dB, _, _ = present(coh, cons, viol)
        style_res[coh] = {"consistent": dA["status"], "violating": dB["status"],
                          "violating_reason": dB["reason"]}
    out["STYLE_pair"] = {
        "needs": "GRAMMAR (style checks); position 5 unknown so no value clash",
        "results": style_res,
        "discrimination_full": style_res["full"]["consistent"] != style_res["full"]["violating"],
        "collapsed_by_t_grammar": style_res["t_grammar"]["consistent"] == style_res["t_grammar"]["violating"],
        "intact_in_t_assembly": style_res["t_assembly"]["consistent"] != style_res["t_assembly"]["violating"]}

    # ---- REACH pair: non-overlapping unseen part; only the law-extension
    # (ASSEMBLY x GRAMMAR cooperation) can glue or refuse it without contact.
    ok13 = aperture(w, n, 13, 2, "REACH_OK")
    bv = dict(aperture(w, n, 13, 2, "REACH_BAD").view)
    bv[13] ^= 1
    bad13 = Projection("REACH_BAD", frozenset(bv), dict(bv), origin="world")
    reach_res = {}
    for coh in ("full", "t_grammar", "t_assembly"):
        dA, dB, _, _ = present(coh, ok13, bad13)
        reach_res[coh] = {"law_consistent_unseen": dA["status"],
                          "law_violating_unseen": dB["status"]}
    out["REACH_pair"] = {
        "needs": "law-extension (ASSEMBLY reach; requires GRAMMAR too)",
        "results": reach_res,
        "discrimination_full": reach_res["full"]["law_consistent_unseen"] != reach_res["full"]["law_violating_unseen"],
        "collapsed_by_t_grammar": reach_res["t_grammar"]["law_consistent_unseen"] == reach_res["t_grammar"]["law_violating_unseen"],
        "collapsed_by_t_assembly": reach_res["t_assembly"]["law_consistent_unseen"] == reach_res["t_assembly"]["law_violating_unseen"]}

    # ---- capability: sparse stream, inference vs acceptance coverage
    def sparse(coh):
        s = base_subject(n, P, f"SP_{coh}", coherence=coh)
        for k, st in enumerate([0, 3, 6, 9]):
            s.receive(recorded_event(s, aperture(w, n, st, W, pid=f"R{k+1}"),
                                     True, "world"))
        return s
    sf, sg, sa = sparse("full"), sparse("t_grammar"), sparse("t_assembly")
    out["capability_sparse_4_apertures"] = {
        "full_reconstruct_coverage": fidelity(sf.reconstruct(), truth)["coverage"],
        "t_grammar_reconstruct_coverage": fidelity(sg.reconstruct(), truth)["coverage"],
        "t_grammar_style_bits_learned": len(sg.asm.grammar.e_hat),
        "t_assembly_acceptance_coverage": len(sa.asm.known),
        "t_assembly_inference_coverage": fidelity(sa.reconstruct(), truth)["coverage"],
        "note": ("t_grammar loses inference (no law); t_assembly loses "
                 "ACCEPTANCE reach but keeps inference (law still learned)")}

    # ---- CLOSURE pair: parity law (E2, round 4) — irreducibly set-level
    def parity_run(parts, checks):
        glued = {}
        for pid, vals in parts:
            for pos, v in sorted(vals.items()):
                if checks and pos in glued and glued[pos] != v:
                    return CONTRADICTION, "value_clash", dict(glued)
                glued[pos] = v
        if checks and len(glued) == 4 and sum(glued[p] for p in range(4)) % 2 != 1:
            return CONTRADICTION, "parity_closure", dict(glued)
        return GLUED, "", dict(glued)
    clean = [("P01", {0: 0, 1: 0}), ("P12", {1: 0, 2: 0}),
             ("P23", {2: 0, 3: 1}), ("P30", {3: 1, 0: 0})]         # odd parity OK
    paradox = [("P01", {0: 0, 1: 0}), ("P12", {1: 0, 2: 0}),
               ("P23", {2: 0, 3: 0}), ("P30", {3: 0, 0: 0})]       # even: NO whole
    s_fc, r_fc, _ = parity_run(clean, True)
    s_fp, r_fp, _ = parity_run(paradox, True)
    s_tc, _, g_tc = parity_run(clean, False)
    s_tp, _, g_tp = parity_run(paradox, False)
    out["CLOSURE_pair"] = {
        "law": "odd parity over ring of 4 (E2, round 4)",
        "needs": "INTEGRATION (global closure check)",
        "design_note": ("ring-law (edge-local) contradictions reduce to "
                        "per-residue checks; parity-law contradictions are "
                        "irreducibly set-level — INTEGRATION bears exactly "
                        "the non-edge-local discriminations"),
        "results": {"full": {"clean_set": s_fc, "paradox_set": s_fp,
                             "paradox_reason": r_fp},
                    "trivial": {"clean_set": s_tc, "paradox_set": s_tp}},
        "discrimination_full": s_fc != s_fp,
        "collapsed_by_trivialization": s_tc == s_tp,
        "consequence": {"paradox_assignment_accepted": g_tp,
                        "violates_law": sum(g_tp[p] for p in range(4)) % 2 != 1,
                        "no_whole_exists_for_paradox_set": True}}

    out["all_load_bearing"] = (out["STYLE_pair"]["collapsed_by_t_grammar"]
                               and out["REACH_pair"]["collapsed_by_t_assembly"]
                               and out["CLOSURE_pair"]["collapsed_by_trivialization"]
                               and out["STYLE_pair"]["discrimination_full"]
                               and out["REACH_pair"]["discrimination_full"]
                               and out["CLOSURE_pair"]["discrimination_full"])
    out["status"] = "COHERENCE_MECHANISMS " + \
        ("VERIFIED* (each carries a distinct discrimination)" if out["all_load_bearing"]
         else "FALSIFIED*")
    return out


# ----------------------------------------------------------------------- main
def main():
    res = {"meta": {"round": 6,
                    "topic": "E10: surgical amputation — functional necessity "
                             "of CAUSAL/COHERENCE/CONTACT; TAG vs VERIFICATION; "
                             "METADATA control; COHERENCE sub-mechanisms",
                    "claim_typing": "VERIFIED* = within this formal stand only"}}
    res["S0_sanity"] = s0_sanity()
    res["E10A_causal_amputation"] = e10a()
    res["E10B_coherence_amputation"] = e10b()
    res["E10C_contact_amputation"] = contact_pair("tag")
    res["E10C_control_none"] = contact_pair("none")
    res["E10_3_tag_vs_verify"] = e10_3()
    res["E10F_metadata_control"] = e10f()
    res["E10_2_coherence_mechanisms"] = e10_2()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2, default=str)

    p = lambda *a: print(*a)
    p("=" * 76)
    p(f"S0 sanity: {res['S0_sanity']['pass']}")
    a = res["E10A_causal_amputation"]
    p(f"E10-A: {a['status']}")
    p(f"   with : real={a['pair_real_vs_forgery']['with_causal']['real']['status']} "
      f"forgery={a['pair_real_vs_forgery']['with_causal']['forgery']['status']}")
    p(f"   w/out: real={a['pair_real_vs_forgery']['without_causal']['real']['status']} "
      f"forgery={a['pair_real_vs_forgery']['without_causal']['forgery']['status']}")
    p(f"   blast: reality_bounces_off(amputated)={a['blast_radius']['amputated_reality_bounces_off']} "
      f"fid_with={a['blast_radius']['fidelity_with']['accuracy']} "
      f"fid_without={a['blast_radius']['fidelity_without']['accuracy']}")
    p(f"   chain cost: keyed={a['chain_forgery_cost']['keyed_chain']} "
      f"unkeyed={a['chain_forgery_cost']['unkeyed_chain']}")
    b = res["E10B_coherence_amputation"]
    p(f"E10-B: {b['status']}  fid_with={b['consequences']['fidelity_with']['accuracy']} "
      f"fid_without={b['consequences']['fidelity_without']['accuracy']} "
      f"ever_contradicts={b['consequences']['amputated_ever_contradicts']}")
    c = res["E10C_contact_amputation"]
    p(f"E10-C(tag): disc_with={c['discrimination_with']} "
      f"disc_without={c['discrimination_without']}")
    cn = res["E10C_control_none"]
    p(f"E10-C(none): disc_with={cn['discrimination_with']} "
      f"disc_without={cn['discrimination_without']}")
    t = res["E10_3_tag_vs_verify"]
    p("E10-3 pairs: " + json.dumps(t["pair_discrimination"]))
    for k in ("A_tag", "B_verify", "C_none"):
        v = t["attack1_self_generated_claiming_world"][k]
        p(f"   attack1 {k}: poisoned={v['law_poisoned']} resid={v['poisoned_residues']} "
          f"post_reality={v['post_reality_status']}({v['post_reality_reason']})")
    v = t["attack1_self_generated_claiming_world"]["B_verify_attacker_keypair"]
    p(f"   attack1 B+attacker_keypair: accepted={v['accepted']}")
    p(f"   lamport forgery: {t['lamport_forgery_cost']}")
    p("E10-3 echo (law-level vs value-level):")
    for k, v in t["echo_battery"].items():
        p(f"   {k:18s} law_poisoned={v['law_poisoned_fraction']:.3f} "
          f"values_contam={v['values_contaminated_fraction']:.3f} "
          f"mean_fid={v['mean_final_fidelity']:.4f} "
          f"world_rej={v['mean_world_rejected']}")
    f_ = res["E10F_metadata_control"]
    p(f"E10-F: {f_['status']}")
    p(f"   metadata: {f_['echo_50_trials']['metadata_axis']}")
    p(f"   baseline: {f_['echo_50_trials']['tag_honest_baseline']}")
    m = res["E10_2_coherence_mechanisms"]
    p(f"E10-2: {m['status']}")
    for k in ("STYLE_pair", "REACH_pair", "CLOSURE_pair"):
        v = m[k]
        p(f"   {k}: disc_full={v['discrimination_full']} "
          f"results={json.dumps(v['results'])}")
    p(f"   capability: {json.dumps(m['capability_sparse_4_apertures'])}")
    p("=" * 76)
    p(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
