"""LFPOOP-DELTAS — the treeshell category_theory shape, with the laws REAL.

heaven-tree-repl's category_theory.py carried the right shape (a program
FAMILY = a fixed base + a stream of typed config deltas; an instance = the
closure of composing deltas over the base; generation = forking the whole at
a new coordinate) but every law was a docstring: bind was bare application,
composites left the operation vocabulary, "preserves structure" was a
key-presence check. This module is that shape with the checks existing:

  * TYPED delta ops — override / add / exclude — on paths into a config.
    A delta PROGRAM is an ordered list; compose() = concatenate + NORMALIZE
    (per-path fold), so composition is CLOSED (results re-enter the same
    vocabulary) and ASSOCIATIVE BY CONSTRUCTION (normalization of the
    flattened sequence is grouping-independent) — and both laws are
    PROPERTY-TESTED over the whole small algebra, refusals included.
    Illegal sequences refuse, naming why (add must be FIRST at its path).
  * The ACTION LAW (functoriality): apply(c, compose(p, q)) ==
    apply(apply(c, p), q) — tested, refusal branches agreeing too.
  * GENES ARE DELTAS: crossover(a, b) = operad composition of two genes'
    delta programs — disjoint targets merge, identical ones dedupe, and
    CONFLICTS (same target, different result) surface as NAMED gaps;
    never a silent merge. The GP loop's missing operator, from the algebra.
  * fork() = generate_sibling done honestly: a stored node forked WHOLE at
    a new coordinate with lineage recorded — and its witness history EMPTY,
    because autonomy grades never transfer (non-transferability): a fork
    re-enters at the bottom of its own cooling ladder.
  * The FIBRATION = a substrate registry whose preservation check is
    BEHAVIORAL — the projected artifact is imported and probed and must
    BEHAVE identically to the source of truth — never key-presence.

Stdlib only.
"""
import copy
import importlib.util
import os

OPS = ("override", "add", "exclude")


class DeltaError(ValueError):
    """A refused delta operation — carries the named reason."""


def delta(op: str, path, value=None) -> dict:
    if op not in OPS:
        raise DeltaError(f"unknown delta op {op!r} — vocabulary is {OPS}")
    return {"op": op, "path": tuple(path), "value": value}


# ── composition: concat + normalize ⇒ closed AND associative ────────────────

def _fuse(seq):
    """Fold one path's op sequence to a single delta (or refuse, named).

    Only two same-path shapes are representable in the vocabulary WITHOUT
    changing when the program refuses (the action law is exact, so fusion
    must preserve refusal behavior, not just final values):
      add(v…) followed by overrides  → add(last v)     (still refuses on
                                                        an existing path)
      override(v…) followed by overrides → override(last v)
    Everything else — any mix involving exclude, or add not first — is NOT
    representable as one delta with identical refusal behavior, so compose
    REFUSES, naming why (composition is deliberately partial; the sequence
    itself stays applicable as separate program steps)."""
    if len(seq) == 1:
        return dict(seq[0])
    path = seq[0]["path"]
    ops = [d["op"] for d in seq]
    if "exclude" in ops:
        raise DeltaError(
            f"composition mixing exclude with other ops at {path} is not "
            f"representable in the vocabulary with the same refusal "
            f"behavior (refused; keep exclude as its own program step)")
    if "add" in ops[1:]:
        raise DeltaError(
            f"add at {path} composed AFTER another op on the same path — "
            f"add must be first at its path (refused; use override)")
    return delta(ops[0], path, seq[-1]["value"])


def compose(*programs):
    """Compose delta programs. Result is a delta program in the SAME
    vocabulary; normalization works on the flattened sequence, so grouping
    cannot matter — associativity by construction, tested anyway."""
    flat = [d for p in programs for d in p]
    by_path, order = {}, []
    for d in flat:
        if d["path"] not in by_path:
            by_path[d["path"]] = []
            order.append(d["path"])
        by_path[d["path"]].append(d)
    return [_fuse(by_path[p]) for p in order]


def identity():
    """The identity program."""
    return []


# ── the action on configs ───────────────────────────────────────────────────

def _walk(cfg, path):
    cur = cfg
    for k in path[:-1]:
        cur = cur.setdefault(k, {})
    return cur


