"""rollup — the multi-function roll-up learner (MVP gap ①).

Learns WHICH FUNCTIONS ROLL INTO WHICH RINGS — the containment structure of
a module — from the code's own wiring, never from authorship:

  bank(module)          every module-level function + the STATIC wiring:
                        the real call graph (AST: which functions call
                        which) — dataflow at function grain.
  trace_coactivation    the DYNAMIC wiring: run something REAL (the
                        module's own green test suite) under a profiler and
                        count actual caller→callee events between module
                        functions. Co-firing under a passing suite is the
                        warranted co-activation signal.
  learn_rollup          the GP loop over CONTAINMENT GENOMES: the base
                        config is ⊥ — every function its own singleton ring
                        (fully apart); mutators are MECHANICAL and Hebbian
                        (move a function to the ring holding most of its
                        wiring mass; merge the two most-connected rings);
                        fitness = Newman MODULARITY Q over the combined
                        wiring (the principled cohesion-vs-coupling
                        objective: all-in-one-ring scores 0, so the
                        degenerate roll-up cannot win). Selection/registry/
                        budget ride lfpoop.gp unchanged. NO LLM in any seat.
  emit_rollup           CODE OUT: the learned grouping as ring classes
                        (one class per ring, members bound to the REAL
                        functions, __ring_members__ as data) — and the
                        SHADOW LAW: calling through the rolled classes must
                        behave identically to the originals.

The LFP reading: ⊥ = everything discrete; each accepted merge/move is one
closure step; the learned grouping is the fixpoint of "roll together what
fires together" under the modularity objective. Stdlib + lfpoop.gp.
"""
import ast
import inspect
import sys
import textwrap

from . import gp as GP
from . import deltas as DL


def bank(module):
    """The function bank + the static call graph, AST-exact.
    Returns (functions, edges) — edges: {(caller, callee): weight}."""
    functions = {n: o for n, o in vars(module).items()
                 if inspect.isfunction(o) and o.__module__ == module.__name__}
    edges = {}
    for name, fn in functions.items():
        try:
            tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        except (OSError, TypeError):
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id in functions
                    and node.func.id != name):
                edges[(name, node.func.id)] = edges.get(
                    (name, node.func.id), 0) + 1
    return functions, edges


def trace_coactivation(functions, runner):
    """REAL dynamic wiring: run `runner` (something real — a green test
    suite) under a profiler; count caller→callee call events where both
    ends are bank functions. Returns {(caller, callee): count}."""
    names = set(functions)
    code_to_name = {fn.__code__: n for n, fn in functions.items()}
    counts = {}

    def prof(frame, event, arg):
        if event == "call":
            callee = code_to_name.get(frame.f_code)
            if not callee:
                return
            # nearest bank ANCESTOR, not the literal parent frame:
            # comprehensions/genexprs run in their own frames (pre-3.12),
            # which would otherwise swallow the true caller (found live:
            # compose→_fuse hidden behind a <listcomp> frame)
            caller, f = None, frame.f_back
            while f is not None and caller is None:
                caller = code_to_name.get(f.f_code)
                f = f.f_back
            if caller and caller != callee:
                counts[(caller, callee)] = counts.get(
                    (caller, callee), 0) + 1

    sys.setprofile(prof)
    try:
        runner()
    finally:
        sys.setprofile(None)
    return counts


def combine_wiring(static_edges, dynamic_edges, dynamic_weight=1):
    """One symmetric weighted graph from both signals."""
    w = {}
    for (a, b), c in static_edges.items():
        k = tuple(sorted((a, b)))
        w[k] = w.get(k, 0) + c
    for (a, b), c in dynamic_edges.items():
        k = tuple(sorted((a, b)))
        w[k] = w.get(k, 0) + c * dynamic_weight
    return w


def modularity(assign, wiring):
    """Newman modularity Q of a grouping over the weighted graph — the
    cohesion-vs-coupling objective; the one-ring grouping scores 0."""
    m = sum(wiring.values())
    if m == 0:
        return 0.0
    deg = {}
    for (a, b), c in wiring.items():
        deg[a] = deg.get(a, 0) + c
        deg[b] = deg.get(b, 0) + c
    q = 0.0
    rings = {}
    for fn, r in assign.items():
        rings.setdefault(r, []).append(fn)
    for members in rings.values():
        ms = set(members)
        internal = sum(c for (a, b), c in wiring.items()
                       if a in ms and b in ms)
        dsum = sum(deg.get(f, 0) for f in members)
        q += internal / m - (dsum / (2 * m)) ** 2
    return q


