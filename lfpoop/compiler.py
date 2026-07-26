"""The LFPOOPCompiler — the Manual's loop verbs made REAL, on the UCO chain.

One cycle compiles one spec (source + its test) through:
  materialize — write into a QUARANTINE dir (never the package: sandbox law)
  execute     — import and run it there
  test        — its unittest suite, in a SUBPROCESS
  graph       — mirror the artifact into the append-only store
  quarantine  — assert the artifact exists ONLY in the sandbox
  witnessed_effect — tests green AND an INDEPENDENT second-process re-run
                (process-level independence; the self-witnessing defect law —
                the process that built it never solely certifies it)
  goldenize   — cool the artifact's Node with REAL witnesses only (each
                cooling step maps to an artifact check; no artifact, no claim)
  improve_compiler — the compiler re-mirrors ITSELF into the store (its own
                Node accretes provenance: the fold's substrate)

Driven by chains.build_loop_chain — executing the UCO chain IS running the
compiler. Stdlib + uco only.
"""
import importlib.util
import os
import subprocess
import sys

from . import codething
from . import ontology as O
from .chains import build_loop_chain


_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_tests(test_path: str, workspace: str) -> bool:
    env = dict(os.environ)
    env["PYTHONPATH"] = _REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run(
        [sys.executable, "-m", "unittest",
         os.path.splitext(os.path.basename(test_path))[0], "-q"],
        cwd=workspace, capture_output=True, text=True, timeout=120, env=env)
    return r.returncode == 0


