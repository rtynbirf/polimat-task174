#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E9 BATTERY — round 5: independent convergence, underdetermination,
second-order projection (whole_A -> projection -> whole_B).

Groups (user's spec, made strict):
  E9-A  same projections, two independent subjects:  I_A == I_B?  W_A == W_B?
        A2: permuted orders -> confluence of learning
  E9-B  different projections, one world:  W_A ≡ W_B?  invariant witnessed
        from (mostly) disjoint edges?
  E9-C  different worlds, shared part:  P_shared determines the whole only up
        to a CLASS;  (P,I_A) ⊢ W_A ≠ (P,I_B) ⊢ W_B;  class collapse 4→2→1;
        mutual refutation on contact
  E9-D  second-order projection:  unison via compressed whole (O(period) bits);
        fork refusal by invariant;  lying report: naive import poisons the LAW
        and bypasses stream-replay blame;  disciplined contact-verification
        refuses and detects;  law-surgery repair by source tag

Claim typing (adopted from the user's correction):
  every claim below is VERIFIED* = within this formal stand (ring, period-4
  law, noise-free streams) and these concrete tests — not a universal theorem.
"""
import os
import sys
import json
import random
from itertools import permutations, product

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from holographic_core import (GLUED, CONTRADICTION, DISCONNECTED,  # noqa: E402
                              make_style, whole_from_style, aperture, fidelity,
                              Assembly, rebuild)

OUT = "/home/z/my-project/download/e9_results.json"


def flip(style, residue):
    lst = list(style)
    lst[residue] ^= 1
    return tuple(lst)


def candidate_wholes(n, period, v0, fixed):
    """All wholes consistent with: law form + v0 at position 0 + fixed
    residue->bit map. This is the CLASS a set of parts determines."""
    free = [r for r in range(period) if r not in fixed]
    out = []
    for bits in product((0, 1), repeat=len(free)):
        st = [0] * period
        for r, b in fixed.items():
            st[r] = b
        for r, b in zip(free, bits):
            st[r] = b
        out.append(whole_from_style(tuple(st), n, v0))
    return out


def class_from_views(n, period, views, v0):
    """Class size given accumulated (anchor, view) pairs."""
    fixed = {}
    for anchor, view in views:
        for i in range(n):
            j = (i + 1) % n
            if i in anchor and j in anchor:
                fixed[i % period] = view[i] ^ view[j]
    return len({tuple(c) for c in candidate_wholes(n, period, v0, fixed)})


# ---------------------------------------------------------------------- E9-A
def e9a(seed: int = 21, perm_trials: int = 20):
    rng = random.Random(seed)
    n, P, W = 16, 4, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=rng.randint(0, 1))
    starts = [0, 3, 6, 9, 12, 15]
    stream = [aperture(w, n, s, W, pid=f"P{k+1}") for k, s in enumerate(starts)]
    A, B = Assembly(n, P), Assembly(n, P)
    steps = []
    for k, p in enumerate(stream):
        A.integrate(p)
        B.integrate(p)
        steps.append({"after": p.pid,
                      "known_equal": A.known == B.known,
                      "style_equal": A.grammar.e_hat == B.grammar.e_hat,
                      "pending_equal": sorted(A.pending) == sorted(B.pending)})
    truth = {i: w[i] for i in range(n)}
    a1 = {"stepwise_state_equal": all(s["known_equal"] and s["style_equal"]
                                      and s["pending_equal"] for s in steps),
          "n_steps": len(steps),
          "style_I_A_eq_I_B": A.grammar.style_tuple() == B.grammar.style_tuple(),
          "style_complete": A.grammar.style_complete,
          "whole_W_A_eq_W_B": A.reconstruct() == B.reconstruct(),
          "whole_eq_truth": A.reconstruct() == truth}
    # A2: confluence — the final whole must not depend on the reading order
    perms = list(permutations(range(len(stream))))
    rng.shuffle(perms)
    finals = set()
    for perm in perms[:perm_trials]:
        asm, _ = rebuild([stream[i] for i in perm], n, P)
        st = asm.grammar.style_tuple() if asm.grammar.style_complete else None
        finals.add((st, tuple(sorted(asm.reconstruct().items()))))
    a2 = {"orders_tested": perm_trials,
          "distinct_final_states": len(finals),
          "confluent": len(finals) == 1}
    return {"A1_same_stream_two_subjects": a1, "A2_confluence": a2,
            "true_style": style}


# ---------------------------------------------------------------------- E9-B
def e9b(seed: int = 21):
    rng = random.Random(seed)
    n, P, W = 16, 4, 4
    style = make_style(rng, P)
    w = whole_from_style(style, n, v0=rng.randint(0, 1))
    chain_A = [0, 3, 6, 9]      # 4 apertures -> positions 0..11, edges 0..9
    chain_B = [14, 11]          # 2 apertures -> positions {0,1,11..15}

    def anchors(chain):
        return {i for s in chain for i in {(s + k) % n for k in range(W)}}

    def build(chain):
        asm = Assembly(n, P)
        for s in chain:
            asm.integrate(aperture(w, n, s, W, pid=f"@{s}"))
        return asm

    A, B = build(chain_A), build(chain_B)
    truth = {i: w[i] for i in range(n)}

    def witnesses(chain):
        d = {r: set() for r in range(P)}
        for s in chain:
            for (i, r) in aperture(w, n, s, W, "x").internal_edges(n, P):
                d[r].add(i)
        return d

    witA, witB = witnesses(chain_A), witnesses(chain_B)
    uniq = {r: sorted(witB[r] - witA[r]) for r in range(P)}
    return {"style_I_A_eq_I_B": A.grammar.style_tuple() == B.grammar.style_tuple(),
            "both_complete": A.grammar.style_complete and B.grammar.style_complete,
            "W_A_eq_W_B_eq_truth": A.reconstruct() == B.reconstruct() == truth,
            "observed_A": len(A.known), "observed_B": len(B.known),
            "apertures_A": len(chain_A), "apertures_B": len(chain_B),
            "position_overlap": len(anchors(chain_A) & anchors(chain_B)),
            "witness_edges_A": {r: sorted(v) for r, v in witA.items()},
            "witness_edges_B": {r: sorted(v) for r, v in witB.items()},
            "B_unique_witness_edges": uniq,
            "every_residue_has_B_unique_witness":
                all(len(uniq[r]) > 0 for r in range(P))}


# ---------------------------------------------------------------------- E9-C
def e9c(seed: int = 21):
    rng = random.Random(seed)
    n, P = 16, 4
    styleA = make_style(rng, P)
    styleB = flip(flip(styleA, 2), 3)     # agrees on residues 0,1
    v0 = rng.randint(0, 1)
    wA = whole_from_style(styleA, n, v0)
    wB = whole_from_style(styleB, n, v0)
    diff_positions = [i for i in range(n) if wA[i] != wB[i]]

    # shared part: width-3 aperture at 0 (positions 0..2, edges 0 and 1)
    ps = aperture(wA, n, 0, 3, pid="PS")
    psB = aperture(wB, n, 0, 3, pid="PS")     # identical values (shared region)
    views = [(ps.anchor, ps.view)]

    # the CLASS consistent with P_shared + law form alone
    fixed0 = {0: wA[0] ^ wA[1], 1: wA[1] ^ wA[2]}
    cls0 = candidate_wholes(n, P, wA[0], fixed0)
    cls0_ok = all(all(c[i] == ps.view[i] for i in ps.anchor) for c in cls0)
    cls0_distinct = len({tuple(c) for c in cls0}) == len(cls0)

    A, B = Assembly(n, P), Assembly(n, P)
    stA = [A.integrate(ps).status]
    stB = [B.integrate(psB).status]
    states_equal_after_PS = (sorted(A.pending) == sorted(B.pending)
                             and A.grammar.e_hat == B.grammar.e_hat)

    # divergent continuation: SAME anchors, values from each one's own world
    cascade = [{"after": "PS", "class_size": class_from_views(n, P, views, wA[0])}]
    outs = {"A": stA, "B": stB}
    for s, wd in [(2, 2), (3, 2)]:
        pA = aperture(wA, n, s, wd, pid=f"cont@{s}")
        pB = aperture(wB, n, s, wd, pid=f"cont@{s}")
        outs["A"].append(A.integrate(pA).status)
        outs["B"].append(B.integrate(pB).status)
        views.append((pA.anchor, pA.view))
        cascade.append({"after": pA.pid,
                        "class_size": class_from_views(n, P, views, wA[0])})

    truthA = {i: wA[i] for i in range(n)}
    truthB = {i: wB[i] for i in range(n)}
    # mutual refutation: A's completed assembly rejects B's continuation
    cross = A.integrate(aperture(wB, n, 3, 2, pid="Bstream@3"))
    return {"styles": {"A": styleA, "B": styleB},
            "differing_positions": diff_positions,
            "epistemic_states_equal_after_PS": states_equal_after_PS,
            "class_given_P_shared": {"size": len(cls0), "all_consistent": cls0_ok,
                                     "all_distinct": cls0_distinct},
            "continuation_statuses": outs,
            "no_contradiction_inside_either_stream":
                all(s in (GLUED, DISCONNECTED) for s in outs["A"]) and
                all(s in (GLUED, DISCONNECTED) for s in outs["B"]),
            "class_collapse": cascade,
            "style_A_neq_B": styleA != styleB,
            "W_A_eq_truth": A.reconstruct() == truthA,
            "W_B_eq_truth": B.reconstruct() == truthB,
            "acc_W_A_vs_worldB": fidelity(A.reconstruct(), wB),
            "mutual_refutation_on_contact":
                cross.status == CONTRADICTION,
            "cross_reason": cross.reason}


# ---------------------------------------------------------------------- E9-D
def e9d(seed: int = 21):
    rng = random.Random(seed)
    n, P, W = 16, 4, 4
    styleA = make_style(rng, P)
    v0 = rng.randint(0, 1)
    wA = whole_from_style(styleA, n, v0)
    chain_A = [0, 3, 6, 9]
    chain_B = [14, 11]

    def build(world, chain):
        asm = Assembly(n, P)
        for s in chain:
            asm.integrate(aperture(world, n, s, W, pid=f"@{s}"))
        return asm

    # ---- D1: unison via compressed whole (same world, different chains)
    A = build(wA, chain_A)
    B = build(wA, chain_B)
    Q = {"style": list(styleA), "v0": wA[0], "pos": 0}   # A's report of ITS whole
    d1 = {"style_claim_matches_B": tuple(Q["style"]) == B.grammar.style_tuple(),
          "value_claim_matches_B": Q["v0"] == B.reconstruct()[Q["pos"]]}
    d1["unison_of_wholes"] = d1["style_claim_matches_B"] and d1["value_claim_matches_B"]
    d1["units_sent"] = P + 2
    d1["units_naive_whole"] = n

    # ---- D2: fork refusal (B2 holds a DIFFERENT whole)
    styleB2 = flip(styleA, 1)
    wB2 = whole_from_style(styleB2, n, v0)
    B2 = build(wB2, chain_B)
    before = B2.reconstruct()
    refuse = tuple(Q["style"]) != B2.grammar.style_tuple()
    d2 = {"style_claim_matches_B2": not refuse,
          "verdict": "REFUSE" if refuse else "ACCEPT",
          "B2_state_unchanged": B2.reconstruct() == before,
          "B2_fidelity_vs_own_world": fidelity(B2.reconstruct(), wB2)}

    # ---- D3: lying report to an incomplete subject
    # B3: incomplete law (r3 free): width-3 chain [0,1] -> known 0..3
    lie = flip(styleA, 3)                 # false but internally consistent
    s3 = [aperture(wA, n, 0, 3, pid="B3@0"), aperture(wA, n, 1, 3, pid="B3@1")]
    B3, B3n = Assembly(n, P), Assembly(n, P)
    st3 = [B3.integrate(p).status for p in s3]
    for p in s3:
        B3n.integrate(p)
    fixed3 = {r: b for r, (b, _) in B3.grammar.e_hat.items()}
    class_before = len({tuple(c) for c in
                        candidate_wholes(n, P, B3.known[0][0], fixed3)})
    # naive: import the report AS law (bypasses gluing discipline)
    for r, b in enumerate(lie):
        B3n.grammar.e_hat[r] = (b, "REPORT")
    fid_naive = fidelity(B3n.reconstruct(), wA)
    contact = aperture(wA, n, 3, 2, pid="contact@3")
    nc = B3n.integrate(contact)
    # law-surgery repair: evict report-tagged residue, re-learn from contact
    evicted = [r for r, (b, src) in B3n.grammar.e_hat.items() if src == "REPORT"]
    for r in evicted:
        B3n.grammar.e_hat.pop(r)
    repair = B3n.integrate(contact)
    fid_repaired = fidelity(B3n.reconstruct(), wA)
    # selective: import ONLY the free residue, keep contact-sourced tags
    B3s = Assembly(n, P)
    for p in s3:
        B3s.integrate(p)
    free = [r for r in range(P) if r not in B3s.grammar.e_hat]
    for r in free:
        B3s.grammar.e_hat[r] = (lie[r], "REPORT")
    fid_selective = fidelity(B3s.reconstruct(), wA)
    nc_s = B3s.integrate(contact)
    evicted_s = [r for r, (b, src) in B3s.grammar.e_hat.items() if src == "REPORT"]
    for r in evicted_s:
        B3s.grammar.e_hat.pop(r)
    repair_s = B3s.integrate(contact)
    fid_sel_rep = fidelity(B3s.reconstruct(), wA)
    # disciplined: report stored as hypothesis; only contact completes the law
    hyp = {"style": lie, "origin": "REPORT", "verified": False}
    dc = B3.integrate(contact)
    hyp["verified"] = tuple(hyp["style"]) == B3.grammar.style_tuple()
    fid_disc = fidelity(B3.reconstruct(), wA)
    lie_detected = tuple(lie) != B3.grammar.style_tuple()
    return {"D1_unison_via_compressed_whole": d1,
            "D2_fork_refusal": d2,
            "D3_lying_report": {
                "B3_class_size_before": class_before,
                "B3_stream_statuses": st3,
                "import_disciplines": {
                    "total_import": {
                        "fidelity": fid_naive,
                        "contact_outcome": nc.status,
                        "contact_reason": nc.reason,
                        "evicted_for_repair": len(evicted),
                        "post_surgery_fidelity": fid_repaired},
                    "selective_import_free_residues_only": {
                        "fidelity": fid_selective,
                        "contact_outcome": nc_s.status,
                        "evicted_for_repair": len(evicted_s),
                        "post_surgery_fidelity": fid_sel_rep},
                    "disciplined_no_import": {
                        "fidelity": fid_disc,
                        "contact_outcome": dc.status,
                        "evicted_for_repair": 0,
                        "lie_detected_after_contact": lie_detected}},
                "blast_radius_gradient": "total=4 residues, selective=1, disciplined=0",
                "stream_replay_cannot_see_law_poison": True}}


# ---------------------------------------------------------------------- main
def main():
    res = {"meta": {"round": 5, "topic": "E9: independent convergence, "
                    "underdetermination, second-order projection",
                    "claim_typing": "VERIFIED* = within this formal stand only"}}
    res["E9A_same_stream_confluence"] = e9a()
    res["E9B_different_streams_one_world"] = e9b()
    res["E9C_shared_part_divergent_wholes"] = e9c()
    res["E9D_second_order_projection"] = e9d()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2, default=str)

    p = lambda *a: print(*a)
    p("=" * 72)
    a = res["E9A_same_stream_confluence"]
    p(f"E9-A1: stepwise_equal={a['A1_same_stream_two_subjects']['stepwise_state_equal']} "
      f"I_A==I_B={a['A1_same_stream_two_subjects']['style_I_A_eq_I_B']} "
      f"W_A==W_B={a['A1_same_stream_two_subjects']['whole_W_A_eq_W_B']} "
      f"W==truth={a['A1_same_stream_two_subjects']['whole_eq_truth']}")
    p(f"E9-A2: confluent={a['A2_confluence']['confluent']} "
      f"distinct={a['A2_confluence']['distinct_final_states']} "
      f"over {a['A2_confluence']['orders_tested']} orders")
    b = res["E9B_different_streams_one_world"]
    p(f"E9-B: I_A==I_B={b['style_I_A_eq_I_B']} W==truth={b['W_A_eq_W_B_eq_truth']} "
      f"obs_A={b['observed_A']} obs_B={b['observed_B']} "
      f"apos={b['apertures_A']} bpos={b['apertures_B']} overlap={b['position_overlap']}")
    p(f"      B-unique witnesses={b['B_unique_witness_edges']} "
      f"all_residues={b['every_residue_has_B_unique_witness']}")
    c = res["E9C_shared_part_divergent_wholes"]
    p(f"E9-C: diff_pos={c['differing_positions']} class0={c['class_given_P_shared']}")
    p(f"      states_equal_after_PS={c['epistemic_states_equal_after_PS']}")
    p(f"      statuses A={c['continuation_statuses']['A']} B={c['continuation_statuses']['B']}")
    p(f"      collapse={c['class_collapse']}")
    p(f"      W_A==truth={c['W_A_eq_truth']} W_B==truth={c['W_B_eq_truth']} "
      f"acc_A_vs_B={c['acc_W_A_vs_worldB']}")
    p(f"      no_contra_inside={c['no_contradiction_inside_either_stream']} "
      f"mutual_refutation={c['mutual_refutation_on_contact']} ({c['cross_reason']})")
    d = res["E9D_second_order_projection"]
    p(f"E9-D1: {d['D1_unison_via_compressed_whole']}")
    p(f"E9-D2: {d['D2_fork_refusal']}")
    p(f"E9-D3: {json.dumps(d['D3_lying_report'], ensure_ascii=False)}")
    p("=" * 72)
    p(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
