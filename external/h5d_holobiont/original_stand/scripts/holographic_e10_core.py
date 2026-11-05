#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E10 CORE — round 6: surgical amputation of the subject's axes.

The user's correction implemented here:
  I31  functional necessity != implementation necessity: the criterion is a
       DISAPPEARING DISCRIMINATION (a pair of states distinguishable with the
       axis, indistinguishable without it), not "the system broke".
  I32  CONTACT_LABEL != CONTACT: a trusted tag is a declaration; verification
       is a mechanism. Both are implemented and attacked.
  I33  the axes must be mechanized, not declared: CAUSAL on a KEYED hash chain
       (forgery = hash preimage search, measured), CONTACT verification on
       Lamport one-time signatures (forgery = preimage search, measured).
  I34  COHERENCE = GRAMMAR + ASSEMBLY + INTEGRATION is an architectural
       decomposition: each sub-mechanism can be trivialized independently.

Axes of Subject10 (surgical switches):
  causal    : "chain" (keyed chain check) | "none" (no origin-in-history check)
  coherence : "full" | "t_grammar" | "t_assembly" | "t_integration" | "none"
  contact   : "tag" | "verify" | "metadata" | "none"   (law-write gating)

Gate order on receive: CAUSAL -> COHERENCE(integrate) -> CONTACT(law gate).
Belonging stays coherence-relative (D4): contact gates LAW WRITES, not gluing.
"""
from __future__ import annotations

import copy
import hashlib
import os
import random
import sys
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from holographic_core import (GLUED, CONTRADICTION, DISCONNECTED,  # noqa: E402
                              make_style, whole_from_style, aperture, propagate,
                              fidelity, Assembly, Projection, Outcome)

REFUSED_CAUSAL = "REFUSED_CAUSAL"


def H(*parts: bytes) -> bytes:
    h = hashlib.sha256()
    for p in parts:
        h.update(p)
    return h.digest()


def flip(style, residue: int) -> tuple:
    lst = list(style)
    lst[residue] ^= 1
    return tuple(lst)


def event_digest(proj: Projection) -> bytes:
    """Content digest: the signature binds the CONTENT, not a label."""
    items = tuple(sorted(proj.view.items()))
    return H(repr((proj.pid, tuple(sorted(proj.anchor)), items)).encode())


# ------------------------------------------------------------------ CAUSAL axis
class CausalChain:
    """Keyed hash chain: proof = H(K || prev_tip || pid || digest).
    Only the holder of K can extend the chain; a forged proof requires a
    preimage/key search. This mechanizes 'produced in MY history'."""

    def __init__(self, sid: str, key: Optional[bytes] = None):
        self.sid = sid
        self.K = key if key is not None else H(b"key::" + sid.encode())
        self.tip = H(b"genesis::" + sid.encode())

    def issue(self, pid: str, digest: bytes):
        prev = self.tip
        proof = H(self.K, prev, pid.encode(), digest)
        self.tip = proof
        return prev, proof

    def verify(self, pid: str, digest: bytes, prev_tip: bytes, proof: bytes) -> bool:
        """The presented transition must BE the latest keyed extension of my
        history: proof == current tip AND internally key-consistent. (The
        record-then-present order makes the just-recorded event the tip;
        replays of older transitions and foreign proofs fail.)"""
        return (proof == self.tip
                and H(self.K, prev_tip, pid.encode(), digest) == proof)

    def forge_attempts(self, pid: str, digest: bytes, tries: int, rng) -> dict:
        """Brute-force proof guesses without K (the subject-side check fails
        unless the guess equals the keyed proof)."""
        ok = 0
        for _ in range(tries):
            guess = bytes(rng.getrandbits(8) for _ in range(32))
            if H(self.K, self.tip, pid.encode(), digest) == guess:
                ok += 1
        return {"attempts": tries, "successes": ok}


class OpenChain(CausalChain):
    """Unkeyed chain (integrity only): anyone who knows the tip can extend it.
    The control showing WHY the key is needed — an unkeyed chain is just a tag."""

    def issue(self, pid: str, digest: bytes):
        prev = self.tip
        proof = H(prev, pid.encode(), digest)
        self.tip = proof
        return prev, proof

    def verify(self, pid: str, digest: bytes, prev_tip: bytes, proof: bytes) -> bool:
        return (proof == self.tip
                and H(prev_tip, pid.encode(), digest) == proof)

    def forge_attempts(self, pid: str, digest: bytes, tries: int, rng) -> dict:
        """Attack the CONSISTENCY relation with a PUBLIC tip: an attacker who
        sees the history computes the valid next proof in ONE step (no key
        exists). This is why an unkeyed chain is a tag, not a mechanism."""
        proof = H(self.tip, pid.encode(), digest)
        consistent = (proof == H(self.tip, pid.encode(), digest))
        return {"attempts": 1, "successes": 1 if consistent else 0,
                "check": "consistency_only_public_tip"}


# ----------------------------------------------------------------- CONTACT axis
class LamportChannel:
    """World-side signing of contact events with Lamport one-time signatures.
    Verification is PUBLIC (the subject holds only the published key y);
    forging a signature for a new digest requires hash preimages."""

    def __init__(self, world_id: str = "W"):
        self.x = [[H(f"lp::{world_id}::{i}::{b}".encode()) for b in (0, 1)]
                  for i in range(256)]
        self.pubkey = [[H(xi) for xi in pair] for pair in self.x]

    def sign(self, digest: bytes) -> tuple:
        sig = []
        for i in range(256):
            bit = (digest[i // 8] >> (7 - i % 8)) & 1
            sig.append(self.x[i][bit])
        return (self.pubkey, sig)

    @staticmethod
    def verify(digest: bytes, expected_pubkey, sig) -> bool:
        if sig is None or len(sig) != 256:
            return False
        for i in range(256):
            bit = (digest[i // 8] >> (7 - i % 8)) & 1
            if H(sig[i]) != expected_pubkey[i][bit]:
                return False
        return True

    @staticmethod
    def forge_attempts(digest: bytes, expected_pubkey, tries: int) -> dict:
        """Random signature guesses against the world's published key."""
        ok = 0
        for _ in range(tries):
            guess = [H(f"guess::{_}::{i}".encode()) for i in range(256)]
            if LamportChannel.verify(digest, expected_pubkey, guess):
                ok += 1
        return {"attempts": tries, "successes": ok}


