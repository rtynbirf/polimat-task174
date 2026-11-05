#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Механическое доказательство дефектов v2.8.0 перед выпуском v2.9.0.

D1: Predicate/PredicateRegistry — мёртвый код: TypedRuleEngine.entails
    никогда не обращается к реестру предикатов; все проверки захардкожены.
    Следствие: «typed rule engine исполняет предикаты» — декорация.
D2: Claim не имеет depends_on; per-claim вывод не знает о зависимостях
    между утверждениями. Следствие: assertion-claim закрывается чужим
    evidence, пока его предпосылка (capability-claim) не доказана;
    UNKNOWN не распространяется по зависимостям.
"""
import importlib.util
import sys

PATH = "/home/z/my-project/agent_1/polymath_agent_v2.8.0.py"

spec = importlib.util.spec_from_file_location("v280", PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def make_engine():
    return m.TypedRuleEngine(m.RuleRegistry(), m.PredicateRegistry())


RULE = "claim_witnessed_by_successful_action_observation"


def d1_dead_predicates() -> bool:
    claim = m.Claim("claim:1", "capability:write_file выполнена", "capability", "write_file")
    ev = [m.EvidenceObject("evidence:1", "", "observation", "step:1",
                           m.sha256_hex(b"x"), "2026-08-28T00:00:00+00:00",
                           True, "write_file", True)]
    contract = m.EvidenceContract("claim:1", required_capability="write_file")

    ok_normal = make_engine().entails(RULE, claim, ev, contract)

    # Выжигаем реестр предикатов: заменяем на объект без единого метода.
    eng = make_engine()
    eng.predicates = object()
    ok_burned = eng.entails(RULE, claim, ev, contract)

    # Полностью пустой реестр — тоже без эффекта.
    eng2 = m.TypedRuleEngine(m.RuleRegistry(), m.PredicateRegistry())
    eng2.predicates._predicates.clear()
    ok_empty = eng2.entails(RULE, claim, ev, contract)

    print(f"D1 entails(normal)={ok_normal} entails(burned registry)={ok_burned} "
          f"entails(empty registry)={ok_empty}")
    return ok_normal == ok_burned == ok_empty  # True => предикаты ни на что не влияют


def d2_no_claim_dependency_propagation() -> bool:
    state = {
        "criteria": ["capability:write_file выполнена успешно",
                     "итоговый отчёт записан"],
        "required_capabilities": ["write_file", "web_search"],
        "ledger": [
            {"step": 1, "action": "web_search", "ok": True, "kind": "net",
             "obs_brief": "search results"},
        ],
    }
    proof = m.ProofCompiler(state).compile()
    derivations = state.get("derivations", [])
    assertion_claims = [c.id for c in m.ProofCompiler(state).claims if c.claim_type == "assertion"]
    valid_for_assertion = [d for d in derivations
                           if d.get("claim_id") in assertion_claims
                           and d.get("valid") and d.get("evidence_ids")]
    has_depends_on = hasattr(m.Claim(id="x", text="y"), "depends_on")
    print(f"D2 valid derivation for assertion claim while prerequisite "
          f"capability claim unproven: {len(valid_for_assertion)}")
    print(f"D2 Claim.depends_on exists: {has_depends_on}")
    # Дефект = вывод для assertion валиден, а выразить зависимость нельзя.
    return len(valid_for_assertion) > 0 and not has_depends_on


if __name__ == "__main__":
    r1 = d1_dead_predicates()
    r2 = d2_no_claim_dependency_propagation()
    print(f"D1 dead predicates reproduced: {r1}")
    print(f"D2 no UNKNOWN propagation reproduced: {r2}")
    sys.exit(0 if (r1 and r2) else 1)
