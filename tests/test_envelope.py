"""envelope tests — the candidate intake's laws, exact; temp stores.

E1  a truthful candidate is admitted: genome content-addressed, the intent
    (seat/demand/rationale) recorded verbatim, derived facts alongside.
E2  CONFABULATION CAUGHT: declares missing a real read AND overclaiming a
    fake one → refused naming BOTH diffs exactly.
E3  a candidate without intent fields → refused by name (intent required).
E4  placement claims meet the wiring: against known rings, declaring the
    unsupported ring is refused naming the better-supported one; declaring
    the supported ring admits.
E5  the same source under different seats = the SAME genome id (content
    addressing survives the envelope); different source = different id.
E6  v0 blockify refusals propagate (nested def inside a candidate).

Run: python3 tests/test_envelope.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lfpoop.envelope import intake, derive, EnvelopeRefusal
from lfpoop.codething import Store

SRC = """
def widen_interval(lo, hi, pad):
    span = compute_span(lo, hi)
    scaled = span * pad
    return (lo - scaled, hi + scaled)
"""


def make(declares=None, **over):
    c = {"source": SRC, "seat": "llm:test_session",
         "answers_demand": "queue:interval-too-tight",
         "rationale": "held-out CIs are too tight at small n; widen "
                      "proportionally to the span",
         "declares": declares if declares is not None else
         {"reads": ["compute_span"], "writes": ["widen_interval"]}}
    c.update(over)
    return c


def main():
    checks = {}

    # E1 — truthful candidate admitted; intent recorded verbatim.
    with tempfile.TemporaryDirectory() as td:
        store = Store(os.path.join(td, "s.jsonl"))
        genome, rec = intake(make(), store=store)
        stored = store.records()[-1]
        checks["E1_admitted_and_ontologized"] = (
            genome["id"].startswith("g_")
            and rec["derived"]["reads"] == ["compute_span"]
            and stored["rationale"].startswith("held-out CIs")
            and stored["answers_demand"] == "queue:interval-too-tight"
            and stored["genome_id"] == genome["id"])

    # E2 — confabulated declares refused, both diffs named.
    try:
        intake(make(declares={"reads": ["numpy"],
                              "writes": ["widen_interval"]}))
        checks["E2_confabulation_caught_both_ways"] = False
    except EnvelopeRefusal as e:
        checks["E2_confabulation_caught_both_ways"] = (
            "undeclared ['compute_span']" in str(e)
            and "overclaimed ['numpy']" in str(e))

    # E3 — intent required.
    try:
        intake({"source": SRC, "seat": "llm:x",
                "declares": {"reads": ["compute_span"],
                             "writes": ["widen_interval"]}})
        checks["E3_intent_required"] = False
    except EnvelopeRefusal as e:
        checks["E3_intent_required"] = ("answers_demand" in str(e)
                                        and "rationale" in str(e))

    # E4 — placement vs wiring mass.
    rings = {"stats": ["compute_span", "wilson"],
             "io": ["read_file", "write_file"]}
    try:
        intake(make(declares={"reads": ["compute_span"],
                              "writes": ["widen_interval"],
                              "ring": "io"}), known_rings=rings)
        checks["E4_unsupported_ring_refused"] = False
    except EnvelopeRefusal as e:
        # refused either by the support floor (io holds none) or by mass
        # comparison (stats holds more) — both are honest refusals
        checks["E4_unsupported_ring_refused"] = (
            "'stats'" in str(e) or "holds NONE" in str(e))
    # and a candidate genuinely reading BOTH rings equally cannot claim
    # the wrong one (>= tie does not go to the claimant — v4 MED-5)
    tie_src = ("def mix(a):\n    return good(a) + bad(a)\n")
    tie_rings = {"g": ["good"], "b": ["bad"]}
    try:
        intake({"source": tie_src, "seat": "llm:x", "answers_demand": "q",
                "rationale": "r",
                "declares": {"reads": ["good", "bad"], "writes": ["mix"],
                             "ring": "b"}}, known_rings=tie_rings)
        checks["E4c_tie_not_to_claimant"] = False
    except EnvelopeRefusal as e:
        checks["E4c_tie_not_to_claimant"] = ">=" in str(e)
    g_ok, _ = intake(make(declares={"reads": ["compute_span"],
                                    "writes": ["widen_interval"],
                                    "ring": "stats"}), known_rings=rings)
    checks["E4b_supported_ring_admits"] = g_ok["id"].startswith("g_")

    # E5 — content addressing survives the envelope.
    g1, _ = intake(make(seat="llm:alice"))
    g2, _ = intake(make(seat="llm:bob",
                        rationale="entirely different thinking"))
    g3, _ = intake(make(source=SRC.replace("* pad", "* pad * 2"),
                        declares={"reads": ["compute_span"],
                                  "writes": ["widen_interval"]}))
    checks["E5_content_addressed"] = (g1["id"] == g2["id"]
                                      and g1["id"] != g3["id"])

    # E6 — blockify refusals propagate.
    nested = "def f(x):\n    def g():\n        return x\n    return g()\n"
    try:
        derive(nested)
        checks["E6_v0_refusal_propagates"] = False
    except Exception as e:
        checks["E6_v0_refusal_propagates"] = "nested" in str(e)

    print()
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print(f"\nENVELOPE: LLM code enters as CHECKED CLAIMS — truthful "
          f"declares admit as cold content-addressed genomes with intent "
          f"ontologized verbatim; confabulated reads/writes and unsupported "
          f"placement claims are refused naming the exact diff; candidates "
          f"without intent are inadmissible. {len(checks)} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
