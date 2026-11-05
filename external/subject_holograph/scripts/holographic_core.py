#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HOLOGRAPHIC SUBJECT — round 4: formalizing the projection-whole construction.

Question implemented here (after the user's holographic pivot):
  Which MINIMAL properties make "this part belongs to this whole" recoverable
  from a set of projections ALONE — without physical transfer, without labels,
  without a stored copy of the whole, without origin proofs?

Formalization commitments (each is a decision, all are testable):
  D1  The whole is a ring of bits governed by a LAW: v[i+1] = v[i] XOR e[i % P].
      The law FORM + period P is the invariant schema; the style e is learned
      from projections. The law is what "the whole" contributes to every part.
  D2  A PROJECTION is (anchor, view): anchor = self-location in the whole's
      index space; view = partial content. A projection carries NO copy of the
      whole, NO labels, NO origin proofs. It carries relations (internal edges).
  D3  The whole is NEVER stored by the subject. The subject holds only:
      (a) glued, contributor-tagged values (assembly),
      (b) the learned style (law parameters),
      (c) parked projections it could not yet place (pending).
      "The whole" = the fixed point of gluing, reconstructed on demand.
  D4  BELONGING = gluing: anchor-fit + overlap-agreement + global law check.
      Not by labels, not by physical transfer, not by origin.
  D5  Once the law is learned, any single part FORCES the whole (inference):
      part + law -> whole. This is the literal holographic move.
  D6  Integration outcomes: GLUED (verified) / CONTRADICTION (falsified) /
      DISCONNECTED (cannot judge — parked). Verification/falsification/ignorance.
  D7  Parts check against PARTS, not only against the assembly: a projection
      with no assembly-contact may cohere with a parked projection. The first
      coherent pair anchors the whole (the minimal unavoidable postulate —
      the holographic analog of genesis).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional
from itertools import combinations

GLUED = "GLUED"
CONTRADICTION = "CONTRADICTION"
DISCONNECTED = "DISCONNECTED"


# ------------------------------------------------------------------ God view

def make_style(rng: random.Random, period: int) -> tuple:
    return tuple(rng.randint(0, 1) for _ in range(period))


def whole_from_style(style, n: int, v0: int = 0) -> tuple:
    """Ground-truth whole: ring of bits with v[i+1] = v[i] XOR style[i % P].
    Exists only in the experiment's God view; the subject never sees it."""
    xs = [v0]
    for i in range(n - 1):
        xs.append(xs[-1] ^ style[i % len(style)])
    acc = 0
    for i in range(n):
        acc ^= xs[i] ^ xs[(i + 1) % n]
    assert acc == 0, f"style {style} does not close on ring n={n}"
    return tuple(xs)


@dataclass(frozen=True)
class Projection:
    pid: str
    anchor: frozenset          # positions in the whole's index space
    view: dict                 # pos -> value
    origin: str = "world"      # battery bookkeeping ONLY; the subject does not
                               # read this field (that is the whole point of D4)

    def internal_edges(self, n: int, period: int):
        """Edges (i, i+1) fully inside the anchor: the RELATIONS the part
        carries. A part is not a bag of values; it carries edges of the law."""
        out = []
        for i in range(n):
            j = (i + 1) % n
            if i in self.anchor and j in self.anchor:
                out.append((i, i % period))
        return out


def aperture(w, n: int, start: int, width: int, pid: str,
             origin: str = "world") -> Projection:
    """Discrimination of a phase: a partial, anchored view of the whole."""
    anchor = {(start + k) % n for k in range(width)}
    view = {pos: w[pos] for pos in anchor}
    return Projection(pid=pid, anchor=frozenset(anchor), view=view, origin=origin)


def propagate(style, n: int, period: int, pos0: int, v0: int) -> dict:
    """Force the whole from one part using the law. The holographic move:
    part + law -> whole."""
    vals = {pos0: v0}
    cur, v = pos0, v0
    for _ in range(n - 1):
        nxt = (cur + 1) % n
        v = v ^ style[cur % period]
        vals[nxt] = v
        cur = nxt
    return vals


def fidelity(recon: dict, truth) -> dict:
    if not recon:
        return {"coverage": 0.0, "accuracy": None}
    cov = len(recon) / len(truth)
    acc = sum(1 for p, v in recon.items() if truth[p] == v) / len(recon)
    return {"coverage": round(cov, 4), "accuracy": round(acc, 4)}


# ------------------------------------------------------------- Subject side

class SubjectGrammar:
    """The whole's law as held by the subject: form + period + learned style."""

    def __init__(self, n: int, period: int):
        self.n = n
        self.period = period
        self.e_hat = {}   # residue -> (bit, source_pid)

    @property
    def style_complete(self) -> bool:
        return len(self.e_hat) == self.period

    def style_tuple(self) -> tuple:
        return tuple(self.e_hat[r][0] for r in range(self.period))


@dataclass
class Outcome:
    status: str
    reason: str = ""
    detail: dict = field(default_factory=dict)


class Assembly:
    """The whole-under-construction. Never a stored whole: only glued,
    contributor-tagged values + learned law + parked projections."""

    def __init__(self, n: int, period: int):
        self.n = n
        self.period = period
        self.grammar = SubjectGrammar(n, period)
        self.known = {}          # pos -> (value, contributor_pid, origin)
        self.pending = {}        # pid -> Projection (unjudgeable yet)
        self.latent = {}         # pid -> Outcome (contradiction seen, parked)
        self.absorbed_pids = set()
        self._absorbing = False

    # ------------------------------------------------------------ inference
    def infer_full(self) -> Optional[dict]:
        """The whole FORCED by the learned law + any known part."""
        if not self.grammar.style_complete or not self.known:
            return None
        pos0 = min(self.known)
        v0 = self.known[pos0][0]
        return propagate(self.grammar.style_tuple(), self.n, self.period, pos0, v0)

    def reconstruct(self) -> dict:
        full = self.infer_full()
        if full is not None:
            return full
        return {pos: v for pos, (v, _, _) in self.known.items()}

    # ------------------------------------------------------------- helpers
    def _votes(self, p: Projection) -> dict:
        """Style-bit votes carried by the part's internal edges."""
        return {r: p.view[i] ^ p.view[(i + 1) % self.n]
                for (i, r) in p.internal_edges(self.n, self.period)}

    def _commit_anchor(self, q: Projection):
        """Accept the first coherent part as the anchor. Minimal unavoidable
        postulate of the construction (holographic analog of genesis):
        SOMETHING must be accepted without a prior test."""
        for pos in q.anchor:
            self.known[pos] = (q.view[pos], q.pid, q.origin)
        for (i, r) in q.internal_edges(self.n, self.period):
            bit = q.view[i] ^ q.view[(i + 1) % self.n]
            if r not in self.grammar.e_hat:
                self.grammar.e_hat[r] = (bit, q.pid)
        self.pending.pop(q.pid, None)
        self.absorbed_pids.add(q.pid)

    def _park_or_cohere(self, p: Projection) -> Outcome:
        """No assembly-contact: try to cohere with a PARKED part (parts check
        against parts). Compatible -> the parked part anchors, p glues.
        Clash -> contradiction. No overlap at all -> park as unjudgeable."""
        overlapping = [q for q in self.pending.values()
                       if q.pid != p.pid and p.anchor & q.anchor]
        if not overlapping:
            self.pending[p.pid] = p
            return Outcome(DISCONNECTED, "no_overlap_no_law_contact",
                           {"parked": p.pid})
        vp = self._votes(p)
        for q in overlapping:                       # prefer a compatible anchor
            if any(p.view[pos] != q.view[pos] for pos in p.anchor & q.anchor):
                continue
            vq = self._votes(q)
            if any(vp[r] != vq[r] for r in set(vp) & set(vq)):
                continue
            self._commit_anchor(q)
            return self.integrate(p)
        q0 = overlapping[0]
        shared = sorted(p.anchor & q0.anchor)
        if any(p.view[pos] != q0.view[pos] for pos in shared):
            return Outcome(CONTRADICTION, "clash_with_parked",
                           {"with": q0.pid, "positions": shared,
                            "blame_candidates": sorted({p.pid, q0.pid})})
        vq0 = self._votes(q0)
        conf = sorted(r for r in set(vp) & set(vq0) if vp[r] != vq0[r])
        return Outcome(CONTRADICTION, "style_clash_with_parked",
                       {"with": q0.pid, "residues": conf,
                        "blame_candidates": sorted({p.pid, q0.pid})})

    # ----------------------------------------------------------------- core
    def integrate(self, p: Projection) -> Outcome:
        """Try to glue a projection into the whole. Checks run BEFORE commit."""
        merged = {pos: self.known[pos][0] for pos in self.known}
        for pos in p.anchor:
            merged[pos] = p.view[pos]

        # (1) direct value clashes against glued values
        clashes = [(pos, self.known[pos][0], p.view[pos])
                   for pos in sorted(p.anchor)
                   if pos in self.known and self.known[pos][0] != p.view[pos]]
        if clashes:
            blame = sorted({self.known[pos][1] for pos, _, _ in clashes} | {p.pid})
            return Outcome(CONTRADICTION, "value_clash",
                           {"clashes": clashes, "blame_candidates": blame})

        # (2) connectivity: positional overlap OR law-contact OR parked-part contact
        inf_old = self.infer_full()
        overlap = any(pos in self.known for pos in p.anchor)
        if not overlap and inf_old is None:
            return self._park_or_cohere(p)

        # (3) style checks: relations the part carries + relations CREATED by gluing
        style_clashes = []
        for (i, r) in p.internal_edges(self.n, self.period):
            bit = p.view[i] ^ p.view[(i + 1) % self.n]
            if r in self.grammar.e_hat and self.grammar.e_hat[r][0] != bit:
                style_clashes.append({"edge": i, "residue": r})
        for i in range(self.n):
            j = (i + 1) % self.n
            if i in merged and j in merged:
                r = i % self.period
                bit = merged[i] ^ merged[j]
                if (r in self.grammar.e_hat and self.grammar.e_hat[r][0] != bit
                        and not any(c["edge"] == i for c in style_clashes)):
                    style_clashes.append({"edge": i, "residue": r})
        if style_clashes:
            blame = sorted({p.pid} |
                           {self.grammar.e_hat[c["residue"]][1] for c in style_clashes})
            return Outcome(CONTRADICTION, "style_clash",
                           {"edges": style_clashes, "blame_candidates": blame})

        # (4) law completion + inference checks. If this part COMPLETES the law,
        #     the thereby-forced whole must agree with everything glued so far.
        new_bits = {}
        for i in range(self.n):
            j = (i + 1) % self.n
            if i in merged and j in merged:
                r = i % self.period
                if r not in self.grammar.e_hat and r not in new_bits:
                    new_bits[r] = (merged[i] ^ merged[j], p.pid)
        if inf_old is not None:
            mism = [pos for pos in sorted(p.anchor) if inf_old[pos] != p.view[pos]]
            if mism:
                return Outcome(CONTRADICTION, "law_mismatch",
                               {"positions": mism, "blame_candidates": [p.pid]})
        if len(self.grammar.e_hat) + len(new_bits) == self.period:
            st_bits = {r: self.grammar.e_hat[r][0] for r in self.grammar.e_hat}
            for r, (b, _) in new_bits.items():
                st_bits[r] = b
            st = tuple(st_bits[r] for r in range(self.period))
            pos0 = min(merged)
            full = propagate(st, self.n, self.period, pos0, merged[pos0])
            mism2 = [pos for pos in sorted(merged) if full[pos] != merged[pos]]
            if mism2:
                blame = sorted({self.known[pos][1] for pos in mism2
                                if pos in self.known} | {p.pid})
                return Outcome(CONTRADICTION, "inference_clash",
                               {"positions": mism2, "blame_candidates": blame})

        # (5) commit: merge values, learn law bits, absorb now-connectable parts
        for pos in p.anchor:
            self.known[pos] = (p.view[pos], p.pid, p.origin)
        for r, (b, pid) in new_bits.items():
            self.grammar.e_hat[r] = (b, pid)
        absorbed = self._absorb_pending()
        return Outcome(GLUED, "", {"absorbed": absorbed,
                                   "style_learned": sorted(new_bits.keys())})

    def _absorb_pending(self):
        """The part->whole->part loop: newly glued parts may bridge parked ones."""
        absorbed = []
        if self._absorbing:
            return absorbed
        self._absorbing = True
        try:
            progress = True
            while progress and self.pending:
                progress = False
                for q in list(self.pending.values()):
                    self.pending.pop(q.pid, None)
                    out = self.integrate(q)
                    if out.status == GLUED:
                        absorbed.append(q.pid)
                        self.absorbed_pids.add(q.pid)
                        progress = True
                    elif out.status == CONTRADICTION:
                        self.latent[q.pid] = out
                    else:
                        self.pending[q.pid] = q
        finally:
            self._absorbing = False
        return absorbed


def rebuild(stream, n: int, period: int):
    """Fresh subject state; replay the stream; final absorb sweep (the completed
    law may bridge parked parts). Used for blame attribution."""
    asm = Assembly(n, period)
    outs = []
    for p in stream:
        outs.append([p.pid, asm.integrate(p)])
    asm._absorb_pending()
    final = []
    for pid, out in outs:
        if out.status == DISCONNECTED and pid in asm.absorbed_pids:
            out = Outcome(GLUED, "", {"absorbed_late": True})
        final.append((pid, out))
    return asm, final


def minimal_repair_sets(stream, n: int, period: int):
    """ALL minimal removal sets making the remaining stream glue cleanly.
    Subject-side criterion only (internal consistency + law closure);
    several candidates may exist — reality contact discriminates them."""
    for k in range(0, len(stream) + 1):
        found = []
        for combo in combinations(range(len(stream)), k):
            sub = [p for i, p in enumerate(stream) if i not in combo]
            asm, outs = rebuild(sub, n, period)
            if all(o.status == GLUED for _, o in outs):
                found.append(set(combo))
        if found:
            return found
    return []
