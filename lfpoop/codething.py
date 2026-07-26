"""CodeThing → GraphMirrorEntity: real Python artifacts as Node records.

mirror(obj) introspects a real function/class/module into a record honoring
the Manual's NODE_FIELDS: provenance, realization level, graph identity
(= sha256 of the actual source — stable across runs, changes when the source
changes), adapters, generated_*, tests, golden history. Store = append-only
JSONL (crystallization is an append, never a rewrite). Stdlib only.
"""
import hashlib
import inspect
import json
import os

from . import ontology as O

DEFAULT_STORE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".lfpoop", "store.jsonl")


def _source_of(obj) -> str:
    if inspect.ismodule(obj):
        return open(obj.__file__).read()
    return inspect.getsource(obj)


def _kind(obj) -> str:
    if inspect.ismodule(obj):
        return "module"
    if inspect.isclass(obj):
        return "class"
    if inspect.isfunction(obj):
        return "function"
    return "callable"


def _level(obj) -> str:
    # honest default: a bare function is at "function"; anything importable
    # and running as part of a package is at "program". Higher rungs are
    # EARNED through the compiler loop, never assigned at mirror time.
    return "function" if inspect.isfunction(obj) else "program"


def mirror(obj) -> dict:
    """A real artifact's Node record — graph identity from its source."""
    src = _source_of(obj)
    name = getattr(obj, "__name__", str(obj))
    module = getattr(obj, "__module__", name)
    return {
        "name": name,
        "kind": _kind(obj),
        "python_path": f"{module}.{name}" if not inspect.ismodule(obj) else name,
        "graph_identity": hashlib.sha256(src.encode()).hexdigest(),
        "realization_level": _level(obj),
        "provenance": [f"mirrored:{_kind(obj)}"],
        "adapters": [],
        "generated_documentation": [],
        "generated_agents": [],
        "generated_packages": [],
        "tests": [],
        "golden_history": [],
    }


class Store:
    """Append-only JSONL node store. Records are never rewritten; the latest
    record for a name is the current state, the full stream is provenance."""

    def __init__(self, path: str = DEFAULT_STORE):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def append(self, record: dict) -> dict:
        with open(self.path, "a") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
        return record

    def records(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path) as f:
            return [json.loads(line) for line in f if line.strip()]

    def latest(self, name: str):
        recs = [r for r in self.records() if r.get("name") == name]
        return recs[-1] if recs else None

    def history(self, name: str):
        return [r for r in self.records() if r.get("name") == name]


def external_witnesses(store: Store, name: str):
    """External (handler-seat) witness records for this artifact — the
    compiler's own process re-runs (witness_id 'process_rerun:*') never
    count. The gauge computes; the handler accepts."""
    return [r for r in store.records()
            if r.get("kind") == "witness" and r.get("name") == name
            and not str(r.get("witness_id", "")).startswith("process_rerun")]


def accept_witness(store: Store, name: str, witness_id: str) -> dict:
    """THE HANDLER SEAT: an external witness (a human, a separate verifier
    agent) accepts the artifact. Who witnessed is recorded verbatim — this is
    never called by the compiler on its own output."""
    if not witness_id or witness_id.startswith("process_rerun"):
        raise ValueError("an external witness needs a real, non-process id")
    return store.append({"kind": "witness", "name": name,
                         "witness_id": witness_id})


def agentify(name: str, store: Store, repo_root: str = None) -> dict:
    """The six rites, granted ONLY against THIS NODE's own artifacts —
    never against repo files or other artifacts' records. No artifact, no
    rite. Returns {"is_agent": bool, "granted": [...], "missing": [...]}."""
    hist = [r for r in store.history(name) if r.get("kind") != "witness"]
    latest = hist[-1] if hist else None    # witness records are NOT node state
    identities = {r.get("graph_identity") for r in hist if r.get("graph_identity")}
    checks = {
        # its OWN generated documentation exists
        "explanation": bool(latest and latest.get("generated_documentation")),
        # it actually EVOLVED: ≥2 distinct source identities in its history
        "evolution": len(identities) >= 2,
        # it has tests AND a recorded cooled run that includes testing
        "testing": bool(latest and latest.get("tests")
                        and any("testing" in g
                                for r in hist
                                for g in r.get("golden_history", []))),
        # its OWN generated package artifact exists
        "export": bool(latest and latest.get("generated_packages")),
        # an EXTERNAL witness accepted it (the handler seat)
        "review": bool(external_witnesses(store, name)),
        "graph_identity": bool(latest and latest.get("graph_identity")),
    }
    granted = [r for r in O.AGENT_RITES if checks[r]]
    missing = [r for r in O.AGENT_RITES if not checks[r]]
    return {"is_agent": not missing, "granted": granted, "missing": missing}
