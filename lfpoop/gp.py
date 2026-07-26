"""lfpoop.gp — genetic programming as a full suite, riding the delta algebra.

What the grammar loop's (1+1) hill-climb lacked, made structural:

  * GENOME = a delta PROGRAM (lfpoop.deltas ops — the law-tested algebra),
    CONTENT-ADDRESSED (id = sha256 of the canonical op tree; no names, the
    B7 ruling) with pedigree (parents, seat, reads) as metadata that does
    NOT enter the hash — same ops, same identity, whoever bred them.
  * PHENOTYPE = apply the program to the domain's base config (genotype →
    phenotype is deltas.apply_program — the compile step is the algebra's
    action, nothing bespoke).
  * REGISTRY = append-only, content-keyed: a genome is EVALUATED AT MOST
    ONCE, ever (the loop-until-dry dedup); REJECT verdicts are the lab-grade
    BESTIARY — mutators consult the registry and never re-propose the dead.
  * FITNESS = a VECTOR of named metrics; rate metrics carry (k, n) and a
    Wilson interval, so ±1-of-58 is visibly noise, not a verdict.
  * SELECTION = a pluggable strategy: hillclimb (the old policy), tournament,
    mu_plus_lambda, pareto_front — the open selection-policy fork becomes a
    config choice.
  * CROSSOVER = deltas.crossover (operad composition; same-target conflicts
    surface by name, never silently merged); children carry both parents.
  * THE GOODHART GUARD BY CONSTRUCTION: the Evaluator is built once with the
    held-out oracle CLOSED OVER (held in no attribute); mutators are called
    with the TRAIN VIEW ONLY — the API hands them nothing else.
  * PROMOTION = the gauge/handler split at GP grain: a champion's fitness
    record is the GAUGE; promotion requires an EXTERNAL witness accepted
    through the handler seat (codething.accept_witness) — the loop cannot
    crown its own output.

Stdlib + lfpoop.deltas + lfpoop.codething only.
"""
import hashlib
import json
import math
import random

from . import deltas as DL
from .codething import Store, external_witnesses


# ── genome: content-addressed delta program ─────────────────────────────────

def genome(ops, proposed_by, reads="train_view", parents=()):
    g = {"ops": list(ops), "proposed_by": proposed_by, "reads": reads,
         "parents": list(parents)}
    g["id"] = genome_id(g)
    return g


def genome_id(g):
    """Content address: the ops tree alone — pedigree/seat never enter."""
    canon = json.dumps([[d["op"], list(d["path"]), d.get("value")]
                        for d in g["ops"]], sort_keys=True)
    return "g_" + hashlib.sha256(canon.encode()).hexdigest()[:16]


def phenotype(g, base_config):
    """Genotype → phenotype = the delta algebra's action. Refusals (illegal
    programs) propagate as DeltaError — an unviable genome, named."""
    return DL.apply_program(base_config, g["ops"])


def crossover(a, b, proposed_by="crossover"):
    """Breed via the operad composition; conflicts surface, never merge."""
    child_gene, conflicts = DL.crossover(
        {"name": a["id"], "deltas": a["ops"]},
        {"name": b["id"], "deltas": b["ops"]})
    if conflicts:
        return None, conflicts
    return genome(child_gene["deltas"], proposed_by,
                  reads=f"{a['reads']}+{b['reads']}",
                  parents=[a["id"], b["id"]]), []


# ── fitness: vectors with honest uncertainty ────────────────────────────────