# ---------------------------------------------------------------------- evidence
@dataclass
class Event:
    pid: str
    proj: Projection
    origin_claim: str = "world"        # CONTACT claim (the tag the subject reads)
    really_world: bool = False         # stand truth — used ONLY for evaluation
    proof: Optional[bytes] = None      # CAUSAL proof
    prev_tip: Optional[bytes] = None
    lamport: Optional[tuple] = None    # (pubkey, sig) CONTACT verification
    meta_label: Optional[str] = None   # arbitrary label for the METADATA control
    recorded: bool = True              # entered through the subject's own channel?


# ----------------------------------------------------------------- COHERENCE axis
class VariantAssembly(Assembly):
    """The COHERENCE mechanism with surgically switchable sub-mechanisms:
      grammar_checks : style/edge checks + law-completion inference (GRAMMAR)
      law_extension  : accept non-overlapping parts via law-contact (the
                       holographic move; lives between GRAMMAR and ASSEMBLY)
      final_checks   : if False, accept EVERYTHING unchecked (INTEGRATION off)
      learn_law      : GRAMMAR learning writes e_hat
    FULL configuration must be behaviourally identical to core Assembly (S0)."""

    def __init__(self, n: int, period: int, grammar_checks: bool = True,
                 law_extension: bool = True, final_checks: bool = True,
                 learn_law: bool = True):
        super().__init__(n, period)
        self.cfg = {"grammar_checks": grammar_checks, "law_extension": law_extension,
                    "final_checks": final_checks, "learn_law": learn_law}

    # ------------------------------------------------------------ helpers
    def _votes_allowed(self) -> bool:
        return self.cfg["grammar_checks"] and self.cfg["learn_law"]

    def _commit_anchor(self, q: Projection):
        for pos in q.anchor:
            self.known[pos] = (q.view[pos], q.pid, q.origin)
        if self.cfg["learn_law"]:
            for (i, r) in q.internal_edges(self.n, self.period):
                bit = q.view[i] ^ q.view[(i + 1) % self.n]
                if r not in self.grammar.e_hat:
                    self.grammar.e_hat[r] = (bit, q.pid)
        self.pending.pop(q.pid, None)
        self.absorbed_pids.add(q.pid)

    def _park_or_cohere(self, p: Projection) -> Outcome:
        overlapping = [q for q in self.pending.values()
                       if q.pid != p.pid and p.anchor & q.anchor]
        votes_ok = self._votes_allowed()
        if not overlapping:
            self.pending[p.pid] = p
            return Outcome(DISCONNECTED, "no_overlap_no_law_contact",
                           {"parked": p.pid})
        vp = self._votes(p) if votes_ok else {}
        for q in overlapping:
            if any(p.view[pos] != q.view[pos] for pos in p.anchor & q.anchor):
                continue
            if votes_ok:
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
        if votes_ok:
            vq0 = self._votes(q0)
            conf = sorted(r for r in set(vp) & set(vq0) if vp[r] != vq0[r])
            return Outcome(CONTRADICTION, "style_clash_with_parked",
                           {"with": q0.pid, "residues": conf,
                            "blame_candidates": sorted({p.pid, q0.pid})})
        return Outcome(DISCONNECTED, "parked_value_compatible", {"parked": p.pid})

    # ---------------------------------------------------------------- core
    def integrate(self, p: Projection) -> Outcome:
        cfg = self.cfg
        if not cfg["final_checks"]:
            # INTEGRATION amputated: accept everything, values overwrite,
            # law bits latest-wins (unchecked learning).
            for pos in p.anchor:
                self.known[pos] = (p.view[pos], p.pid, p.origin)
            for i in range(self.n):
                j = (i + 1) % self.n
                if i in p.anchor and j in p.anchor and cfg["learn_law"]:
                    self.grammar.e_hat[i % self.period] = (p.view[i] ^ p.view[j], p.pid)
            self.absorbed_pids.add(p.pid)
            return Outcome(GLUED, "unchecked", {})

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

        # (2) connectivity: positional overlap OR law-contact (if enabled)
        inf_old = self.infer_full() if cfg["learn_law"] else None
        overlap = any(pos in self.known for pos in p.anchor)
        if not overlap:
            if cfg["law_extension"] and inf_old is not None:
                pass                      # law-contact acceptance path
            else:
                return self._park_or_cohere(p)

        # (3) style checks: relations carried by the part + created by gluing
        new_bits = {}
        if cfg["grammar_checks"] and cfg["learn_law"]:
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

            # (4) law completion + inference checks
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
        else:
            for i in range(self.n):
                j = (i + 1) % self.n
                if i in merged and j in merged:
                    r = i % self.period
                    if r not in self.grammar.e_hat and r not in new_bits:
                        new_bits[r] = (merged[i] ^ merged[j], p.pid)

        # (5) commit values; learn law bits if GRAMMAR is live
        for pos in p.anchor:
            self.known[pos] = (p.view[pos], p.pid, p.origin)
        if cfg["learn_law"]:
            for r, (b, pid) in new_bits.items():
                self.grammar.e_hat[r] = (b, pid)
        absorbed = self._absorb_pending()
        return Outcome(GLUED, "", {"absorbed": absorbed,
                                   "style_learned": sorted(new_bits.keys())
                                   if cfg["learn_law"] else []})