def apply_program(config: dict, program) -> dict:
    """Act on a config. Refusals are named: add refuses on an existing
    path, exclude refuses on an absent one (missing ≠ fine — fail loud)."""
    out = copy.deepcopy(config)
    for d in program:
        if not d["path"]:
            raise DeltaError("empty path — a delta must target something")
        parent = _walk(out, d["path"])
        leaf = d["path"][-1]
        if d["op"] == "add":
            if leaf in parent:
                raise DeltaError(
                    f"add at {d['path']}: already present (refused; "
                    f"override to replace)")
            parent[leaf] = copy.deepcopy(d["value"])
        elif d["op"] == "override":
            parent[leaf] = copy.deepcopy(d["value"])
        elif d["op"] == "exclude":
            if leaf not in parent:
                raise DeltaError(
                    f"exclude at {d['path']}: not present (refused; "
                    f"nothing to exclude)")
            del parent[leaf]
    return out


# ── genes are deltas: crossover = operad composition, conflicts named ───────

def crossover(gene_a: dict, gene_b: dict):
    """gene = {name, deltas}. Returns (child_gene, conflicts). Disjoint
    targets merge; identical deltas dedupe; same-target DIFFERENT outcomes
    are CONFLICTS, surfaced by path — never silently resolved."""
    fused_a = {d["path"]: d for d in compose(gene_a["deltas"])}
    fused_b = {d["path"]: d for d in compose(gene_b["deltas"])}
    child, conflicts = [], []
    for path in list(fused_a) + [p for p in fused_b if p not in fused_a]:
        da, db = fused_a.get(path), fused_b.get(path)
        if da and db and da != db:
            conflicts.append({"path": path, "a": da, "b": db})
        else:
            child.append(da or db)
    name = f"{gene_a['name']}x{gene_b['name']}"
    return ({"name": name, "deltas": child,
             "lineage": [gene_a["name"], gene_b["name"]]}, conflicts)


# ── fork(): the sibling at a new coordinate, lineage recorded ───────────────

def fork(name: str, coordinate: str, store, witness: str) -> dict:
    """Fork a stored node whole at a new coordinate. Structure travels;
    WITNESS HISTORY DOES NOT (non-transferability: grades are earned per
    instance, never inherited) — the fork re-enters cooling at the bottom."""
    hist = [r for r in store.history(name) if r.get("kind") != "witness"]
    if not hist:
        raise DeltaError(f"fork: no such node {name!r} in the store")
    if not witness:
        raise DeltaError("fork requires a witness")
    src = hist[-1]
    child = copy.deepcopy(src)
    child["name"] = f"{name}@{coordinate}"
    child["golden_history"] = []                  # witnessing never transfers
    child["provenance"] = [
        f"forked_from:{name}:at:{coordinate}:by:{witness}"]
    return store.append(child)


# ── the fibration: substrates with a BEHAVIORAL preservation check ──────────

SUBSTRATES = {}


def register_substrate(name: str, project_fn):
    """project_fn(spec, workspace) -> path of the projected artifact."""
    SUBSTRATES[name] = project_fn


def _import_path(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(s)
    s.loader.exec_module(mod)
    return mod


def materialize(spec: dict, substrate: str, workspace: str, probe):
    """Project spec = {name, source} onto a registered substrate, then check
    preservation BEHAVIORALLY: probe(module) must return the SAME value on
    the source of truth and on the projection. Key-presence proves nothing;
    behavior is the fiber map's structure."""
    if substrate not in SUBSTRATES:
        raise DeltaError(f"unknown substrate {substrate!r} — registered: "
                         f"{sorted(SUBSTRATES)}")
    truth_path = os.path.join(workspace, f"_truth_{spec['name']}.py")
    with open(truth_path, "w") as f:
        f.write(spec["source"])
    projected_path = SUBSTRATES[substrate](spec, workspace)
    truth = probe(_import_path(f"truth_{spec['name']}", truth_path))
    shadow = probe(_import_path(f"proj_{spec['name']}_{substrate}",
                                projected_path))
    return {"path": projected_path, "preserved": truth == shadow,
            "truth": truth, "projected": shadow}


def _substrate_module(spec, workspace):
    p = os.path.join(workspace, f"{spec['name']}.py")
    with open(p, "w") as f:
        f.write(spec["source"])
    return p


def _substrate_package(spec, workspace):
    pkg = os.path.join(workspace, spec["name"] + "_pkg")
    os.makedirs(pkg, exist_ok=True)
    open(os.path.join(pkg, "__init__.py"), "w").close()
    p = os.path.join(pkg, "impl.py")
    with open(p, "w") as f:
        f.write(spec["source"])
    return p


register_substrate("module", _substrate_module)
register_substrate("package", _substrate_package)
