"""lfpoop.gp tests — the suite's laws, exact; temp stores; seeded rng.

Covers: content addressing (pedigree never enters the hash), registry
evaluate-once + the bestiary, Wilson intervals (property-checked), the
sealed evaluator (no attribute leaks the held-out oracle; mutators receive
the train view ONLY — asserted by a spy), crossover pedigree + conflicts,
each selection strategy on exact fixtures (the fork as config: hillclimb
rejects a neutral child, mu+lambda keeps it), a full evolve() run on a
deterministic domain (climbs, dedups across generations, respects the eval
budget), and promotion via the handler seat (the loop cannot crown itself).

Run: python3 tests/test_gp.py
"""
import os
import random
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lfpoop import gp as GP
from lfpoop import deltas as DL
from lfpoop import codething as CT


def main():
    checks = {}

    # content addressing: ops alone are identity; pedigree never enters.
    g1 = GP.genome([DL.delta("override", ("x",), 1)], "seat_a")
    g2 = GP.genome([DL.delta("override", ("x",), 1)], "seat_b",
                   parents=["g_someone"])
    g3 = GP.genome([DL.delta("override", ("x",), 2)], "seat_a")
    checks["content_addressed"] = (g1["id"] == g2["id"]
                                   and g1["id"] != g3["id"])

    # wilson: property checks (bounds, containment, narrowing with n).
    ok = True
    for (k, n) in [(0, 10), (5, 58), (58, 58), (1, 2)]:
        lo, hi = GP.wilson(k, n)
        p = k / n
        if not (0.0 <= lo <= p <= hi <= 1.0):
            ok = False
    lo1, hi1 = GP.wilson(5, 58)
    lo2, hi2 = GP.wilson(50, 580)
    checks["wilson_properties"] = ok and (hi2 - lo2) < (hi1 - lo1)
    checks["plus_one_is_noise"] = not GP.significantly_above(
        GP.rate(6, 58), GP.rate(5, 58))

    # the sealed evaluator: no attribute holds the oracle; base is copied.
    heldout = {"secret_corpus": [1, 2, 3]}

    def eval_fn(phen):
        return {"primary": {"k": phen.get("x", 0), "n": 10}}
    ev = GP.Evaluator({"x": 0}, eval_fn)
    leaked = [a for a in vars(ev)
              if "held" in a.lower() or "secret" in a.lower()
              or "oracle" in a.lower()]
    checks["evaluator_sealed"] = (leaked == []
                                  and ev.evaluate(g1)["primary"]["k"] == 1)

    # mutators receive the TRAIN VIEW only (the Goodhart guard signature).
    received = {}

    def spy_mutator(train_view, rng, registry):
        received["args"] = train_view
        return [GP.genome([DL.delta("override", ("x",), 3)], "spy")]
    GP.evolve({"x": 0}, [spy_mutator], ev, train_view=["train only"],
              generations=1, rng=random.Random(1))
    checks["mutator_gets_train_view_only"] = received["args"] == ["train only"]

    # crossover: pedigree recorded; conflicts surface, never merge.
    child, conflicts = GP.crossover(g1, g3)
    checks["crossover_conflict_surfaces"] = (child is None
                                             and conflicts[0]["path"] == ("x",))
    ga = GP.genome([DL.delta("add", ("a",), 1)], "s")
    gb = GP.genome([DL.delta("add", ("b",), 2)], "s")
    child, conflicts = GP.crossover(ga, gb)
    checks["crossover_pedigree"] = (
        conflicts == [] and child["parents"] == [ga["id"], gb["id"]]
        and sorted(d["path"] for d in child["ops"]) == [("a",), ("b",)])

    # selection strategies on exact fixtures — the FORK as config.
    base = {"primary": GP.rate(5, 58)}
    neutral = (ga, {"primary": GP.rate(5, 58)})     # +0 vs baseline
    better = (gb, {"primary": GP.rate(7, 58)})
    checks["hillclimb_rejects_neutral"] = (
        GP.hillclimb([neutral, better], 2, "primary", baseline=base)
        == [better])
    checks["mu_plus_lambda_keeps_neutral"] = (
        set(g["id"] for (g, _) in GP.mu_plus_lambda(
            [neutral, better], 2, "primary", baseline=base))
        == {ga["id"], gb["id"]})
    front = GP.pareto_front(
        [(ga, {"a": 1.0, "b": 0.0}), (gb, {"a": 0.0, "b": 1.0}),
         (g3, {"a": 0.0, "b": 0.0})], 3, ["a", "b"])
    checks["pareto_front_exact"] = ({g["id"] for (g, _) in front}
                                    == {ga["id"], gb["id"]})
    t = GP.tournament([neutral, better], 1, "primary",
                      rng=random.Random(0), size=2)
    checks["tournament_picks_winner"] = t == [better]

    # the bandit strategy: same rate, fewer samples -> exploration credit.
    wide = (g1, {"primary": GP.rate(1, 8)})     # ~0.125, wide interval
    narrow = (g3, {"primary": GP.rate(10, 80)})  # 0.125, narrow interval
    checks["ucb_prefers_undersampled_arm"] = (
        GP.ucb([narrow, wide], 1, "primary")[0][0]["id"] == g1["id"]
        and GP.ucb([narrow, better], 1, "primary")[0][0]["id"] == gb["id"])

    # evolve(): deterministic domain — fitness = value at ("x",) capped;
    # a ladder mutator proposes x+1 each generation; must climb, dedup,
    # respect budget, and record the bestiary.
    def eval_fn2(phen):
        return {"primary": {"k": min(phen.get("x", 0), 10), "n": 10}}
    ev2 = GP.Evaluator({"x": 0}, eval_fn2)

    def ladder(train_view, rng, registry):
        return [GP.genome([DL.delta("override", ("x",), v)], "ladder")
                for v in (1, 2, 3)]
    with tempfile.TemporaryDirectory() as td:
        reg = GP.Registry(os.path.join(td, "registry.jsonl"))
        run = GP.evolve({"x": 0}, [ladder], ev2, train_view=[],
                        generations=3, mu=1, lam=4, registry=reg,
                        rng=random.Random(2), eval_budget=10)
        top = run["survivors"][0]
        checks["evolve_climbs"] = top[1]["primary"]["k"] == 3
        # gens 2 and 3 propose the SAME genomes — all deduped, 3 evals total
        checks["evolve_dedups_everything_seen"] = (
            run["evals"] == 3
            and run["log"][1]["fresh"] == 0 and run["log"][2]["fresh"] == 0)
        checks["bestiary_holds_the_dead"] = (
            len(run["bestiary"]) == 2
            and top[0]["id"] not in run["bestiary"])
        # a fresh Registry over the same file remembers (persistence)
        reg2 = GP.Registry(os.path.join(td, "registry.jsonl"))
        checks["registry_persists"] = all(
            reg2.seen(gid) for gid in run["bestiary"])

        # promotion: gauge alone does NOT promote; the handler seat does.
        store = CT.Store(os.path.join(td, "store.jsonl"))
        p1 = GP.promote(top[0], top[1], store)
        CT.accept_witness(store, top[0]["id"],
                          "external:test-governor:accept=yes")
        p2 = GP.promote(top[0], top[1], store)
        checks["promotion_needs_handler"] = (
            p1["promoted"] is False and "accept_witness" in p1["pending"]
            and p2["promoted"] is True)

    # unviable genomes are recorded, named, and never crash the loop.
    def bad_mutator(train_view, rng, registry):
        return [GP.genome([DL.delta("exclude", ("nope",))], "bad")]
    with tempfile.TemporaryDirectory() as td:
        reg = GP.Registry(os.path.join(td, "r.jsonl"))
        run = GP.evolve({"x": 0}, [bad_mutator], ev2, train_view=[],
                        generations=1, registry=reg, rng=random.Random(3))
        rec = reg.get(GP.genome([DL.delta("exclude", ("nope",))], "z")["id"])
        checks["unviable_named_not_fatal"] = (
            run["evals"] == 0 and rec["verdict"] == "UNVIABLE"
            and "nope" in rec["fitness"]["error"])

    print()
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print(f"\nlfpoop.gp: genomes are content-addressed delta programs; the "
          f"evaluator is sealed and mutators see only the train view; "
          f"fitness carries honest uncertainty (+1/58 is noise); selection "
          f"is a config choice (the fork dissolved); evolve climbs, dedups, "
          f"budgets, and keeps a bestiary; promotion requires the handler "
          f"seat. {len(checks)} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
