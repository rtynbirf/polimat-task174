#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E10' CORE — round 7: closing the two open channels found in round 6.

Channel 1 (VALUE LAYER): in round 6 values were deliberately ungated
(belonging is coherence-relative, D4) -> wrong_value contamination 0.32-0.44
under ALL contact policies; reality bounced off poisoned values
(world_rejected 1.5-1.7 per trial). Fix implemented here: PROVENANCE-WEIGHTED
CONFLICT ARBITRATION — on a value clash, the side with the HIGHER trust tier
evicts the lower one; equal tiers still contradict (conservative).

  TIER_VERIFIED  = 2  Lamport signature valid against the setup trust anchor
                      (independent of the subject's own judgment)
  TIER_ATTESTED  = 1  policy-passed claim (tag/metadata) — may be a LIE
  TIER_SELF      = 0  self-claimed or gate-failed; conservative default

Channel 2 (ATTESTATION MONOTONICITY): world_pids only grew in round 6; a wrong
attestation was irrevocable. Fix: REVOCATION = epistemic downgrade, not erasure
(fact of the past is not erased):
  - revoke(pid): remove attestation, downgrade its glued VALUES to TIER_SELF
    (in place), remove+quarantine LAW BITS sourced by pid (a wrong bit poisons
    inference globally, so it is excised but recorded);
  - _reground_law(): a law bit with NO remaining fully-merged edge loses its
    grounding -> excised+recorded too;
  - a revoked pid cannot write law by tag alone; fresh VERIFIED evidence
    (new content, valid signature) re-attests CONTENT, not the revoked pid;
  - the causal chain and the quarantine ledger are append-only (audit trail).

Design constraints carried over:
  - gate order CAUSAL -> COHERENCE -> CONTACT unchanged;
  - arbitration is SILENT without provenance conflicts (S0' parity);
  - arbitration WITHOUT contact tiers has nothing to weight with (E10'-F
    control: mechanism alone is not sufficient — needs the CONTACT axis).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from holographic_core import (GLUED, CONTRADICTION, DISCONNECTED,  # noqa: E402
                              make_style, whole_from_style, aperture, propagate,
                              fidelity, Assembly, Projection, Outcome)
from holographic_e10_core import (REFUSED_CAUSAL, CausalChain, H,  # noqa: E402
                                  LamportChannel, Event, VariantAssembly,
                                  COHERENCE_CONFIGS, Subject10, recorded_event,
                                  injected_event, event_digest, flip)

TIER_SELF = 0
TIER_ATTESTED = 1
TIER_VERIFIED = 2
TIER_NAME = {0: "self", 1: "attested", 2: "verified"}


class PrimeAssembly(VariantAssembly):
    """VariantAssembly + per-position provenance (tier, pid).
    Arbitration lives at the Subject level (pre-integrate), so this subclass
    only TRACKS provenance; with no eviction it is behaviourally identical."""

    def __init__(self, n: int, period: int, **cfg):
        super().__init__(n, period, **cfg)
        self.prov = {}            # pos -> (tier, pid)

    def sync_provenance(self, pending_tier: dict):
        for pos, (v, pid, origin) in self.known.items():
            if pos not in self.prov:
                self.prov[pos] = (pending_tier.get(pid, TIER_SELF), pid)


class Subject10Prime(Subject10):
    """Subject10 + arbitration + revocation. Surgical switches:
      arbitration : value-level eviction by trust tier (channel 1)
      revocation  : attestation revocation + law re-grounding (channel 2)
    Base switches (causal/coherence/contact) inherited unchanged."""

    def __init__(self, n: int, period: int, sid: str, causal: str = "chain",
                 coherence: str = "full", contact: str = "tag",
                 arbitration: bool = True, revocation: bool = True):
        super().__init__(n, period, sid=sid, causal=causal,
                         coherence=coherence, contact=contact)
        self.asm = PrimeAssembly(n, period, **COHERENCE_CONFIGS[coherence])
        self.arbitration = arbitration
        self.revocation = revocation
        self.revoked_pids = set()      # epistemic: cannot write law by tag alone
        self.pending_tier = {}         # pid -> tier at receive time (for absorbed parts)
        self.quarantine = []           # append-only audit ledger
        self.stream = []               # (event, tier) history for re-derivation
        self.t_counter = 0

    # ------------------------------------------------------------ trust tier
    def tier_of(self, ev: Event) -> int:
        if ev.pid in self.revoked_pids:
            return TIER_SELF      # a revoked contributor attests nothing
        if self.contact == "none":
            return TIER_SELF      # no CONTACT axis: no trust distinctions,
                                  # the signature channel is not even looked at
        # verification is POLICY-ORTHOGONAL evidence (I31/I32): a valid
        # signature against the setup trust anchor outranks any label
        if ev.lamport is not None and self.lamport_pub is not None:
            y, sig = ev.lamport
            if y == self.lamport_pub and \
                    LamportChannel.verify(event_digest(ev.proj), y, sig):
                return TIER_VERIFIED
        if self.contact == "verify":
            return TIER_SELF      # claim without verification = self-grade
        if self.contact == "tag":
            return TIER_ATTESTED if ev.origin_claim == "world" else TIER_SELF
        if self.contact == "metadata":
            return TIER_ATTESTED if ev.meta_label == "trusted" else TIER_SELF
        return TIER_SELF

    # ------------------------------------------------------- quarantine/audit
    def _quarantine(self, pid: str, kind: str, payload: dict):
        self.quarantine.append({"t": self.t_counter, "pid": pid,
                                "kind": kind, **payload})

    # ------------------------------------------------------------- revocation
    def revoke(self, pid: str, cause: str) -> bool:
        """Epistemic downgrade: attestation removed, values downgraded IN PLACE,
        law bits sourced by pid excised+recorded. History (chain, ledger) kept."""
        if pid in self.revoked_pids:
            return False
        self.revoked_pids.add(pid)
        self.world_pids.discard(pid)
        self._quarantine(pid, "attestation_revoked", {"cause": cause})
        for pos, (v, src, origin) in list(self.asm.known.items()):
            if src == pid:
                self.asm.prov[pos] = (TIER_SELF, pid)   # downgrade, not delete
        if self.revocation:
            # LAW-BIT EXCISION is a revocation-channel action: with the
            # channel amputated, revocation downgrades attestation+values
            # only and the poisoned bits stay (surgical separability)
            for r in list(self.asm.grammar.e_hat):
                b, src = self.asm.grammar.e_hat[r]
                if src == pid:
                    self._quarantine(pid, "law_bit_excised",
                                     {"residue": r, "bit": b})
                    del self.asm.grammar.e_hat[r]
        return True

    def _reground_law(self):
        """Drop law bits whose residue has no remaining fully-merged edge."""
        dropped = []
        for r in list(self.asm.grammar.e_hat):
            grounded = False
            for i in range(self.n):
                j = (i + 1) % self.n
                if i % self.period == r and i in self.asm.known and j in self.asm.known:
                    grounded = True
                    break
            if not grounded:
                b, src = self.asm.grammar.e_hat.pop(r)
                self._quarantine(src, "law_bit_ungrounded", {"residue": r, "bit": b})
                dropped.append(r)
        return dropped

    # ------------------------------------------------------- arbitration pre-steps
    def _pre_evict(self, proj: Projection, tier: int) -> list:
        """Direct value clashes: incoming tier must EXCEED every clashing
        incumbent tier. Equal/lower tiers keep the old CONTRADICTION."""
        if tier == TIER_SELF:
            return []
        clashes = [pos for pos in sorted(proj.anchor)
                   if pos in self.asm.known
                   and self.asm.known[pos][0] != proj.view[pos]]
        if not clashes:
            return []
        if any(self.asm.prov.get(pos, (TIER_SELF, None))[0] >= tier
               for pos in clashes):
            return []
        evicted_pids = set()
        for pos in clashes:
            v, pid, origin = self.asm.known.pop(pos)
            self.asm.prov.pop(pos, None)
            self._quarantine(pid, "value_evicted",
                             {"pos": pos, "value": v, "by_tier": TIER_NAME[tier]})
            evicted_pids.add(pid)
        for pid in list(evicted_pids):
            self.revoke(pid, "values_evicted_by_higher_tier")
        if self.revocation:
            # law re-grounding is a REVOCATION-channel action (bit excision);
            # gating it here keeps the two channels surgically separable
            self._reground_law()
        return sorted(evicted_pids)

    def _pid_tier(self, pid: str) -> int:
        return self.pending_tier.get(pid, TIER_SELF)

    def _pre_revoke_by_verified(self, proj: Projection) -> dict:
        """VERIFIED incoming part = anchor of reality.
        (a) part's internal-edge votes contradict learned bits -> revoke
            low-tier bit sources (VERIFIED sources = world self-contradiction,
            left unresolved: noise, E11 territory);
        (b) CERTIFICATE: e_hat bits + part votes + law FORM -> forced whole.
            Valid only if the part contradicts nothing (a) silent. Covers BOTH
            complete and COMPLETING laws (a completing verified part certifies
            the ring too). Glued values disagreeing with the certificate and
            tiered below VERIFIED are downgraded; law bits contradicted by
            certified edges are excised via source-pid revocation;
        (b0) fallback when the certificate is unavailable (style contradicted
            or equal-tier ambiguity): merged edges contradicting learned bits
            are arbitrated by the TRUST ORDER — the least-trusted side yields.
        All downgrades are recorded in the append-only quarantine ledger."""
        notes = {"revoked": [], "downgraded_positions": [], "unresolved": [],
                 "radius": 0, "certified": False}
        # (a) style votes from the part's own internal edges
        part_votes = {}
        for (i, r) in proj.internal_edges(self.n, self.period):
            bit = proj.view[i] ^ proj.view[(i + 1) % self.n]
            part_votes[r] = bit
            if r in self.asm.grammar.e_hat and self.asm.grammar.e_hat[r][0] != bit:
                pid = self.asm.grammar.e_hat[r][1]
                if self._pid_tier(pid) < TIER_VERIFIED:
                    if self.revoke(pid, f"style_vote_contradicted_r{r}"):
                        notes["revoked"].append(pid)
                else:
                    notes["unresolved"].append(
                        {"kind": "verified_source_vote", "residue": r})
        # (b) certificate: e_hat + part votes, must complete or be complete
        st_bits = {r: b for r, (b, _) in self.asm.grammar.e_hat.items()}
        st_bits.update(part_votes)
        if len(st_bits) == self.period and not notes["revoked"] \
                and not notes["unresolved"]:
            st = tuple(st_bits[r] for r in range(self.period))
            a0 = min(proj.anchor)
            certified = propagate(st, self.n, self.period, a0, proj.view[a0])
            notes["certified"] = True
            # (b1) law bits contradicted by certified edges
            for r in list(self.asm.grammar.e_hat):
                bit_c = None
                for i in range(self.n):
                    j = (i + 1) % self.n
                    if i % self.period == r and i in certified and j in certified:
                        bit_c = certified[i] ^ certified[j]
                        break
                if bit_c is not None and self.asm.grammar.e_hat[r][0] != bit_c:
                    pid = self.asm.grammar.e_hat[r][1]
                    if self._pid_tier(pid) < TIER_VERIFIED:
                        if self.revoke(pid, f"certified_edge_contradicted_r{r}"):
                            notes["revoked"].append(pid)
                    else:
                        notes["unresolved"].append(
                            {"kind": "verified_source_certified", "residue": r})
            # (b2) glued values contradicted by the certified whole
            for pos in sorted(certified):
                if pos in proj.anchor or pos not in self.asm.known:
                    continue      # anchor clashes are _pre_evict's job
                if self.asm.known[pos][0] != certified[pos] and \
                        self.asm.prov.get(pos, (TIER_SELF, None))[0] < TIER_VERIFIED:
                    v, pid, origin = self.asm.known.pop(pos)
                    self.asm.prov.pop(pos, None)
                    self._quarantine(pid, "value_evicted",
                                     {"pos": pos, "value": v,
                                      "by_tier": "verified_inference"})
                    self.revoke(pid, "values_contradicted_by_certified_whole")
                    notes["downgraded_positions"].append(pos)
        elif notes["revoked"] or notes["unresolved"] or \
                len(st_bits) < self.period:
            # (b0) trust-order arbitration on merged edges (no certificate)
            mt = {pos: (self.asm.known[pos][0],
                        self.asm.prov.get(pos, (TIER_SELF, None))[0])
                  for pos in self.asm.known}
            for pos in proj.anchor:
                mt[pos] = (proj.view[pos], TIER_VERIFIED)
            for i in range(self.n):
                j = (i + 1) % self.n
                if i in mt and j in mt:
                    r = i % self.period
                    bit = mt[i][0] ^ mt[j][0]
                    if r in self.asm.grammar.e_hat and \
                            self.asm.grammar.e_hat[r][0] != bit:
                        tl = self._pid_tier(self.asm.grammar.e_hat[r][1])
                        m = min(mt[i][1], mt[j][1])
                        if tl < m:
                            # the law side is the least trusted -> excise
                            pid_l = self.asm.grammar.e_hat[r][1]
                            if self.revoke(pid_l,
                                           f"merged_edge_contradicted_r{r}"):
                                notes["revoked"].append(pid_l)
                        elif m < tl:
                            # the least-trusted endpoint(s) yield
                            for ep in (i, j):
                                if mt[ep][1] < tl and ep not in proj.anchor \
                                        and ep in self.asm.known:
                                    v, pid, origin = self.asm.known.pop(ep)
                                    self.asm.prov.pop(ep, None)
                                    self._quarantine(pid, "value_evicted",
                                                     {"pos": ep, "value": v,
                                                      "by_tier": "merged_edge"})
                                    self.revoke(pid, "value_contradicted_by_law")
                                    notes["downgraded_positions"].append(ep)
                        else:
                            notes["unresolved"].append(
                                {"kind": "equal_tier_edge", "residue": r,
                                 "edge": i})
        if notes["revoked"] or notes["downgraded_positions"]:
            self._reground_law()
        notes["radius"] = (len(notes["downgraded_positions"])
                           + len(notes["revoked"]))
        return notes

    # ------------------------------------------------------------------ receive
    def receive(self, ev: Event) -> dict:
        self.t_counter += 1
        self.sync_pending()
        self.asm.sync_provenance(self.pending_tier)
        tier = self.tier_of(ev)
        self.pending_tier[ev.pid] = tier
        self.stream.append((ev, tier))
        extra = {"tier": TIER_NAME[tier], "evictions": [], "revocations": [],
                 "downgraded_positions": [], "unresolved": [], "radius": 0,
                 "quarantined_now": 0}

        # 1 CAUSAL gate (unchanged)
        if self.causal == "chain":
            ok = (ev.recorded and ev.proof is not None and ev.prev_tip is not None
                  and self.chain.verify(ev.pid, event_digest(ev.proj),
                                        ev.prev_tip, ev.proof))
            if not ok:
                d = {"pid": ev.pid, "status": REFUSED_CAUSAL,
                     "reason": "no_valid_proof", "law_write": False,
                     "contact_gate_pass": None, "state_unchanged": True, **extra}
                self.log.append(d)
                return d

        # 2 arbitration pre-step (channel 1)
        if self.arbitration:
            evicted = self._pre_evict(ev.proj, tier)
            extra["evictions"] = evicted
            extra["quarantined_now"] += len(self.quarantine)

        # 3 revocation pre-step (channel 2, verified evidence only)
        if self.revocation and tier == TIER_VERIFIED:
            rn = self._pre_revoke_by_verified(ev.proj)
            extra["revocations"] = rn["revoked"]
            extra["downgraded_positions"] = rn["downgraded_positions"]
            extra["unresolved"] = rn["unresolved"]
            extra["radius"] = rn["radius"]
            extra["quarantined_now"] += len(self.quarantine)

        # 4 COHERENCE integration (variant, unchanged)
        before = dict(self.asm.grammar.e_hat)
        out = self.asm.integrate(ev.proj)
        allow = self.contact_allows_law(ev) and ev.pid not in self.revoked_pids
        if allow:
            self.world_pids.add(ev.pid)
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

        # 5 provenance commit
        if out.status == GLUED:
            self.asm.prov.update({pos: (tier, ev.pid) for pos in ev.proj.anchor})

        d = {"pid": ev.pid, "status": out.status, "reason": out.reason,
             "law_write": law_write, "contact_gate_pass": allow,
             "state_unchanged": False, **extra}
        self.log.append(d)
        return d

    def sync_pending(self):
        self.pending_tier.update({q.pid: self.pending_tier.get(q.pid, TIER_SELF)
                                  for q in self.asm.pending.values()})

    # ----------------------------------------------------------------- proxies
    def state_key_prime(self):
        return self.state_key() + (tuple(sorted(
            (pos, t, pid) for pos, (t, pid) in self.asm.prov.items())),)

    def quarantine_size(self) -> int:
        return len(self.quarantine)


def recorded_event_prime(subj: Subject10Prime, proj: Projection,
                         really_world: bool, claim: str,
                         world_channel: "LamportChannel | None" = None,
                         sign: bool = False) -> Event:
    """Recorded event with a valid causal proof on the subject's own chain.
    sign=True + really_world=True + world_channel -> genuine Lamport signature."""
    return recorded_event(subj, proj, really_world, claim,
                          world_channel=world_channel, sign=sign)