def wilson(k, n, z=1.96):
    """Wilson score interval for a rate — so a ±1 delta is visibly noise."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    lo, hi = max(0.0, center - half), min(1.0, center + half)
    # the boundary cases are exact mathematically (k=0 → lo=0, k=n → hi=1);
    # float rounding must not make the interval exclude p̂ itself
    if k == 0:
        lo = 0.0
    if k == n:
        hi = 1.0
    return (lo, hi)


def rate(k, n):
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": (k / n if n else 0.0),
            "ci": (lo, hi)}


def significantly_above(m_a, m_b):
    """Rate metric a exceeds b beyond overlap of Wilson intervals."""
    return m_a["ci"][0] > m_b["ci"][1]


class Evaluator:
    """THE SEALED GAUGE. Built once with the held-out oracle; the oracle is
    closed over in the evaluate function — this object carries NO attribute
    holding it, so nothing downstream can read what it must not."""

    def __init__(self, base_config, eval_fn):
        # eval_fn(phen) -> {"metric": {"k":..,"n":..} | float}; it closes
        # over the held-out data itself.
        self._base = dict(base_config)

        def _evaluate(g):
            phen = phenotype(g, self._base)
            out = {}
            for name, v in eval_fn(phen).items():
                out[name] = (rate(v["k"], v["n"])
                             if isinstance(v, dict) and "k" in v else v)
            return out
        self.evaluate = _evaluate


# ── registry: evaluate-once + the bestiary ──────────────────────────────────

class Registry:
    """Content-keyed, append-only. seen() is the dedup; the REJECT subset is
    the bestiary (dead genomes mutators must not re-propose)."""

    def __init__(self, path=None):
        self._mem = {}
        self._store = Store(path) if path else None
        if self._store:
            for r in self._store.records():
                if r.get("kind") == "gp_genome":
                    self._mem[r["id"]] = r

    def seen(self, gid):
        return gid in self._mem

    def record(self, g, fitness, verdict):
        rec = {"kind": "gp_genome", "id": g["id"], "ops": g["ops"],
               "proposed_by": g["proposed_by"], "parents": g["parents"],
               "fitness": fitness, "verdict": verdict}
        self._mem[g["id"]] = rec
        if self._store:
            self._store.append(dict(rec, name=g["id"]))
        return rec

    def bestiary(self):
        return sorted(gid for gid, r in self._mem.items()
                      if r["verdict"] == "REJECT")

    def get(self, gid):
        return self._mem.get(gid)


# ── selection strategies (the fork, as config) ──────────────────────────────

def _primary(fit, key):
    m = fit[key]
    return m["rate"] if isinstance(m, dict) and "rate" in m else m


def hillclimb(scored, mu, key, baseline=None):
    """The old policy: survivors must STRICTLY beat the baseline."""
    floor = _primary(baseline, key) if baseline else float("-inf")
    keep = [(g, f) for (g, f) in scored if _primary(f, key) > floor]
    return sorted(keep, key=lambda x: -_primary(x[1], key))[:mu]


def mu_plus_lambda(scored, mu, key, baseline=None):
    """(μ+λ): best μ of the union survive — neutral children may live."""
    pool = list(scored) + ([(None, baseline)] if baseline else [])
    best = sorted(pool, key=lambda x: -_primary(x[1], key))[:mu]
    return [(g, f) for (g, f) in best if g is not None]


def tournament(scored, mu, key, baseline=None, rng=None, size=2):
    rng = rng or random.Random(0)
    winners = []
    pool = list(scored)
    while pool and len(winners) < mu:
        heat = rng.sample(pool, min(size, len(pool)))
        w = max(heat, key=lambda x: _primary(x[1], key))
        winners.append(w)
        pool.remove(w)
    return winners


def pareto_front(scored, mu, keys, baseline=None):
    """Non-dominated set over several metrics (multi-objective)."""
    def dominates(fa, fb):
        ge = all(_primary(fa, k) >= _primary(fb, k) for k in keys)
        gt = any(_primary(fa, k) > _primary(fb, k) for k in keys)
        return ge and gt
    front = [(g, f) for (g, f) in scored
             if not any(dominates(f2, f) for (_, f2) in scored if f2 is not f)]
    return front[:mu]


# ── the evolve loop ─────────────────────────────────────────────────────────

def evolve(base_config, mutators, evaluator, train_view, *,
           generations=3, mu=2, lam=4, select=mu_plus_lambda,
           select_key="primary", registry=None, rng=None,
           crossover_rate=0.5, eval_budget=64):
    """Population GP. mutators: [fn(train_view, rng, registry) -> [genome]]
    — the TRAIN VIEW is the only data the API hands them (the Goodhart
    guard is this signature). Returns the run log as data."""
    rng = rng or random.Random(7)
    registry = registry or Registry()
    baseline = evaluator.evaluate(genome([], "baseline", reads="none"))
    survivors, evals, log = [], 0, []
    for gen in range(generations):
        brood = []
        for m in mutators:
            brood.extend(m(train_view, rng, registry))
        if len(survivors) >= 2 and rng.random() < crossover_rate:
            a, b = rng.sample([g for (g, _) in survivors], 2)
            child, conflicts = crossover(a, b)
            if child:
                brood.append(child)
        fresh = []
        for g in brood:
            if registry.seen(g["id"]):
                continue                       # dedup + bestiary: never re-try
            fresh.append(g)
        scored = []
        for g in fresh[:max(0, min(lam, eval_budget - evals))]:
            try:
                fit = evaluator.evaluate(g)
            except DL.DeltaError as e:
                registry.record(g, {"error": str(e)}, "UNVIABLE")
                continue
            evals += 1
            scored.append((g, fit))
        pool = scored + survivors
        survivors = select(pool, mu, select_key, baseline=baseline)
        for (g, f) in scored:
            verdict = "KEEP" if any(g2["id"] == g["id"]
                                    for (g2, _) in survivors) else "REJECT"
            registry.record(g, f, verdict)
        log.append({"generation": gen, "proposed": len(brood),
                    "fresh": len(fresh), "evaluated": len(scored),
                    "survivors": [g["id"] for (g, _) in survivors]})
    return {"baseline": baseline, "survivors": survivors, "log": log,
            "evals": evals, "bestiary": registry.bestiary()}


# ── promotion: the handler seat (the loop cannot crown itself) ──────────────

def promote(champion, fitness, store: Store):
    """GAUGE: record the champion + its fitness. Promotion is GRANTED only
    when an EXTERNAL witness has accepted this genome id through the
    handler seat (codething.accept_witness) — returns the honest status."""
    store.append({"kind": "gp_champion", "name": champion["id"],
                  "ops": champion["ops"], "fitness": fitness,
                  "provenance": [f"gauged:{champion['proposed_by']}"]})
    ext = external_witnesses(store, champion["id"])
    return {"id": champion["id"], "gauged": True,
            "promoted": bool(ext),
            "pending": None if ext else
            "external handler acceptance (accept_witness) — the loop "
            "cannot crown its own output"}
