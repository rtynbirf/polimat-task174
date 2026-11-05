#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HOLOGRAPHIC BATTERY — round 4: experiments E1..E8.

E1  reconstruction monotonicity + holographic inference (part+law->whole) + ablation
E2  pairwise consistency vs global belonging (the set-level counterexample)
E3  defense grows with learning: unjudgeable -> reject at contact -> reject
    without contact; positive control (own unseen part accepted by law-contact)
E4  forgery: (a) law-complete forgery degenerates into truth;
    (b) early poisoning: forged anchor, reality bounces, minimal repair
E5  fork: two wholes, one stream -> cluster-relative belonging
E6  amnesia: total wipe -> re-identification of the whole from present projections
E7  separation from M2': (A) pedigreed nonsense, (B) coherent forgery +
    multi-candidate blame resolved by next contact, (C) echo chamber
E8  the hermeneutic loop: informed vs random attention (part->whole->part->...)
"""
import os
import sys
import json
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from holographic_core import (GLUED, CONTRADICTION, DISCONNECTED,  # noqa: E402
                              make_style, whole_from_style, Projection, aperture,
                              propagate, fidelity, Assembly, rebuild,
                              minimal_repair_sets)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = "/home/z/my-project/download/holographic_results.json"
STARTS6 = [0, 3, 6, 9, 12, 15]   # overlap-chained apertures (width 4, step 3)


# --------------------------------------------------------------------------- E1
def e1(seed: int = 7):
    rng = random.Random(seed)
    n, P, W = 16, 4, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=rng.randint(0, 1))
    asm = Assembly(n, P)
    traj = []
    for k, s in enumerate(STARTS6):
        p = aperture(w, n, s, W, pid=f"A{k+1}")
        out = asm.integrate(p)
        rec = asm.reconstruct()
        traj.append({"after": p.pid, "status": out.status,
                     "observed": len(asm.known),
                     "reconstruction": fidelity(rec, w),
                     "style_complete": asm.grammar.style_complete,
                     "full_inference": asm.infer_full() is not None})
    # ablation: same stream, reconstruction WITHOUT the law (glued values only)
    traj_abl = []
    asm2 = Assembly(n, P)
    for k, s in enumerate(STARTS6):
        asm2.integrate(aperture(w, n, s, W, pid=f"A{k+1}"))
        rec = {pos: v for pos, (v, _, _) in asm2.known.items()}
        traj_abl.append({"after": f"A{k+1}", "observed": len(asm2.known),
                         "reconstruction": fidelity(rec, w)})
    return {"true_style": style,
            "trajectory_with_law": traj,
            "trajectory_ablation_no_law": traj_abl,
            "relations_carried_per_projection": W - 1,
            "conclusion": ("2 projections (7/16 positions observed) + learned law "
                           "force the whole at 16/16; without the law the whole "
                           "appears only after full positional coverage")}


# --------------------------------------------------------------------------- E2
def e2():
    views = [
        Projection("P01", frozenset({0, 1}), {0: 0, 1: 0}),
        Projection("P12", frozenset({1, 2}), {1: 0, 2: 0}),
        Projection("P23", frozenset({2, 3}), {2: 0, 3: 0}),
        Projection("P30", frozenset({3, 0}), {3: 0, 0: 0}),
    ]
    all_assignments = [(a, b, c, d) for a in (0, 1) for b in (0, 1)
                       for c in (0, 1) for d in (0, 1)]
    parity_ok = lambda t: sum(t) % 2 == 1          # the whole's law: odd parity
    local = {v.pid: any(all(a[pos] == val for pos, val in v.view.items())
                        for a in all_assignments if parity_ok(a))
             for v in views}
    pair_ok = all(views[i].view[p] == views[j].view[p]
                  for i in range(4) for j in range(i + 1, 4)
                  for p in (views[i].anchor & views[j].anchor))
    glued = {}
    for v in views:
        glued.update(v.view)
    global_ok = parity_ok(tuple(glued[p] for p in range(4)))

    def whole_exists(g):
        free = [p for p in range(4) if p not in g]
        return any(parity_ok(t) and all(t[p] == val for p, val in g.items())
                   for t in all_assignments)

    # repair attempt 1: remove ONE view
    removal = []
    for drop in range(4):
        g = {}
        for i, v in enumerate(views):
            if i != drop:
                g.update(v.view)
        removal.append({"removed": views[drop].pid,
                        "whole_exists": whole_exists(g)})
    # repair attempt 2: coordinated flip of ONE position in ALL views containing it
    coordinated = []
    for pos in range(4):
        g = dict(glued)
        g[pos] ^= 1
        pair_kept = all(views[i].view[p] == views[j].view[p]
                        for i in range(4) for j in range(i + 1, 4)
                        for p in (views[i].anchor & views[j].anchor))
        coordinated.append({"position": pos,
                            "whole_exists": parity_ok(tuple(g[p] for p in range(4))),
                            "pairwise_agreement_kept": pair_kept})
    return {"law": "odd parity over ring of 4",
            "local_extendability": local,
            "pairwise_agreement": pair_ok,
            "global_gluing_of_full_set": global_ok,
            "removal_of_one_view": removal,
            "coordinated_position_flip": coordinated,
            "conclusion": ("every part locally fine, ALL pairs agree, yet the set "
                           "has NO whole: no part is guilty; removing any one "
                           "part does NOT repair; the minimal repair is a "
                           "COORDINATED one-position change across parts — the "
                           "contradiction belongs to the set alone")}


# --------------------------------------------------------------------------- E3
def e3(seed: int = 11):
    rng = random.Random(seed)
    n, P, W = 16, 4, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)
    lst = list(style); lst[2] ^= 1; lst[3] ^= 1
    fstyle = tuple(lst)
    fw = whole_from_style(fstyle, n, v0=1)

    # phase 0: nothing learned -> foreign fragment is UNJUDGEABLE (parked)
    a0 = Assembly(n, P)
    out_p0 = a0.integrate(aperture(fw, n, 5, W, "F0"))

    # phase 1: parked true seed + foreign fragment sharing a position
    a1 = Assembly(n, P)
    a1.integrate(aperture(w, n, 0, W, "R1"))          # parks (first part)
    out_p1 = a1.integrate(aperture(fw, n, 3, W, "F1"))

    # phase 2: law complete, positions 12..15 left uncovered (stream [:4]):
    # foreign rejected WITHOUT positional contact; own unseen part accepted
    asm = Assembly(n, P)
    for k, s in enumerate(STARTS6[:4]):
        asm.integrate(aperture(w, n, s, W, pid=f"R{k+1}"))
    out_overlap = asm.integrate(aperture(fw, n, 5, W, "F2"))
    # second foreign whole: flip ONLY residue 3 -> divergence at {4..7, 12..15};
    # position 14 has BOTH neighbors unknown (13, 15) -> pure law-contact channel
    lst2 = list(style); lst2[3] ^= 1
    fw2 = whole_from_style(tuple(lst2), n, v0=1)
    probes = {}
    out_f14 = asm.integrate(aperture(fw2, n, 14, 1, "F3@14"))
    probes["foreign2@14_no_contact"] = {"status": out_f14.status, "reason": out_f14.reason,
                                        "truth": w[14], "foreign": fw2[14]}
    out_t14 = asm.integrate(aperture(w, n, 14, 1, "T14"))
    probes["own_unseen@14"] = {"status": out_t14.status, "reason": out_t14.reason}
    # position 13: differs AND touches known position 12 -> SEAM rejection
    out_f13 = asm.integrate(aperture(fw2, n, 13, 1, "F4@13"))
    probes["foreign2@13_seam"] = {"status": out_f13.status, "reason": out_f13.reason,
                                  "truth": w[13], "foreign": fw2[13]}
    # position 15: differs AND is the ring-neighbor of known position 0 ->
    # rejected via the SEAM relation it creates with the whole
    out_f15 = asm.integrate(aperture(fw, n, 15, 1, "F4@15"))
    probes["foreign@15_seam"] = {"status": out_f15.status, "reason": out_f15.reason,
                                 "truth": w[15], "foreign": fw[15]}
    out_t15 = asm.integrate(aperture(w, n, 15, 1, "T15"))
    probes["own_unseen@15"] = {"status": out_t15.status, "reason": out_t15.reason}
    return {"true_style": style, "foreign_style": fstyle,
            "phase0_unjudgeable": {"status": out_p0.status, "reason": out_p0.reason},
            "phase1_partial_law": {"status": out_p1.status, "reason": out_p1.reason,
                                   "blame": out_p1.detail.get("blame_candidates")},
            "phase2_full_law": {"overlapping_foreign": {"status": out_overlap.status,
                                                        "reason": out_overlap.reason},
                                "probes": probes},
            "conclusion": ("defense grows with learning: unjudgeable -> reject at "
                           "contact -> reject WITHOUT contact; the whole recognizes "
                           "its own unseen parts and refuses foreign ones by law "
                           "alone")}


# --------------------------------------------------------------------------- E4
def e4(seed: int = 11):
    rng = random.Random(seed)
    n, P, W = 16, 4, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)

    # (a) law-complete forgery attempt: forger knows law + one true value,
    #     fabricates a view never emitted by the world process
    asm = Assembly(n, P)
    for k, s in enumerate(STARTS6):
        asm.integrate(aperture(w, n, s, W, pid=f"R{k+1}"))
    law_view = propagate(asm.grammar.style_tuple(), n, P, 15, asm.known[15][0])
    forged_view = {pos: law_view[pos] for pos in (15, 0, 1, 2)}
    pf = Projection("FORGED", frozenset(forged_view), dict(forged_view), origin="forged")
    out_forged = asm.integrate(pf)
    equals_truth = all(forged_view[pos] == w[pos] for pos in forged_view)

    # (b) early poisoning: forged fragment arrives FIRST and anchors
    lst = list(style); lst[2] ^= 1
    fw = whole_from_style(tuple(lst), n, v0=1)
    forged_seed = Projection("F0", frozenset({(0 + k) % n for k in range(W)}),
                             {(0 + k) % n: fw[(0 + k) % n] for k in range(W)},
                             origin="forged")
    reals = [aperture(w, n, s, W, pid=f"R{k+1}") for k, s in enumerate([5, 10, 15, 1])]
    stream = [forged_seed] + reals
    asm2 = Assembly(n, P)
    timeline = []
    first_contra = None
    for p in stream:
        out = asm2.integrate(p)
        timeline.append({"pid": p.pid, "status": out.status, "reason": out.reason})
        if out.status == CONTRADICTION and first_contra is None:
            first_contra = {"at": p.pid, "reason": out.reason}
    poisoned_fid = fidelity(asm2.reconstruct(), w)
    cands = minimal_repair_sets(stream, n, P)
    cand_pids = [sorted(stream[i].pid for i in c) for c in cands]
    post_fid = None
    if cands:
        sub = [p for i, p in enumerate(stream) if i not in cands[0]]
        asm3, _ = rebuild(sub, n, P)
        post_fid = fidelity(asm3.reconstruct(), w)
    return {"a_law_complete_forgery": {"integration": out_forged.status,
                                       "forged_values_equal_truth": equals_truth},
            "b_early_poisoning": {"timeline": timeline,
                                  "first_contradiction": first_contra,
                                  "poisoned_reconstruction": poisoned_fid,
                                  "minimal_repair_candidates": cand_pids,
                                  "post_repair_fidelity": post_fid},
            "conclusion": ("under a complete law forgery degenerates into truth; "
                           "before completion the forged anchor takes the throne "
                           "and reality bounces off it; minimal blame (unique "
                           "here) evicts the forgery and restores the whole")}


# --------------------------------------------------------------------------- E5
def e5(seed: int = 11):
    rng = random.Random(seed)
    n, P, W = 16, 4, 4
    sA = make_style(rng, P)
    sB = tuple(1 - b for b in sA)
    wA = whole_from_style(sA, n, v0=0)
    wB = whole_from_style(sB, n, v0=0)
    stream, origins = [], {}
    plan = [(0, "A"), (1, "B"), (3, "A"), (4, "B"), (6, "A"), (7, "B")]
    for k, (s, who) in enumerate(plan):
        src = wA if who == "A" else wB
        stream.append(aperture(src, n, s, W, pid=f"X{k+1}", origin=who))
        origins[f"X{k+1}"] = who
    single = Assembly(n, P)
    single_out = []
    for p in stream:                       # integrate EXACTLY once per projection
        o = single.integrate(p)
        single_out.append({"pid": p.pid, "status": o.status, "reason": o.reason})

    # subject-side fork resolution: cluster by style votes
    def votes(p):
        return {r: p.view[i] ^ p.view[(i + 1) % n] for (i, r) in p.internal_edges(n, P)}
    clusters = []
    for p in stream:
        v = votes(p)
        placed = False
        for c in clusters:
            if all(c["style"].get(r, b) == b for r, b in v.items()):
                for r, b in v.items():
                    c["style"][r] = b
                c["members"].append(p.pid)
                placed = True
                break
        if not placed:
            clusters.append({"style": dict(v), "members": [p.pid]})
    cluster_report = []
    for c in clusters:
        sub = [p for p in stream if p.pid in c["members"]]
        asm, outs = rebuild(sub, n, P)
        cluster_report.append({
            "members": c["members"],
            "all_glued": all(o.status == GLUED for _, o in outs),
            "style_learned": asm.grammar.style_tuple() if asm.grammar.style_complete else None,
            "fid_vs_worldA": fidelity(asm.reconstruct(), wA),
            "fid_vs_worldB": fidelity(asm.reconstruct(), wB)})
    purity = all(len({origins[m] for m in c["members"]}) == 1 for c in clusters)
    return {"true_styles": {"A": sA, "B": sB},
            "single_assembly_outcomes": single_out,
            "clusters": cluster_report,
            "cluster_purity_vs_true_origin": purity,
            "conclusion": ("one assembly cannot hold two wholes: foreign parts "
                           "bounce; style votes separate the stream into "
                           "cluster-relative belonging — the subject now holds "
                           "two wholes as hypotheses")}


# --------------------------------------------------------------------------- E6
def e6(seed: int = 11):
    rng = random.Random(seed)
    n, P, W = 16, 4, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)
    pre = Assembly(n, P)
    for k, s in enumerate(STARTS6):
        pre.integrate(aperture(w, n, s, W, pid=f"pre{k+1}"))
    style_pre = pre.grammar.style_tuple()
    rec_pre = pre.reconstruct()
    # TOTAL WIPE: no assembly, no law, no pending, no logs
    post = Assembly(n, P)
    for k, s in enumerate([1, 4]):
        post.integrate(aperture(w, n, s, W, pid=f"post{k+1}"))
    style_post = post.grammar.style_tuple()
    rec_post = post.reconstruct()
    return {"style_before_wipe": style_pre, "style_after_wipe": style_post,
            "style_match": style_pre == style_post,
            "reconstruction_match": rec_pre == rec_post,
            "observed_after_wipe": len(post.known),
            "fidelity_after_wipe": fidelity(rec_post, w),
            "conclusion": ("belonging and whole-identity survive TOTAL loss of "
                           "history: the whole is re-identified from present "
                           "projections + law — the holographic superpower "
                           "M2' does not have")}


# --------------------------------------------------------------------------- E7
class M2PrimeLite:
    """Origin axis only: genesis + hash-chained transitions (round-2 M2', minimal)."""

    def __init__(self):
        self.chain = [hash(("GENESIS",))]

    def perform(self, content) -> int:
        self.chain.append(hash((self.chain[-1], content)))
        return len(self.chain) - 1

    def verify(self, idx: int, content) -> bool:
        return 0 < idx < len(self.chain) and \
            hash((self.chain[idx - 1], content)) == self.chain[idx]


def e7(seed: int = 11):
    rng = random.Random(seed)
    n, P, W = 16, 4, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=1)

    # ---- Case A: pedigreed nonsense — a glitch the subject REALLY performed
    asm = Assembly(n, P)
    m2 = M2PrimeLite()
    for k, s in enumerate(STARTS6):
        p = aperture(w, n, s, W, pid=f"R{k+1}")
        asm.integrate(p)
        m2.perform(frozenset(p.view.items()))
    glitch_view = dict(aperture(w, n, 5, W, "tmp").view)
    glitch_view[6] ^= 1
    glitch = Projection("GLITCH", frozenset(glitch_view), glitch_view, origin="world")
    idx = m2.perform(frozenset(glitch_view.items()))
    m2_verdict_A = m2.verify(idx, frozenset(glitch_view.items()))
    holo_verdict_A = asm.integrate(glitch)
    re_dis = asm.integrate(aperture(w, n, 5, W, "RE"))

    # ---- Case B: coherent forgery — glues with a true part, poisons an
    #      unlearned residue; blame is multi-candidate until next contact
    asmB = Assembly(n, P)
    m2B = M2PrimeLite()
    r1 = aperture(w, n, 0, W, "R1")
    asmB.integrate(r1)                       # parks: first part, unjudgeable
    m2B.perform(frozenset(r1.view.items()))
    lst = list(style); lst[3] ^= 1           # forgery obeys learned residues,
    fw = whole_from_style(tuple(lst), n, v0=1)  # deviates on the unlearned one
    fview = {3: w[3], 4: fw[4], 5: fw[5]}    # agrees at the overlap position
    forged = Projection("FORGED", frozenset(fview), dict(fview), origin="forged")
    outB1 = asmB.integrate(forged)
    m2_verdict_B = m2B.verify(1, frozenset(forged.view.items()))
    real2 = aperture(w, n, 5, W, "R2")
    outB2 = asmB.integrate(real2)            # contradiction fires here
    real3 = aperture(w, n, 6, W, "R3")       # next contact: INSIDE the poisoned zone
    cands = minimal_repair_sets([r1, forged, real2, real3], n, P)
    cand_pids = [sorted([r1.pid, forged.pid, real2.pid, real3.pid][i] for i in c)
                 for c in cands]
    post_fid = None
    if len(cands) == 1:
        sub = [p for p in (r1, forged, real2, real3)
               if p.pid not in cand_pids[0]]
        asmB2, outsB = rebuild(sub, n, P)
        post_fid = fidelity(asmB2.reconstruct(), w)

    return {"case_A_pedigreed_nonsense": {
                "m2prime_verdict": "ACCEPT" if m2_verdict_A else "REJECT",
                "holographic_verdict": holo_verdict_A.status,
                "holographic_reason": holo_verdict_A.reason,
                "after_re_discrimination": re_dis.status},
            "case_B_coherent_forgery": {
                "forgery_integration": outB1.status,
                "m2prime_verdict": "ACCEPT" if m2_verdict_B else "REJECT",
                "holographic_at_contact": outB2.status,
                "holographic_reason": outB2.reason,
                "minimal_repair_candidates": cand_pids,
                "unique_after_next_contact": len(cands) == 1,
                "post_repair_fidelity": post_fid},
            "conclusion": ("origin rejects a forgery a priori but cannot see its "
                           "own glitch; coherence sees the glitch, accepts the "
                           "forgery until reality tests it, and localizes blame "
                           "by further contact")}


