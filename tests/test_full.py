"""LFPOOP-FULL tests, v2 (post-adversarial-verification, 2026-07-25):
temp stores only (no persistent pollution); capability ENFORCEMENT (the
leak refusal); the gauge/handler split (the compiler cannot goldenize its
own output — 6/7 until an external witness accepts); per-node rites; and
REAL self-application — the compiler compiles onion.py's actual source,
with the full 15→9→7 distance transition asserted in ONE run.

Run: python3 tests/test_full.py   (needs uco importable)
"""
import asyncio
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:
    import uco  # noqa: F401
except ImportError:
    sys.path.insert(0, os.path.expanduser("~/repo/universal-chain-ontology"))

from lfpoop import codething, compiler, domain, onion, selfapply  # noqa: E402
from lfpoop import ontology as O  # noqa: E402

GEN_RING_SOURCE = '''\
"""gen_audit_ring — a compiler-generated onion ring module (its own doc)."""
from lfpoop.onion import ring

@ring(adds=("audit",), requires=("provenance",))
class GenAuditRing:
    """A GENERATED categorical mixin: audit = read the provenance beneath."""
    def audit(self):
        return list(self.provenance())
'''

GEN_RING_TEST = '''\
import unittest
from lfpoop.onion import stack, StackError
from gen_audit_ring import GenAuditRing

class Base:
    def provenance(self):
        return ["origin"]

class Bare:
    pass

class TestGenAuditRing(unittest.TestCase):
    def test_stacks_and_audits(self):
        C = stack("Audited", Base, [GenAuditRing])
        self.assertEqual(C().audit(), ["origin"])

    def test_refuses_without_capability(self):
        with self.assertRaises(StackError):
            stack("Broken", Bare, [GenAuditRing])

if __name__ == "__main__":
    unittest.main()
'''

GAUGE_STEPS = [s for s in O.COOLING if s != "independent_witnessing"]