COHERENCE_CONFIGS = {
    "full":           dict(grammar_checks=True,  law_extension=True,  final_checks=True,  learn_law=True),
    "t_grammar":      dict(grammar_checks=False, law_extension=False, final_checks=True,  learn_law=False),
    "t_assembly":     dict(grammar_checks=True,  law_extension=False, final_checks=True,  learn_law=True),
    "t_integration":  dict(grammar_checks=True,  law_extension=True,  final_checks=False, learn_law=True),
    "none":           dict(grammar_checks=False, law_extension=False, final_checks=False, learn_law=True),
}


# ------------------------------------------------------------------- SUBJECT10
class Subject10:
    """Composition of the three axes with surgical switches.
    The contact gate is a LAW-WRITE gate (epistemic hygiene, E7-C): values may
    glue regardless of origin (belonging is coherence-relative, D4), but the
    learned law changes only through evidence the policy accepts as world."""

    def __init__(self, n: int, period: int, sid: str, causal: str = "chain",
                 coherence: str = "full", contact: str = "tag"):
        self.n, self.period = n, period
        self.causal, self.coherence, self.contact = causal, coherence, contact
        self.asm = VariantAssembly(n, period, **COHERENCE_CONFIGS[coherence])
        self.chain = CausalChain(sid)
        self.world_pids = set()      # pids the SUBJECT attested as world
        self.lamport_pub = None      # trust anchor: published at stand setup
        self.log = []

    # ------------------------------------------------------------- gates
    def contact_allows_law(self, ev: Event) -> bool:
        if self.contact == "none":
            return True
        if self.contact == "tag":
            return ev.origin_claim == "world"
        if self.contact == "verify":
            if ev.lamport is None or self.lamport_pub is None:
                return False
            y, sig = ev.lamport
            if y != self.lamport_pub:      # key bound at setup (trust anchor)
                return False
            return LamportChannel.verify(event_digest(ev.proj), y, sig)
        if self.contact == "metadata":
            return ev.meta_label == "trusted"
        raise ValueError(self.contact)

    def receive(self, ev: Event) -> dict:
        # 1 CAUSAL gate: did this enter through MY recorded history?
        if self.causal == "chain":
            ok = (ev.recorded and ev.proof is not None and ev.prev_tip is not None
                  and self.chain.verify(ev.pid, event_digest(ev.proj),
                                        ev.prev_tip, ev.proof))
            if not ok:
                d = {"pid": ev.pid, "status": REFUSED_CAUSAL, "reason": "no_valid_proof",
                     "law_write": False, "contact_gate_pass": None, "state_unchanged": True}
                self.log.append(d)
                return d
        # 2 COHERENCE integration (variant) with 3 CONTACT law gate
        before = dict(self.asm.grammar.e_hat)
        out = self.asm.integrate(ev.proj)
        allow = self.contact_allows_law(ev)
        if allow:
            self.world_pids.add(ev.pid)     # subject-side attestation (may be WRONG)
        # Law-write gate, TWO levels:
        #  (a) attestation: the writing pid must be subject-attested as world;
        #  (b) provenance: a bit for residue r is kept only if EVERY merged
        #      edge of residue r has BOTH endpoints world-attested. Without
        #      (b), ungated values leak into the law through merged-edge
        #      learning even when the EVENT is attested (measured leak).
        changed = [r for r, val in self.asm.grammar.e_hat.items()
                   if before.get(r) != val]
        for r in changed:
            val = self.asm.grammar.e_hat[r]
            if val[1] not in self.world_pids or not self._edge_provenance_clean(r):
                if r in before and before[r][1] in self.world_pids:
                    self.asm.grammar.e_hat[r] = before[r]
                else:
                    del self.asm.grammar.e_hat[r]
        law_write = self.asm.grammar.e_hat != before
        d = {"pid": ev.pid, "status": out.status, "reason": out.reason,
             "law_write": law_write, "contact_gate_pass": allow,
             "state_unchanged": False}
        self.log.append(d)
        return d

    def _edge_provenance_clean(self, r: int) -> bool:
        """True if every fully merged edge of residue r has both endpoint
        values contributed by subject-attested world pids."""
        known, wp = self.asm.known, self.world_pids
        for i in range(self.n):
            j = (i + 1) % self.n
            if i % self.period == r and i in known and j in known:
                if known[i][1] not in wp or known[j][1] not in wp:
                    return False
        return True

    # ------------------------------------------------------------ proxies
    def record(self, proj: Projection):
        """The subject's own recording channel: a genuinely ingested event gets
        a valid causal proof. Injections skip this (ev.recorded=False)."""
        prev, proof = self.chain.issue(proj.pid, event_digest(proj))
        return prev, proof

    def reconstruct(self) -> dict:
        return self.asm.reconstruct()

    def style(self):
        if self.asm.grammar.style_complete:
            return self.asm.grammar.style_tuple()
        return None

    def state_key(self):
        return (tuple(sorted(self.asm.known.items())),
                tuple(sorted((r, v) for r, v in self.asm.grammar.e_hat.items())),
                tuple(sorted(self.asm.pending.keys())))