def e7c(seed: int = 13, cycles: int = 12, drift_p: float = 0.4, world_every: int = 4):
    """Case C: echo chamber. Self-referential input with style drift.
    Trusting subject (no provenance) chases its own drift; provenance subject
    updates the law only from world-contact."""
    rng = random.Random(seed)
    n, P, W = 16, 4, 3
    true_style = make_style(rng, P)
    w = whole_from_style(true_style, n, v0=1)
    src_style = list(true_style)
    subj_trusting = list(true_style)
    subj_provenance = list(true_style)
    fid_t, fid_p = [], []
    self_overwrites_trusting = 0
    for t in range(cycles):
        world_contact = (t % world_every == 0)
        if not world_contact and rng.random() < drift_p:
            r = rng.randrange(P)
            src_style[r] ^= 1
        src_w = whole_from_style(tuple(src_style), n, v0=1)
        origin = "world" if world_contact else "self"
        p = aperture(src_w, n, rng.randrange(n), W, pid=f"S{t}", origin=origin)
        for (i, r) in p.internal_edges(n, P):
            bit = p.view[i] ^ p.view[(i + 1) % n]
            if origin == "self" and subj_trusting[r] != bit:
                self_overwrites_trusting += 1
            subj_trusting[r] = bit                    # trusting: latest-wins
            if origin == "world":
                subj_provenance[r] = bit              # provenance: contact-gated
        wt = {i: v for i, v in enumerate(whole_from_style(tuple(subj_trusting), n, v0=1))}
        wp = {i: v for i, v in enumerate(whole_from_style(tuple(subj_provenance), n, v0=1))}
        fid_t.append(fidelity(wt, w)["accuracy"])
        fid_p.append(fidelity(wp, w)["accuracy"])
    e7cr_pure_trusting = None
    return {"true_style": true_style, "cycles": cycles,
            "drift_probability": drift_p, "world_contact_every": world_every,
            "trusting_fidelity_curve": fid_t,
            "provenance_fidelity_curve": fid_p,
            "trusting_min_fidelity": min(fid_t),
            "provenance_min_fidelity": min(fid_p),
            "self_origin_style_overwrites_accepted_by_trusting": self_overwrites_trusting,
            "conclusion": ("coherence without provenance drifts from reality under "
                           "self-referential input; provenance is needed not for "
                           "belonging but for epistemic hygiene (world vs self)")}


