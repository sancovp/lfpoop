"""predict tests — the combination predictor, exact; real artifacts in.

P1  the capability LFP: closure over a chained pool exact (availability,
    growth order, active set); an unmet root stays out.
P2  predict() answers the one question for every unit at once: active /
    buildable (binding residue named) / blocked (capability residue named)
    — the two residue kinds kept distinct, exact.
P3  derivations: every acyclic way to make a target, dependency-first, with
    per-derivation residues; residue() picks the minimal demand set;
    an underivable target names itself.
P4  REAL ARTIFACTS IN: units normalized from an onion2 RingSpec (requires/
    slots exact), a class-ified Wilson (curried z → binding residue), and a
    real callable via the alphabets decider — one predict() over all three
    kinds, statuses exact.
P5  the prediction is data and deterministic (equal dicts across runs).

Run: python3 tests/test_predict.py
"""
import inspect
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lfpoop import predict as P
from lfpoop import classify as K
from lfpoop import onion2 as O2
from lfpoop.gp import wilson


POOL = [
    P.unit("source", provides=["contacts"], requires=["pull_api"]),
    P.unit("qualify", provides=["fit_scores"], requires=["contacts"]),
    P.unit("write", provides=["copy"], requires=["contacts"]),
    P.unit("deliver", provides=["sends"], requires=["copy", "send_api"],
           slots=["postal_address"]),
    P.unit("report", provides=["verdict"], requires=["sends"]),
]


def main():
    checks = {}

    # P1 — the capability LFP, exact.
    available, order, active = P.closure(POOL, base=["pull_api"])
    checks["P1_closure_exact"] = (
        active == ["qualify", "source", "write"]
        and order == ["contacts", "fit_scores", "copy"]
        and "sends" not in available and "pull_api" in available)

    # P2 — one question, every unit, two residue kinds distinct.
    pred = P.predict(POOL, base=["pull_api", "send_api"], bound=[])
    checks["P2_statuses_exact"] = (
        pred["source"]["status"] == "active"
        and pred["deliver"] == {"status": "buildable",
                                "capability_residue": [],
                                "binding_residue": ["postal_address"]}
        and pred["report"]["status"] == "active")
    pred2 = P.predict(POOL, base=["pull_api"])
    checks["P2b_blocked_names_arrival"] = (
        pred2["deliver"] == {"status": "blocked",
                             "capability_residue": ["send_api"],
                             "binding_residue": ["postal_address"]}
        and pred2["report"]["capability_residue"] == ["sends"])

    # P3 — derivations + minimal residue.
    ds = P.derivations(POOL, "verdict", base=["pull_api", "send_api"])
    checks["P3_derivation_chain_exact"] = (
        len(ds) == 1
        and ds[0] == {"chain": ["source", "write", "deliver", "report"],
                      "residue": []})
    checks["P3b_residue_names_arrival"] = (
        P.residue(POOL, "verdict", base=[]) == ["pull_api", "send_api"]
        and P.residue(POOL, "unicorn") == ["unicorn"])

    # P4 — real artifacts normalize in, one prediction over all kinds.
    shout = O2.RingSpec(
        name="Shout", adds=["shout"], requires=["greet"],
        verbs=[O2.VerbSpec(name="shout", slots=["volume"],
                           source="return self.greet().upper()")])
    u_ring = P.unit_from_ring(shout)
    csrc, meta = K.class_ify(inspect.getsource(wilson), slots=["z"])
    Wilson = K.compile_class(csrc, meta, {"math": math})
    u_class = P.unit_from_class(Wilson)
    u_call = P.unit_from_callable(wilson)
    checks["P4a_units_normalized_exact"] = (
        u_ring == {"name": "Shout", "provides": ["shout"],
                   "requires": ["greet"], "slots": ["volume"]}
        and u_class["slots"] == ["z"]
        and u_call == {"name": "wilson", "provides": ["wilson"],
                       "requires": [], "slots": []})  # math is pure ambience
    mixed = P.predict([u_ring, u_class, u_call], base=["greet"],
                      bound=["volume"])
    checks["P4b_mixed_prediction_exact"] = (
        mixed["Shout"]["status"] == "active"
        and mixed["Wilson"] == {"status": "buildable",
                                "capability_residue": [],
                                "binding_residue": ["z"]}
        and mixed["wilson"]["status"] == "active")

    # P5 — the prediction is data, deterministic.
    checks["P5_deterministic_data"] = (
        P.predict(POOL, base=["pull_api"]) == P.predict(POOL,
                                                        base=["pull_api"])
        and P.derivations(POOL, "verdict", base=["pull_api", "send_api"])
        == ds)

    print()
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print(f"\nPREDICT: the one question answered for every unit at once — "
          f"the capability LFP exact, derivations enumerated dependency-"
          f"first, the two residue kinds (what must ARRIVE vs what must be "
          f"BOUND) named distinctly, real rings/classes/callables "
          f"normalized into one pool, and the prediction itself is "
          f"deterministic data. {len(checks)} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
