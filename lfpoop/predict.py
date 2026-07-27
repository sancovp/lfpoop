"""predict — the combination predictor (MVP ③): the ONE public instruction
for "predict code based on what it is."

Because it's LFP, everything combines the same way — so prediction is
DEDUCTION over structure, never guessing. This module answers, for any pool
of units, the one question at code grain:

  predict(pool, base)      for EVERY unit: its status —
                             active     (all capabilities met, all slots
                                         bound — it conducts now)
                             buildable  (capabilities derivable from the
                                         pool; slots still to bind — the
                                         binding residue NAMED)
                             blocked    (capability residue NAMED: what
                                         must ARRIVE before it can exist)
  closure(pool, base)      the capability LFP: everything that becomes
                           available from base by composing the pool —
                           the fixpoint, plus the order it grew in.
  derivations(pool, target) HOW a capability can be made: every acyclic
                           derivation chain through the pool, each with
                           its own residue (unmet leaves). "How do I get
                           X" = an enumeration, not an opinion.
  residue(pool, target)    the minimal named demand set across the best
                           derivations — what must arrive, by name.

UNITS are normalized from the artifacts the SDK already produces — the
ontology IS the input (the coverage law: the pool's extent is the
prediction's extent):

  unit_from_ring(RingSpec)      onion2 rings: provides=adds,
                                requires=requires, slots=verb slots
  unit_from_class(cls)          class-ified classes: __curried__ → slots,
                                provides=[impl or methods]
  unit_from_callable(fn)        bare callables: provides=[name],
                                requires=free external names (alphabets)
  unit(...)                     anything else, by hand, as data

TWO KINDS OF RESIDUE, kept distinct because they are answered differently:
capability residue (a unit/feature must ARRIVE — grow the pool) vs binding
residue (a slot must be BOUND — supply configuration). The prediction is
itself DATA (deterministic, JSON-able). Stdlib + lfpoop.alphabets.
"""
from .alphabets import classify_name


def unit(name, provides=(), requires=(), slots=()):
    return {"name": name, "provides": sorted(provides),
            "requires": sorted(requires), "slots": sorted(slots)}


def unit_from_ring(ring):
    """An onion2 RingSpec as a unit."""
    return unit(ring.name, provides=list(ring.adds),
                requires=list(ring.requires),
                slots=sorted({s for v in ring.verbs for s in v.slots}))


def unit_from_class(cls):
    """A class-ified class (classify.py output) as a unit."""
    provides = [getattr(cls, "__impl__", cls.__name__)]
    methods = getattr(cls, "__residue__", None)
    return unit(cls.__name__, provides=provides,
                requires=[], slots=list(getattr(cls, "__curried__", ())))


def unit_from_callable(fn, context=None):
    """A bare callable as a unit — requires = its free external names
    (the alphabets decider, minus pure ambience which imposes nothing)."""
    import inspect
    from .alphabets import classify_source
    c = classify_source(inspect.getsource(fn), context)
    requires = sorted(n for n, a in c["alphabet"].items()
                      if a not in ("ambient:pure",))
    return unit(fn.__name__, provides=[fn.__name__], requires=requires)


# ── the capability LFP ──────────────────────────────────────────────────────

def closure(pool, base=()):
    """The fixpoint of composition: (available, order, active_units)."""
    available = set(base)
    active, order, changed = [], [], True
    while changed:
        changed = False
        for u in pool:
            if u["name"] in active:
                continue
            if set(u["requires"]) <= available:
                active.append(u["name"])
                new = set(u["provides"]) - available
                available |= set(u["provides"])
                order.extend(sorted(new))
                changed = True
    return sorted(available), order, sorted(active)


def predict(pool, base=(), bound=()):
    """THE ONE QUESTION, answered for every unit at once. Returns data:
    {unit: {status, capability_residue, binding_residue}}."""
    available, _, active = closure(pool, base)
    bound = set(bound)
    out = {}
    for u in pool:
        cap_residue = sorted(set(u["requires"]) - set(available))
        bind_residue = sorted(set(u["slots"]) - bound)
        if cap_residue:
            status = "blocked"
        elif bind_residue:
            status = "buildable"
        else:
            status = "active"
        out[u["name"]] = {"status": status,
                          "capability_residue": cap_residue,
                          "binding_residue": bind_residue}
    return out


# ── derivations: HOW a capability can be made ───────────────────────────────

def derivations(pool, target, base=(), _seen=None, max_depth=8):
    """Every acyclic way the pool can produce `target`, each as
    {"chain": [unit names, dependency-first], "residue": [unmet leaves]}.
    A capability in `base` derives trivially (empty chain)."""
    if target in set(base):
        return [{"chain": [], "residue": []}]
    _seen = _seen or frozenset()
    if target in _seen or max_depth == 0:
        return []
    outs = []
    providers = [u for u in pool if target in u["provides"]]
    if not providers:
        return [{"chain": [], "residue": [target]}]
    for u in providers:
        sub_chains, sub_residue = [], []
        ok = True
        for req in u["requires"]:
            ds = derivations(pool, req, base,
                             _seen | {target}, max_depth - 1)
            if not ds:
                ok = False
                break
            best = min(ds, key=lambda d: (len(d["residue"]),
                                          len(d["chain"])))
            sub_chains.extend(c for c in best["chain"]
                              if c not in sub_chains)
            sub_residue.extend(r for r in best["residue"]
                               if r not in sub_residue)
        if ok:
            outs.append({"chain": sub_chains + [u["name"]],
                         "residue": sorted(sub_residue)})
    return outs


def residue(pool, target, base=()):
    """The minimal named demand set for `target` — what must ARRIVE."""
    ds = derivations(pool, target, base)
    if not ds:
        return [target]
    best = min(ds, key=lambda d: (len(d["residue"]), len(d["chain"])))
    return best["residue"]
