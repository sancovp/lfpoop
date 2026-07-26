"""rollup tests — the roll-up learner on a REAL module (lfpoop.deltas).

R1  the bank is AST-exact: the real function set; known true call edges
    (compose→_fuse, apply_program→_walk, crossover→compose,
    materialize→_import_path) present with correct direction.
R2  REAL dynamic wiring: running the module's own green test suite
    (tests/test_deltas.py main()) under the profiler yields real
    caller→callee counts — known co-fires observed.
R3  THE LEARNING: from ⊥ (every function a singleton ring), the mechanical
    Hebbian mutators + modularity fitness roll the module up — the learned
    grouping puts the algebra together (compose+_fuse), the action together
    (apply_program+_walk), the fibration together
    (materialize+_import_path), SEPARATES algebra from fibration, and
    modularity strictly climbed from ⊥'s score. No LLM in any seat.
R4  CODE OUT + SHADOW: the emitted ring classes carry membership as data
    and behave identically to the originals through the rolled surface.

Run: python3 tests/test_rollup.py
"""
import io
import os
import random
import sys
import contextlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lfpoop import rollup as R
from lfpoop import deltas as DL
from lfpoop import gp as GP


def main():
    checks = {}
    functions, static_edges = R.bank(DL)

    # R1 — bank exact; known true edges present.
    expected_fns = {"delta", "_fuse", "compose", "identity", "_walk",
                    "apply_program", "crossover", "fork",
                    "register_substrate", "_import_path", "materialize",
                    "_substrate_module", "_substrate_package"}
    checks["R1_bank_exact"] = (
        set(functions) == expected_fns
        and ("compose", "_fuse") in static_edges
        and ("apply_program", "_walk") in static_edges
        and ("crossover", "compose") in static_edges
        and ("materialize", "_import_path") in static_edges)

    # R2 — real traces from the module's own green suite.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import test_deltas

    def run_suite():
        with contextlib.redirect_stdout(io.StringIO()):
            assert test_deltas.main() == 0      # the suite must be GREEN
    dynamic = R.trace_coactivation(functions, run_suite)
    checks["R2_real_trace_coactivation"] = (
        dynamic.get(("compose", "_fuse"), 0) > 0
        and dynamic.get(("apply_program", "_walk"), 0) > 0
        and dynamic.get(("materialize", "_import_path"), 0) > 0)

    # R3 — the learner rolls ⊥ up into the real structure.
    wiring = R.combine_wiring(static_edges, dynamic)
    bot = {fn: f"r_{fn}" for fn in functions}
    q_bot = R.modularity(bot, wiring)
    run, assign = R.learn_rollup(functions, wiring,
                                 rng=random.Random(5))
    q_learned = R.modularity(assign, wiring)
    together = lambda a, b: assign[a] == assign[b]
    checks["R3_learned_grouping"] = (
        together("compose", "_fuse")
        and together("apply_program", "_walk")
        and together("materialize", "_import_path")
        and not together("compose", "materialize")     # algebra ≠ fibration
        and q_learned > q_bot)
    print(f"  modularity: bottom={q_bot:.3f} -> learned={q_learned:.3f}; "
          f"rings={len(set(assign.values()))} "
          f"(from {len(functions)} singletons)")

    # R4 — code out + the shadow law through the rolled surface.
    src, ns = R.emit_rollup(DL, assign)
    ring_of = {fn: f"Ring_{r.replace('r_', '')}"
               for fn, r in assign.items()}
    Ralg = ns[ring_of["compose"]]
    d1 = DL.delta("override", ("x",), 1)
    d2 = DL.delta("override", ("x",), 2)
    checks["R4_shadow_through_rings"] = (
        sorted(Ralg.__ring_members__) == sorted(
            fn for fn, r in assign.items() if assign["compose"] == r)
        and Ralg.compose([d1], [d2]) == DL.compose([d1], [d2])
        and "__ring_members__" in src)

    print()
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print(f"\nROLLUP: the real module's containment structure LEARNED from "
          f"its own wiring — static call graph + real traces of its green "
          f"suite, Hebbian mutators, modularity fitness, from ⊥ to "
          f"{len(set(assign.values()))} rings — and the rolled surface "
          f"behaves identically. Which functions roll into which is now an "
          f"output, not an authorship. {len(checks)} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