def main():
    checks = {}

    # ── the onion runtime ──
    class Base:
        def provenance(self):
            return ["origin"]

    @onion.ring(adds=("witness",), requires=("provenance",))
    class WitnessRing:
        def witness(self):
            return f"witnessed:{len(self.provenance())}"

    @onion.ring(adds=("golden",), requires=("witness",))
    class GoldenRing:
        def golden(self):
            return self.witness().startswith("witnessed")

    C = onion.stack("Cooled", Base, [GoldenRing, WitnessRing])
    checks["stack_runtime_synthesis"] = (
        C().golden() is True
        and [k.__name__ for k in C.__mro__[:3]]
        == ["Cooled", "GoldenRing", "WitnessRing"])
    try:
        onion.stack("Bad", Base, [GoldenRing])   # golden needs witness beneath
        checks["stack_refuses_named_gap"] = False
    except onion.StackError as e:
        checks["stack_refuses_named_gap"] = "witness" in str(e)

    # ENFORCED capability: an undeclared self.X access is a LEAK, refused
    # with the leaked name — by construction at assembly time, not policy.
    @onion.ring(adds=("sneak",), requires=())
    class LeakyRing:
        def sneak(self):
            return self.provenance()             # undeclared access

    try:
        onion.stack("Leak", Base, [LeakyRing])
        checks["capability_leak_refused_named"] = False
    except onion.StackError as e:
        checks["capability_leak_refused_named"] = "provenance" in str(e)

    C2 = onion.curried(Base)(WitnessRing)(GoldenRing).build("Cooled")
    checks["curried_equals_stack"] = (
        [k.__name__ for k in C2.__mro__] == [k.__name__ for k in C.__mro__])
    spec = onion.to_data(C)
    C3 = onion.stack_from_data(spec, {"Base": Base})
    checks["data_roundtrip_identical"] = (
        onion.to_data(C3) == spec and C3().golden() is True)

    # ── codething mirroring ──
    def sample():
        return 1

    def sample2():
        return 2

    r1, r1b, r2 = (codething.mirror(sample), codething.mirror(sample),
                   codething.mirror(sample2))
    checks["mirror_identity_stable_and_source_sensitive"] = (
        r1["graph_identity"] == r1b["graph_identity"]
        and r1["graph_identity"] != r2["graph_identity"])

    with tempfile.TemporaryDirectory() as td:
        st = codething.Store(os.path.join(td, "s.jsonl"))
        st.append(r1)
        st.append(r2)
        checks["store_append_only"] = (
            len(st.records()) == 2 and st.latest("sample")["name"] == "sample")

        # ── the compiler loop on a generated ring — TEMP store, no
        #    persistent pollution ──
        store = codething.Store(os.path.join(td, "run.jsonl"))
        ws = os.path.join(td, "quarantine")
        spec_ = {"name": "gen_audit_ring", "source": GEN_RING_SOURCE,
                 "test_source": GEN_RING_TEST}
        run, result = asyncio.run(compiler.compile_spec(spec_, ws, store))
        checks["loop_cycle_all_verbs_fired"] = (
            result.status.value == "success"
            and dict(result.context["trace"])["goldenize"] is True)
        checks["artifact_tested_reexecuted_quarantined"] = (
            run.results["tests_green"] and run.results["witnessed"]
            and run.results["quarantined"])

        # THE GAUGE/HANDLER SPLIT: the compiler alone cools exactly 6/7 —
        # independent_witnessing is NOT claimable by the builder; golden is
        # honestly False until the handler accepts.
        checks["gauge_cools_6_of_7_golden_false"] = (
            run.results["cooled"] == GAUGE_STEPS
            and run.results["golden"] is False)
        checks["process_rerun_never_counts_as_external"] = (
            codething.external_witnesses(store, "gen_audit_ring") == [])

        # the handler seat (LABELED stand-in: this test acts as the handler):
        codething.accept_witness(store, "gen_audit_ring",
                                 "handler_stand_in:test_full")
        checks["handler_acceptance_recorded"] = bool(
            codething.external_witnesses(store, "gen_audit_ring"))

        # ── per-node rites: exactly the artifact-backed subset; a fresh
        #    ring is NOT an agent (missing evolution + export — honest) ──
        rites = codething.agentify("gen_audit_ring", store, ROOT)
        checks["rites_exact_artifact_backed_subset"] = (
            rites["granted"] == ["explanation", "testing", "review",
                                 "graph_identity"]
            and rites["missing"] == ["evolution", "export"]
            and rites["is_agent"] is False)

        # ── REAL SELF-APPLICATION + the exact 15→9→7 transition, one run ──
        store2 = codething.Store(os.path.join(td, "self.jsonl"))
        d0 = len(domain.kleene(domain.sdk_state(store2.path))) - 1
        run2, _ = asyncio.run(selfapply.self_apply(
            store2, os.path.join(td, "self_ws")))
        d1 = len(domain.kleene(domain.sdk_state(store2.path))) - 1
        codething.accept_witness(store2, "lfpoop_onion",
                                 "handler_stand_in:test_full")
        d2 = len(domain.kleene(domain.sdk_state(store2.path))) - 1
        checks["self_application_compiler_really_ran"] = (
            run2.results["tests_green"] and run2.results["quarantined"]
            and run2.results["cooled"] == GAUGE_STEPS
            and store2.latest("lfpoop_onion") is not None)
        checks["transition_15_9_7_exact"] = (d0, d1, d2) == (15, 9, 7)

    print()
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print(f"\nLFPOOP-FULL v2: capability leaks refused at assembly; the "
          f"compiler gauges 6/7 and CANNOT self-goldenize (the 7th is the "
          f"handler's); rites are per-node (a fresh ring is honestly not an "
          f"agent); and the compiler COMPILED onion.py itself — distance "
          f"15→9→7, each step from a real artifact. {len(checks)} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