class LfpoopCompilerRun:
    """One spec through the loop. spec = {name, source, test_source}."""

    def __init__(self, spec: dict, workspace: str, store: codething.Store):
        self.spec, self.workspace, self.store = spec, workspace, store
        os.makedirs(workspace, exist_ok=True)
        self.paths = {}
        self.artifact = None
        self.results = {"tests_green": False, "witnessed": False,
                        "quarantined": False, "cooled": [], "golden": False}

    # ── the verbs (each is a loop impl: ctx in, ctx out) ──
    def observe(self, ctx):
        ctx["spec"] = self.spec
        return ctx

    def classify(self, ctx):
        ctx["kind"] = "code_thing"
        return ctx

    def infer_next_closures(self, ctx):
        ctx["closure"] = {"materialize": self.spec["name"]}
        return ctx

    def materialize(self, ctx):
        src = os.path.join(self.workspace, f"{self.spec['name']}.py")
        tst = os.path.join(self.workspace, f"test_{self.spec['name']}.py")
        with open(src, "w") as f:
            f.write(self.spec["source"])
        with open(tst, "w") as f:
            f.write(self.spec["test_source"])
        self.paths = {"src": src, "test": tst}
        return ctx

    def execute(self, ctx):
        s = importlib.util.spec_from_file_location(
            self.spec["name"], self.paths["src"])
        mod = importlib.util.module_from_spec(s)
        s.loader.exec_module(mod)          # raises on failure — fail loud
        self.artifact = mod
        return ctx

    def test(self, ctx):
        self.results["tests_green"] = _run_tests(self.paths["test"],
                                                 self.workspace)
        return ctx

    def graph(self, ctx):
        rec = codething.mirror(self.artifact)
        rec["provenance"].append(f"materialized_in:{self.workspace}")
        rec["tests"].append(os.path.basename(self.paths["test"]))
        # the artifact's OWN generated documentation (its docstring, rendered
        # to a real file) — the explanation rite's artifact, per-node.
        doc = (self.artifact.__doc__ or "").strip()
        if doc:
            doc_path = os.path.join(self.workspace,
                                    f"{self.spec['name']}.md")
            with open(doc_path, "w") as f:
                f.write(f"# {self.spec['name']}\n\n{doc}\n")
            rec["generated_documentation"].append(doc_path)
        self.node_record = self.store.append(rec)
        return ctx

    def quarantine(self, ctx):
        pkg = os.path.dirname(os.path.abspath(codething.__file__))
        self.results["quarantined"] = (
            os.path.dirname(self.paths["src"]) != pkg
            and os.path.exists(self.paths["src"]))
        return ctx

    def witnessed_effect(self, ctx):
        # HONEST LABEL (verifier 2026-07-25): this is a PROCESS-LEVEL
        # re-execution — a second subprocess re-runs the same suite. It
        # catches flakiness, NOT the self-witnessing defect: same code, same
        # machine, same builder. It is recorded as witness_id
        # 'process_rerun:*' which external_witnesses() deliberately does NOT
        # count. TRUE independent witnessing is the HANDLER SEAT
        # (codething.accept_witness — a human or separate verifier agent).
        reexecuted = self.results["tests_green"] and _run_tests(
            self.paths["test"], self.workspace)
        self.results["witnessed"] = reexecuted
        if reexecuted:
            self.store.append({"kind": "witness", "name": self.spec["name"],
                               "witness_id": "process_rerun:compiler"})
        ctx["witnessed_effect"] = reexecuted and self.results["quarantined"]
        return ctx

    def _relational_validation(self) -> bool:
        """The artifact validates RELATIONALLY: any rings it defines pass the
        assembly-time alphabet/leak enforcement (their declared relations are
        coherent). Artifacts defining no rings validate trivially-but-
        honestly: the check is stated as vacuous for them."""
        from . import onion
        rings = [v for v in vars(self.artifact).values()
                 if isinstance(v, type) and hasattr(v, "__ring_adds__")]
        for r in rings:
            declared = (set(r.__ring_adds__) | set(r.__ring_requires__))
            if onion._body_accesses(r) - declared:
                return False
        return True

    def goldenize(self, ctx):
        # THE GAUGE: six of seven cooling steps are the compiler's own
        # per-artifact checks. The seventh (independent_witnessing) is THE
        # HANDLER'S — only an external witness record (accept_witness)
        # satisfies it; the compiler CANNOT goldenize its own output alone.
        # golden here is therefore honest: False until the handler accepts.
        history_before = len(self.store.history(self.spec["name"]))
        checks = {
            "execution": self.artifact is not None,
            "testing": self.results["tests_green"] and self.results["witnessed"],
            "relational_validation": self._relational_validation(),
            "observation": self.store.latest(self.spec["name"]) is not None,
            "independent_witnessing": bool(
                codething.external_witnesses(self.store, self.spec["name"])),
            "provenance": len(set(self.node_record["provenance"])) >= 2,
            "append_only_crystallization": history_before >= 1,
        }
        node = O.Node(self.spec["name"])
        for step in O.COOLING:
            if checks[step]:
                node.cool(step, f"compiler_run:{self.spec['name']}")
        self.results["cooled"] = [s for s in O.COOLING if checks[s]]
        self.results["golden"] = node.golden
        golden_rec = dict(self.node_record)
        golden_rec["golden_history"] = (
            golden_rec["golden_history"] + [self.results["cooled"]])
        golden_rec["provenance"] = golden_rec["provenance"] + [
            f"goldenized:{len(self.results['cooled'])}/{len(O.COOLING)}"]
        self.store.append(golden_rec)
        return ctx

    def improve_compiler(self, ctx):
        # the compiler's own Node accretes: re-mirror THIS module.
        me = sys.modules[__name__]
        rec = codething.mirror(me)
        rec["provenance"].append(
            f"improve_compiler:after:{self.spec['name']}")
        self.store.append(rec)
        return ctx

    def impls(self):
        return {v: getattr(self, v) for v in O.LOOP if hasattr(self, v)}


async def compile_spec(spec, workspace, store):
    """Run one full loop cycle over the spec via the UCO chain."""
    run = LfpoopCompilerRun(spec, workspace, store)
    chain = build_loop_chain(run.impls())
    result = await chain.execute({})
    return run, result
