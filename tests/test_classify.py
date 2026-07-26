"""classify tests — the classification tier on REAL SDK code, exact.

C1  wilson (real) → verdict pure; alphabet exactly {math: ambient:pure}.
C2  deltas._substrate_module (real, writes files) → verdict effectful;
    os in ambient:effect; open caught as an effect call.
C3  ring coupling on the REAL learned structure: roll up lfpoop.deltas
    from its static wiring, then classify crossover's source — its
    placement is compose's ring, verdict ring_coupled, exactly.
C4  the curry plan drives every free name: config → curry_to_slot,
    ring member → bind_ring, math → leave, os → isolate_effect,
    unresolvable → demand — all five actions in one real-shaped candidate,
    slots/demands lists exact.
C5  effect LOCALIZATION at block grain: a function with one effectful
    statement among pure ones — exactly that block marked, the others not.

Run: python3 tests/test_classify.py
"""
import inspect
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lfpoop import classify as C
from lfpoop import deltas as DL
from lfpoop import rollup as R
from lfpoop.gp import wilson


def main():
    checks = {}

    # C1 — real pure function.
    c1 = C.classify_source(inspect.getsource(wilson))
    checks["C1_wilson_pure_exact"] = (
        c1["verdict"] == "pure"
        and c1["alphabet"] == {"math": "ambient:pure"})

    # C2 — real effectful function.
    c2 = C.classify_source(inspect.getsource(DL._substrate_module))
    checks["C2_effectful_exact"] = (
        c2["verdict"] == "effectful"
        and c2["alphabet"].get("os") == "ambient:effect"
        and "open" in c2["effect_calls"])

    # C3 — ring coupling against the REAL learned roll-up (static wiring).
    functions, static_edges = R.bank(DL)
    wiring = R.combine_wiring(static_edges, {})
    _, assign = R.learn_rollup(functions, wiring, rng=random.Random(5))
    rings = {}
    for fn, r in assign.items():
        rings.setdefault(r, []).append(fn)
    c3 = C.classify_source(inspect.getsource(DL.crossover),
                           context={"rings": rings})
    checks["C3_ring_coupled_placement_exact"] = (
        c3["placement"] == assign["compose"]
        and c3["verdict"] == f"ring_coupled:{assign['compose']}"
        and c3["alphabet"]["compose"] == f"ring:{assign['compose']}")

    # C4 — the full curry plan, all five actions.
    src = """
def sync_report(api_key, month):
    raw = compose(fetch_rows(month), [])
    stats = math.fsum(x for x in [1.0])
    os.makedirs('/tmp/x', exist_ok=True)
    label = mystery_labeler(raw)
    return (api_key, stats, label)
"""
    plan = C.curry_plan(src, context={
        "rings": rings, "config_slots": ["api_key"]})
    checks["C4_curry_plan_exact"] = (
        plan["plan"]["api_key"] == "curry_to_slot"
        and plan["plan"]["compose"] == f"bind_ring:{assign['compose']}"
        and plan["plan"]["math"] == "leave"
        and plan["plan"]["os"] == "isolate_effect"
        and plan["plan"]["mystery_labeler"] == "demand"
        and plan["plan"]["fetch_rows"] == "demand"
        and plan["slots"] == ["api_key"]
        and plan["demands"] == ["fetch_rows", "mystery_labeler"]
        and plan["verdict"] == "effectful")

    # C5 — effect localization at block grain.
    src5 = """
def summarize(xs):
    total = math.fsum(xs)
    mean = total / len(xs)
    os.makedirs('/tmp/reports', exist_ok=True)
    return mean
"""
    blocks = C.classify_blocks(src5)
    checks["C5_effect_localized_to_one_block"] = (
        [b["effect"] for b in blocks] == [False, False, True, False]
        and blocks[2]["global_frees"] == {"os": "ambient:effect"}
        and blocks[0]["global_frees"] == {"math": "ambient:pure"})

    print()
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print(f"\nCLASSIFY: every free name lands in its alphabet and the "
          f"alphabet decides the action — pure/effectful verdicts exact on "
          f"real SDK code, placement from the learned rings, the curry plan "
          f"issuing all five actions, and effects LOCALIZED to the single "
          f"block that carries them (the one law at name grain). "
          f"{len(checks)} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
