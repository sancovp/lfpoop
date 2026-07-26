"""Domain + UCO-retrofit tests: the Scott order, the fixpoint, the loop as a
uco.Chain, the D:D→D meta check, and the Prolog cross-check (exact).

Run: python3 tests/test_domain_chains.py   (uco importable; janus optional)
"""
import asyncio
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:
    import uco  # noqa: F401
except ImportError:
    sys.path.insert(0, os.path.expanduser("~/repo/universal-chain-ontology"))

from lfpoop import domain as D
from lfpoop import ontology as O
from lfpoop import prolog as P
from lfpoop import chains as C


def main():
    checks = {}
    rng = random.Random(7)
    states = list(D.all_states())
    checks["domain_size_exact"] = len(states) == 10 * 2**7 * 2**6

    # Partial order: reflexive (exhaustive), ⊥ and ⊤ bounds (exhaustive),
    # antisymmetry + transitivity (seeded samples).
    checks["reflexive_exhaustive"] = all(D.leq(s, s) for s in states)
    checks["bottom_top_bounds_exhaustive"] = all(
        D.leq(D.BOTTOM, s) and D.leq(s, D.TOP) for s in states)
    anti = trans = True
    for _ in range(20000):
        a, b, c = rng.choice(states), rng.choice(states), rng.choice(states)
        if D.leq(a, b) and D.leq(b, a) and a != b:
            anti = False
        if D.leq(a, b) and D.leq(b, c) and not D.leq(a, c):
            trans = False
    checks["antisym_transitive_sampled"] = anti and trans

    # Lubs exist for arbitrary subsets (finite lattice ⇒ dcpo ⇒ every element
    # compact ⇒ a Scott domain): lub is an upper bound and least (sampled).
    lub_ok = True
    for _ in range(2000):
        sub = [rng.choice(states) for _ in range(rng.randint(1, 5))]
        j = D.lub(sub)
        if not all(D.leq(s, j) for s in sub):
            lub_ok = False
        cand = D.lub([rng.choice(states)])          # a random competitor
        if all(D.leq(s, cand) for s in sub) and not D.leq(j, cand):
            lub_ok = False
    checks["lub_upper_and_least_sampled"] = lub_ok

    # F is inflationary — EXHAUSTIVE over all 81,920 states.
    checks["F_inflationary_exhaustive"] = all(
        D.leq(s, D.closure_step(s)) for s in states)

    # F is monotone — sampled comparable pairs (t = lub(s, r) ⊒ s).
    mono = True
    for _ in range(20000):
        s, r = rng.choice(states), rng.choice(states)
        t = D.lub([s, r])
        if not D.leq(D.closure_step(s), D.closure_step(t)):
            mono = False
    checks["F_monotone_sampled"] = mono

    # The Kleene chain: ascending, exact length 23 (7 cooling + 6 rites +
    # 9 rungs + ⊥), lands on ⊤, and ⊤ is a fixpoint.
    chain = D.kleene()
    checks["kleene_exact"] = (
        len(chain) == 1 + len(O.COOLING) + len(O.AGENT_RITES) + len(O.LADDER) - 1
        and all(D.leq(a, b) for a, b in zip(chain, chain[1:]))
        and chain[-1] == D.TOP and D.closure_step(D.TOP) == D.TOP)

    # SELF-MODEL: the SDK is an element of its own domain; its distance to
    # the fixpoint is computed, exact, and honest (not ⊤, not faked).
    sdk = D.sdk_state()
    checks["sdk_in_domain_below_top"] = D.leq(sdk, D.TOP) and sdk != D.TOP
    # exact distance, cross-validated: the Kleene iteration count must equal
    # the ARITHMETIC of what's missing (rungs + unwitnessed cooling + missing
    # rites) — two independent computations of the same number. The full
    # 15→9→7 transition semantics live in test_full.py on a temp store.
    arithmetic = ((len(O.LADDER) - 1 - sdk.level)
                  + len(O.COOLING) - len(sdk.witnessed)
                  + len(O.AGENT_RITES) - len(sdk.rites))
    checks["sdk_distance_exact"] = len(D.kleene(sdk)) - 1 == arithmetic

    # UCO retrofit: the loop-chain IS the Manual's verb order; a Chain is a
    # Link (homoiconic nesting works); conditional verbs skip without effect.
    loop = C.build_loop_chain()
    checks["loop_chain_is_manual_order"] = [l.name for l in loop.links] == O.LOOP
    from uco import Chain as UChain, Link as ULink
    checks["chain_is_link_homoiconic"] = isinstance(UChain("outer", [loop]),
                                                   ULink)
    r = asyncio.run(loop.execute({}))
    fired = dict(r.context["trace"])
    checks["conditional_verbs_skip_without_effect"] = (
        fired["goldenize"] is False and fired["improve_compiler"] is False
        and fired["observe"] is True)

    # The D:D→D meta check (compoctopus's MetaCompiler move).
    meta = asyncio.run(C.meta_fixpoint_check())
    checks["meta_compiled_equals_handwritten"] = meta["compiled_equals_handwritten"]
    checks["meta_self_application_idempotent"] = meta["self_application_idempotent"]

    # Executing the UCO chain IS computing the fixpoint: drive_node's state
    # sequence equals the domain's Kleene chain, exactly.
    final, cycles, seq = asyncio.run(C.drive_node())
    checks["uco_execution_is_kleene"] = (final == D.TOP and seq == chain
                                         and cycles == len(chain))

    # Prolog cross-check (iff janus+swipl): same chain length, same fixpoint.
    try:
        import janus_swi as janus
        P.write()
        janus.consult(P.PL_PATH)
        # underscore-prefix compound-bound vars (the janus serialization
        # discipline): only N/Eq/FA (int + atoms) cross the bridge.
        r = janus.query_once(
            "lfpoop:bottom_state(_B), lfpoop:kleene(_B, _C), length(_C, N),"
            " last(_C, _F), lfpoop:top_state(_T),"
            " (_F == _T -> Eq = yes ; Eq = no), term_to_atom(_F, FA)")
        top_atom = (f"state({len(O.LADDER)-1},"
                    f"[{','.join(sorted(O.COOLING))}],"
                    f"[{','.join(sorted(O.AGENT_RITES))}])")
        checks["prolog_kleene_identical"] = (
            r is not None and r.get("N") == len(chain)
            and r.get("Eq") == "yes" and r.get("FA") == top_atom)
    except ImportError:
        print("  SKIP  prolog cross-check (janus/swipl not present here)")

    print()
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print(f"\nLFPOOP domain: a Scott domain with F monotone+inflationary, "
          f"lfp(F)=⊤ by Kleene in {len(chain)-1} steps; the loop runs on UCO "
          f"and its execution IS the iteration; the SDK models itself at "
          f"distance {len(D.kleene(sdk)) - 1} from its own fixpoint. "
          f"{len(checks)} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