# --------------------------------------------------------------------------- E8
def e8(trials: int = 50):
    n, P, W = 16, 4, 3

    def run(informed: bool, seed: int) -> int:
        rng = random.Random(1000 + seed)
        style = make_style(rng, P)
        w = whole_from_style(style, n, v0=rng.randint(0, 1))
        asm = Assembly(n, P)
        cycles = 0
        while not asm.grammar.style_complete and cycles < 20:
            if informed:
                best_s, best = 0, -10 ** 9
                for s in range(n):
                    residues = {(s + k) % P for k in range(W - 1)}
                    unknown_res = len(residues - set(asm.grammar.e_hat))
                    unknown_pos = sum(1 for k in range(W)
                                      if (s + k) % n not in asm.known)
                    touches = any((s + k) % n in asm.known for k in range(W)) or \
                        any(p.anchor & {(s + k) % n for k in range(W)}
                            for p in asm.pending.values())
                    score = 10 * unknown_res + unknown_pos + (5 if touches else 0)
                    if score > best:
                        best, best_s = score, s
                s = best_s
            else:
                s = rng.randrange(n)
            asm.integrate(aperture(w, n, s, W, pid=f"a{cycles}"))
            cycles += 1
        return cycles

    inf = [run(True, t) for t in range(trials)]
    rnd = [run(False, t) for t in range(trials)]
    mean = lambda xs: round(sum(xs) / len(xs), 3)
    return {"trials": trials, "informed_cycles": mean(inf),
            "random_cycles": mean(rnd), "informed_min_max": [min(inf), max(inf)],
            "random_min_max": [min(rnd), max(rnd)],
            "conclusion": ("the current whole guides where to look next; parts "
                           "refine the whole; the loop part->whole->part converges "
                           "faster than undirected reading")}


