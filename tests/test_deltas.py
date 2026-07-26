"""LFPOOP-DELTAS tests — the laws are TESTS, not docstrings. Exact, temp
stores, exhaustive over the whole small algebra where feasible.

Laws: identity (two-sided), associativity (EXHAUSTIVE over all atom
triples, refusal branches agreeing), closure (composites stay in the
vocabulary), the action law apply∘compose = apply∘apply (all atom pairs on
a base config, refusals agreeing), crossover (merge/dedupe/CONFLICT-named),
fork (lineage recorded, witness history honestly EMPTIED —
non-transferability), fibration (BEHAVIORAL preservation: an intact
projection preserves, a corrupting substrate is CAUGHT).

Run: python3 tests/test_deltas.py
"""
import itertools
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lfpoop import deltas as DL
from lfpoop import codething as CT
from lfpoop.climb import kleene_climb


def atoms():
    """The whole small algebra: every op × 2 paths × 2 values."""
    out = []
    for path in (("a",), ("b", "c")):
        out.append(DL.delta("exclude", path))
        for v in (1, 2):
            out.append(DL.delta("override", path, v))
            out.append(DL.delta("add", path, v))
    return out


def result_or_error(fn):
    try:
        return ("ok", fn())
    except DL.DeltaError as e:
        return ("refused", type(e).__name__)


def main():
    checks = {}
    A = atoms()

    # identity, two-sided, over every atom
    checks["identity_two_sided"] = all(
        DL.compose([d], DL.identity()) == [d]
        and DL.compose(DL.identity(), [d]) == [d] for d in A)

    # associativity — EXHAUSTIVE over all atom triples (10^3), with the
    # refusal branch agreeing on both groupings
    ok = True
    for d1, d2, d3 in itertools.product(A, repeat=3):
        left = result_or_error(lambda: DL.compose(DL.compose([d1], [d2]), [d3]))
        right = result_or_error(lambda: DL.compose([d1], DL.compose([d2], [d3])))
        if left != right:
            ok = False
            break
    checks["associativity_exhaustive_with_refusals"] = ok

    # closure: every successful composite stays inside the vocabulary
    ok = True
    for d1, d2 in itertools.product(A, repeat=2):
        tag, val = result_or_error(lambda: DL.compose([d1], [d2]))
        if tag == "ok" and any(d["op"] not in DL.OPS for d in val):
            ok = False
    checks["closure_in_vocabulary"] = ok

    # the action law over all atom pairs on a base config: WHEREVER the
    # (partial) composition is defined, applying it equals applying the
    # sequence — including agreeing on WHEN application refuses. Vacuity
    # guarded: the defined region must be substantial.
    base = {"a": 10, "b": {"c": 20}}
    ok, defined = True, 0
    for d1, d2 in itertools.product(A, repeat=2):
        tag, comp = result_or_error(lambda: DL.compose([d1], [d2]))
        if tag == "refused":
            continue                    # composition partial — law vacuous
        defined += 1
        seq = result_or_error(
            lambda: DL.apply_program(DL.apply_program(base, [d1]), [d2]))
        via = result_or_error(lambda: DL.apply_program(base, comp))
        if seq != via:
            ok = False
            break
    checks["action_law_where_defined"] = ok and defined >= 40

    # refusals are NAMED
    try:
        DL.apply_program(base, [DL.delta("add", ("a",), 5)])
        checks["add_on_existing_named"] = False
    except DL.DeltaError as e:
        checks["add_on_existing_named"] = "('a',)" in str(e)
    try:
        DL.apply_program(base, [DL.delta("exclude", ("zz",))])
        checks["exclude_absent_named"] = False
    except DL.DeltaError as e:
        checks["exclude_absent_named"] = "('zz',)" in str(e)
    try:
        DL.compose([DL.delta("override", ("a",), 1)],
                   [DL.delta("add", ("a",), 2)])
        checks["add_after_op_named"] = False
    except DL.DeltaError as e:
        checks["add_after_op_named"] = "must be first" in str(e)

    # crossover: merge, dedupe, and CONFLICTS surfaced by path
    g1 = {"name": "g1", "deltas": [DL.delta("override", ("a",), 1),
                                   DL.delta("add", ("x",), 7)]}
    g2 = {"name": "g2", "deltas": [DL.delta("override", ("a",), 1),
                                   DL.delta("override", ("b", "c"), 9)]}
    child, conflicts = DL.crossover(g1, g2)
    checks["crossover_merge_dedupe"] = (
        conflicts == [] and child["name"] == "g1xg2"
        and child["lineage"] == ["g1", "g2"]
        and sorted(d["path"] for d in child["deltas"])
        == [("a",), ("b", "c"), ("x",)])
    g3 = {"name": "g3", "deltas": [DL.delta("override", ("a",), 999)]}
    _, conflicts = DL.crossover(g1, g3)
    checks["crossover_conflict_named"] = (
        len(conflicts) == 1 and conflicts[0]["path"] == ("a",)
        and conflicts[0]["a"]["value"] == 1
        and conflicts[0]["b"]["value"] == 999)

    # fork: lineage recorded; witnessing DOES NOT transfer
    with tempfile.TemporaryDirectory() as td:
        store = CT.Store(os.path.join(td, "store.jsonl"))
        rec = CT.mirror(main)
        rec["name"] = "parent"
        rec["golden_history"] = [["execution", "testing"]]
        store.append(rec)
        child = DL.fork("parent", "coord1", store, witness="test")
        located = kleene_climb("parent@coord1", store)
        checks["fork_lineage_and_nontransfer"] = (
            child["name"] == "parent@coord1"
            and child["golden_history"] == []
            and child["provenance"] == [
                "forked_from:parent:at:coord1:by:test"]
            and located["position"]["witnessed"] == []
            and kleene_climb("parent", store)["position"]["witnessed"]
            == ["execution", "testing"])
        try:
            DL.fork("ghost", "c", store, witness="test")
            checks["fork_missing_named"] = False
        except DL.DeltaError as e:
            checks["fork_missing_named"] = "ghost" in str(e)

    # fibration: preservation is BEHAVIORAL, and corruption is CAUGHT
    spec = {"name": "doubler", "source": "def f(x):\n    return x * 2\n"}
    with tempfile.TemporaryDirectory() as td:
        probe = lambda mod: mod.f(21)
        r1 = DL.materialize(spec, "module", td, probe)
        r2 = DL.materialize(spec, "package", td, probe)
        checks["fibration_preserves_behaviorally"] = (
            r1["preserved"] and r2["preserved"]
            and r1["truth"] == 42 and r2["projected"] == 42)

        def corrupting(spec, workspace):           # a BROKEN fiber map
            p = os.path.join(workspace, f"{spec['name']}_bad.py")
            with open(p, "w") as f:
                f.write(spec["source"].replace("* 2", "* 3"))
            return p
        DL.register_substrate("corrupting", corrupting)
        r3 = DL.materialize(spec, "corrupting", td, probe)
        checks["fibration_catches_corruption"] = (
            not r3["preserved"] and r3["projected"] == 63)
        try:
            DL.materialize(spec, "nope", td, probe)
            checks["unknown_substrate_named"] = False
        except DL.DeltaError as e:
            checks["unknown_substrate_named"] = "nope" in str(e)

    print()
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print(f"\nLFPOOP-DELTAS: identity + associativity (exhaustive, refusals "
          f"agreeing) + closure + the action law are TESTS; crossover names "
          f"its conflicts; fork records lineage and honestly strips "
          f"witnessing (non-transferability); the fibration checks "
          f"preservation by BEHAVIOR and catches a corrupting substrate. "
          f"{len(checks)} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
