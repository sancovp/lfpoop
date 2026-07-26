"""REAL self-application: the compiler compiles the SDK's own source.

Not mirroring-as-ceremony (the verifier's 2026-07-25 HIGH finding): this
module runs onion.py's ACTUAL source through the full loop — materialized in
quarantine, executed, tested by a real suite against the quarantined copy,
process-reexecuted, graphed, goldenized (gauge 6/7; the 7th belongs to the
handler) — then mirrors the remaining SDK modules. accept via
codething.accept_witness is the HANDLER's move, never made here.
"""
import os

from . import chains, codething, domain, ontology, onion, prolog
from .compiler import compile_spec

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ONION_SELFTEST = '''\
import unittest
from lfpoop_onion import ring, stack, StackError


class Base:
    def provenance(self):
        return ["origin"]


@ring(adds=("witness",), requires=("provenance",))
class W:
    def witness(self):
        return len(self.provenance())


@ring(adds=("leaky",), requires=())
class Leaky:
    def leaky(self):
        return self.provenance()      # undeclared access — must be refused


class TestQuarantinedOnion(unittest.TestCase):
    def test_stack_and_refusals(self):
        C = stack("S", Base, [W])
        self.assertEqual(C().witness(), 1)
        with self.assertRaises(StackError):
            stack("Bad", Base, [Leaky])       # the leak is refused, named

    def test_requires_enforced(self):
        with self.assertRaises(StackError):
            stack("NoCap", object, [W])


if __name__ == "__main__":
    unittest.main()
'''


async def self_apply(store: codething.Store, workspace: str):
    """Compile lfpoop.onion through the loop; mirror the rest. Returns the
    compiler run. The handler seat (external witness) is NOT taken here."""
    src = open(os.path.join(_ROOT, "lfpoop", "onion.py")).read()
    spec = {"name": "lfpoop_onion", "source": src,
            "test_source": ONION_SELFTEST}
    run, result = await compile_spec(spec, workspace, store)
    from . import compiler as compiler_mod
    for mod in (ontology, domain, chains, onion, codething,
                compiler_mod, prolog):
        store.append(codething.mirror(mod))
    return run, result