# ------------------------------------------------------------------------ main
def main():
    res = {"meta": {"round": 4, "topic": "holographic subject: projection-whole "
                    "construction, minimal properties of belonging",
                    "determinism": "seeded RNG; see scripts"}}
    res["E1_reconstruction_and_inference"] = e1()
    res["E2_pairwise_vs_global"] = e2()
    res["E3_defense_phases"] = e3()
    res["E4_forgery"] = e4()
    res["E5_fork"] = e5()
    res["E6_amnesia"] = e6()
    res["E7_separation_from_M2prime"] = e7()
    res["E7c_echo_chamber"] = e7c()
    res["E7c_pure_echo"] = e7c(world_every=10 ** 9)   # zero world contact
    res["E8_hermeneutic_loop"] = e8()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2, default=str)

    p = lambda *a: print(*a)
    p("=" * 72)
    p("E1 with law vs ablation:")
    for t, tb in zip(res["E1_reconstruction_and_inference"]["trajectory_with_law"],
                     res["E1_reconstruction_and_inference"]["trajectory_ablation_no_law"]):
        p(f"  {t['after']}: obs={t['observed']:2d} law={t['reconstruction']} "
          f"inf={t['full_inference']} | ablation obs={tb['observed']:2d} {tb['reconstruction']}")
    e2r = res["E2_pairwise_vs_global"]
    p(f"E2: local_ok={all(e2r['local_extendability'].values())} "
      f"pairwise_ok={e2r['pairwise_agreement']} global_ok={e2r['global_gluing_of_full_set']}")
    p(f"    removal_of_one={[(r['removed'], r['whole_exists']) for r in e2r['removal_of_one_view']]}")
    p(f"    coord_flip={[(c['position'], c['whole_exists'], c['pairwise_agreement_kept']) for c in e2r['coordinated_position_flip']]}")
    e3r = res["E3_defense_phases"]
    p(f"E3: phase0={e3r['phase0_unjudgeable']}")
    p(f"    phase1={e3r['phase1_partial_law']}")
    p(f"    phase2_overlap={e3r['phase2_full_law']['overlapping_foreign']}")
    for k, v in e3r["phase2_full_law"]["probes"].items():
        p(f"    {k}: {v}")
    e4r = res["E4_forgery"]
    p(f"E4a: {e4r['a_law_complete_forgery']}")
    p(f"E4b: timeline={e4r['b_early_poisoning']['timeline']}")
    p(f"     poisoned={e4r['b_early_poisoning']['poisoned_reconstruction']} "
      f"cands={e4r['b_early_poisoning']['minimal_repair_candidates']} "
      f"post={e4r['b_early_poisoning']['post_repair_fidelity']}")
    e5r = res["E5_fork"]
    p(f"E5: single={e5r['single_assembly_outcomes']}")
    for c in e5r["clusters"]:
        p(f"    cluster {c['members']}: glued={c['all_glued']} "
          f"style={c['style_learned']} fidA={c['fid_vs_worldA']} fidB={c['fid_vs_worldB']}")
    p(f"    purity={e5r['cluster_purity_vs_true_origin']}")
    e6r = res["E6_amnesia"]
    p(f"E6: style_match={e6r['style_match']} rec_match={e6r['reconstruction_match']} "
      f"obs_after={e6r['observed_after_wipe']} fid={e6r['fidelity_after_wipe']}")
    e7r = res["E7_separation_from_M2prime"]
    p(f"E7-A: {e7r['case_A_pedigreed_nonsense']}")
    p(f"E7-B: {e7r['case_B_coherent_forgery']}")
    e7cr = res["E7c_echo_chamber"]
    p(f"E7-C: trusting_min={e7cr['trusting_min_fidelity']} "
      f"provenance_min={e7cr['provenance_min_fidelity']} "
      f"self_overwrites={e7cr['self_origin_style_overwrites_accepted_by_trusting']}")
    p(f"      trusting={e7cr['trusting_fidelity_curve']}")
    p(f"      proven. ={e7cr['provenance_fidelity_curve']}")
    pe = res["E7c_pure_echo"]
    p(f"      PURE echo (no world contact): trusting_min={pe['trusting_min_fidelity']} "
      f"curve={pe['trusting_fidelity_curve']}")
    p(f"                                    provenance_min={pe['provenance_min_fidelity']}")
    e8r = res["E8_hermeneutic_loop"]
    p(f"E8: informed={e8r['informed_cycles']} random={e8r['random_cycles']} "
      f"minmax inf={e8r['informed_min_max']} rnd={e8r['random_min_max']}")
    p("=" * 72)
    p(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