def hebbian_mutators(wiring):
    """MECHANICAL proposals from the wiring itself (no LLM):
    move-to-mass — relocate a function to the ring holding most of its
    wiring; merge-hottest — fuse the two rings with the heaviest
    inter-ring weight."""

    def neighbors(fn):
        out = {}
        for (a, b), c in wiring.items():
            if a == fn:
                out[b] = out.get(b, 0) + c
            elif b == fn:
                out[a] = out.get(a, 0) + c
        return out

    def move_to_mass(train_view, rng, registry):
        assign = train_view["assign"]
        genomes = []
        for fn in sorted(assign):
            mass = {}
            for other, c in neighbors(fn).items():
                r = assign.get(other)
                if r is not None and r != assign[fn]:
                    mass[r] = mass.get(r, 0) + c
            if mass:
                target = max(sorted(mass), key=lambda r: mass[r])
                genomes.append(GP.genome(
                    [DL.delta("override", ("assign", fn), target)],
                    "hebbian_move"))
        rng.shuffle(genomes)
        return genomes[:6]

    def merge_hottest(train_view, rng, registry):
        assign = train_view["assign"]
        inter = {}
        for (a, b), c in wiring.items():
            ra, rb = assign.get(a), assign.get(b)
            if ra and rb and ra != rb:
                k = tuple(sorted((ra, rb)))
                inter[k] = inter.get(k, 0) + c
        genomes = []
        for (ra, rb), _ in sorted(inter.items(), key=lambda x: -x[1])[:3]:
            ops = [DL.delta("override", ("assign", fn), ra)
                   for fn, r in sorted(assign.items()) if r == rb]
            genomes.append(GP.genome(ops, "merge_hottest"))
        return genomes

    return [move_to_mass, merge_hottest]


def learn_rollup(functions, wiring, generations=8, rng=None, registry=None):
    """⊥ (singleton rings) → the learned grouping, by gp.evolve. The
    'train view' handed to mutators is the CURRENT champion's assignment
    (the wiring is closed over — mutators see structure, not the
    objective). Returns the gp run + the final assignment."""
    base = {"assign": {fn: f"r_{fn}" for fn in sorted(functions)}}

    def eval_fn(phen):
        return {"primary": modularity(phen["assign"], wiring)}

    evaluator = GP.Evaluator(base, eval_fn)
    mutators = hebbian_mutators(wiring)
    current = dict(base)
    run = None
    for gen in range(generations):
        run = GP.evolve(base, mutators, evaluator,
                        train_view=current, generations=1, mu=2, lam=8,
                        select=GP.mu_plus_lambda, registry=registry,
                        rng=rng or __import__("random").Random(13 + gen))
        if run["survivors"]:
            champ, _ = run["survivors"][0]
            current = GP.phenotype(champ, base)
            base = current                     # roll forward: the LFP climb
            evaluator = GP.Evaluator(base, eval_fn)
    return run, current["assign"]


def emit_rollup(module, assign, class_prefix="Ring"):
    """CODE OUT: one class per learned ring, members = the REAL functions,
    membership carried as data. Returns (source, namespace) with the
    classes exec'd against the real module's functions."""
    rings = {}
    for fn, r in assign.items():
        rings.setdefault(r, []).append(fn)
    lines = [f"# GENERATED by lfpoop.rollup — learned roll-up of "
             f"{module.__name__}"]
    for r, members in sorted(rings.items()):
        cname = f"{class_prefix}_{r.replace('r_', '')}"
        lines.append(f"class {cname}:")
        lines.append(f"    __ring_members__ = {sorted(members)!r}")
        for fn in sorted(members):
            lines.append(f"    {fn} = staticmethod(_M.{fn})")
        lines.append("")
    src = "\n".join(lines)
    ns = {"_M": module}
    exec(src, ns)
    return src, ns