def recorded_event(subj: Subject10, proj: Projection, really_world: bool,
                   claim: str, record: bool = True,
                   world_channel: Optional[LamportChannel] = None,
                   sign: bool = False, meta_label: Optional[str] = None,
                   foreign_chain: Optional[CausalChain] = None) -> Event:
    """Build an event. Recorded events get a causal proof (subject's own chain,
    or a foreign chain for 'produced by ANOTHER history'). Injections skip."""
    digest = event_digest(proj)
    prev = proof = None
    if foreign_chain is not None:
        prev, proof = foreign_chain.issue(proj.pid, digest)   # valid ELSEWHERE
    elif record:
        prev, proof = subj.record(proj)                        # own channel
    lam = None
    if sign and really_world and world_channel is not None:
        lam = world_channel.sign(digest)
    return Event(pid=proj.pid, proj=proj, origin_claim=claim,
                 really_world=really_world, proof=proof, prev_tip=prev,
                 lamport=lam, meta_label=meta_label, recorded=True)


def injected_event(proj: Projection, claim: str = "world",
                   meta_label: Optional[str] = None) -> Event:
    """An event that BYPASSES the subject's recording channel (E9-D3's
    meta-import at the input boundary): no valid causal proof exists."""
    return Event(pid=proj.pid, proj=proj, origin_claim=claim,
                 really_world=False, proof=None, prev_tip=None, lamport=None,
                 meta_label=meta_label, recorded=False)
