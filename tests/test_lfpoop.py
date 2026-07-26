"""LFPOOP SDK tests — stdlib only; the Prolog cross-check runs iff janus+swipl
exist (skipped cleanly otherwise, stated loudly, never faked).

Run: python3 tests/test_lfpoop.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lfpoop import ontology as O
from lfpoop import prolog as P


def main():
    checks = {}

    # The ladder + no-skip law.
    checks["ladder_order"] = (O.next_level("function") == "program"
                              and O.next_level("compiler_improvement") is None)
    checks["no_skip"] = (O.admissible_transition("skill", "manual")
                         and not O.admissible_transition("skill", "agent"))

    # The one question, answered as data.
    n = O.Node("thing_1")
    a = n.next_admissible_closure()
    checks["one_question_exact"] = (
        a["question"] == "what is my next admissible closure?"
        and a["level"] == "function" and a["next_level"] == "program"
        and a["unwitnessed_cooling"] == O.COOLING and a["golden"] is False)

    # Goldenization: hot until every step witnessed; crystallization appends.
    for step in O.COOLING[:-1]:
        n.cool(step, "test_witness")
    checks["hot_until_last_step"] = not n.golden and 0 < n.heat < 0.2
    n.cool(O.COOLING[-1], "test_witness")
    checks["golden_when_all_witnessed"] = (n.golden and n.heat == 0.0
                                           and len(n.golden_history) == 1)

    # Provenance is append-only and external mutation doesn't stick.
    before = len(n.provenance)
    n.provenance.append("forged")
    checks["provenance_append_only"] = len(n.provenance) == before

    # Advance requires a witness and moves exactly one rung.
    try:
        n.advance("")
        checks["advance_needs_witness"] = False
    except ValueError:
        checks["advance_needs_witness"] = True
    n.advance("test_witness")
    checks["advance_one_rung"] = n.realization_level == "program"

    # Agentification = all six rites.
    for r in O.AGENT_RITES[:-1]:
        n.receive_rite(r, "test_witness")
    was_agent_early = n.is_agent
    n.receive_rite(O.AGENT_RITES[-1], "test_witness")
    checks["agent_after_six_rites"] = (not was_agent_early) and n.is_agent

    # The compiler loop honors the witnessed_effect conditional.
    class Dud:
        def witnessed_effect(self):
            return False
    class Live:
        def witnessed_effect(self):
            return True
    dud = {v for (v, fired, _) in O.run_loop(Dud()) if fired}
    live = {v for (v, fired, _) in O.run_loop(Live()) if fired}
    checks["loop_conditional"] = (
        "goldenize" not in dud and "improve_compiler" not in dud
        and "goldenize" in live and "improve_compiler" in live)

    # THE ROUNDTRIP — one source, two substrates, same data.
    text = P.render()
    parsed = P.parse(text)
    checks["roundtrip_python_prolog"] = (
        parsed["ladder"] == O.LADDER
        and parsed["architecture_stage"] == O.ARCHITECTURE
        and parsed["cooling_step"] == O.COOLING
        and parsed["loop_verb"] == O.LOOP
        and parsed["pipeline_stage"] == O.PIPELINE
        and parsed["agent_rite"] == O.AGENT_RITES
        and parsed["node_field"] == O.NODE_FIELDS)

    # The checked-in .pl equals the render (the projection is current).
    on_disk = open(P.PL_PATH).read() if os.path.exists(P.PL_PATH) else ""
    checks["generated_pl_current"] = on_disk == text

    # OPTIONAL cross-substrate check: ask Prolog the one question and compare
    # with Python's answer. Runs iff janus+swipl exist; SKIPPED loudly if not.
    try:
        import janus_swi as janus
        janus.consult(P.PL_PATH)
        r = janus.query_once(
            "lfpoop:next_admissible_closure(skill, [execution, testing], _C),"
            " term_to_atom(_C, A)")
        want_missing = [s for s in O.COOLING if s not in ("execution", "testing")]
        want = f"closure(manual,[{','.join(want_missing)}])"
        checks["prolog_answers_the_question_identically"] = (
            r is not None and r.get("A") == want)
    except ImportError:
        print("  SKIP  prolog cross-check (janus/swipl not present here)")

    print()
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print(f"\nLFPOOP SDK: the Manual is data in Python and Prolog, "
          f"{len(checks)} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
