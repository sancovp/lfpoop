"""blocks tests — the first step, proven on the SDK's own real functions.

B1  blockify on REAL code (gp.wilson): block kinds/reads/writes EXACT.
B2  each functionalized block runs standalone on fed reads.
B3  THE SHADOW LAW: code in → block data → code out → recompiled callable
    behaves IDENTICALLY to the original — wilson over a (k,n) sweep and
    domain.closure_step over 500 sampled states, exact equality (early
    returns inside if/for included).
B4  the emitted source is the LFPOOPy shape: BASE block defs → META chain
    → SUPER onion class, and the class carries its base ring as data.
B5  HOMOICONIC GP: a genome of delta ops over BLOCK DATA (override one
    block's source) → re-emit → recompile → behavior changes exactly as
    the mutation implies; the identity genome reproduces byte-identical
    source. Genetic programming now operates on code-as-data.
B6  refusal: nested defs are refused BY NAME, never mangled.

Run: python3 tests/test_blocks.py
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lfpoop import blocks as B
from lfpoop import domain as D
from lfpoop import gp as GP
from lfpoop import deltas as DL
from lfpoop.gp import wilson


def main():
    checks = {}

    # B1 — the real function decomposes exactly.
    blks, meta = B.blockify(wilson)
    kinds = [b["kind"] for b in blks]
    checks["B1_blockify_exact"] = (
        meta["name"] == "wilson" and meta["params"] == ["k", "n", "z"]
        and kinds == ["control", "binding", "binding", "binding", "binding",
                      "binding", "control", "control", "return"]
        and blks[0] == {"i": 0, "kind": "control", "reads": ["n"],
                        "writes": [], "source": "if n == 0:\n"
                        "    return (0.0, 1.0)"}
        and blks[2]["reads"] == ["n", "z"] and blks[2]["writes"] == ["d"])

    # B2 — a functionalized block runs standalone.
    ns = dict(meta["globals"])
    exec(B.functionalize(blks[1], "t"), ns)          # p = k / n
    checks["B2_block_runs_standalone"] = ns["t_1"](k=5, n=58) == (
        "__w__", (5 / 58,))

    # B3 — the shadow law, exact over real sweeps.
    rebuilt, src, m2, cls = B.roundtrip(wilson)
    sweep_ok = all(rebuilt(k, n) == wilson(k, n)
                   for n in (1, 2, 10, 58, 580)
                   for k in range(0, n + 1, max(1, n // 7)))
    rebuilt_cs, _, _, _ = B.roundtrip(D.closure_step)
    rng = random.Random(3)
    states = list(D.all_states())
    cs_ok = all(rebuilt_cs(s) == D.closure_step(s)
                for s in rng.sample(states, 500))
    checks["B3_shadow_identical_behavior"] = sweep_ok and cs_ok

    # B4 — the LFPOOPy shape: BASE -> META -> SUPER, ring as data.
    checks["B4_base_meta_super"] = (
        src.index("# BASE") < src.index("# META") < src.index("# SUPER")
        and cls.__name__ == "WilsonOnion"
        and cls.__ring_base__ == [f"_wilson_blk_{i}" for i in range(9)]
        and cls.wilson(5, 58) == wilson(5, 58))

    # B5 — homoiconic GP: genomes mutate BLOCK DATA.
    base_cfg = {"blocks": {str(b["i"]): dict(b) for b in blks}}

    def compile_genome(g):
        phen = GP.phenotype(g, base_cfg)
        bl = [phen["blocks"][str(i)] for i in range(len(blks))]
        s2, m3 = B.emit_from_blocks(bl, meta)
        return B.compile_fn(s2, m3)[0], s2

    identity = GP.genome([], "identity")
    f_id, s_id = compile_genome(identity)
    _, s_id2 = compile_genome(identity)
    mut = GP.genome([DL.delta("override", ("blocks", "2", "source"),
                              "d = 1 + z * z / (2 * n)")], "block_mutator")
    f_mut, s_mut = compile_genome(mut)
    lo_o, hi_o = wilson(5, 58)
    lo_m, hi_m = f_mut(5, 58)
    checks["B5_gp_on_code_as_data"] = (
        s_id == s_id2
        and f_id(5, 58) == wilson(5, 58)
        and (lo_m, hi_m) != (lo_o, hi_o)
        and (hi_m - lo_m) > (hi_o - lo_o))   # halved denominator widens d⁻¹
    checks["B5b_genome_content_addressed"] = (
        GP.genome([], "someone_else")["id"] == identity["id"]
        and mut["id"] != identity["id"])

    # B6 — refusal by name.
    def has_nested():
        def inner():
            return 1
        return inner()
    try:
        B.blockify(has_nested)
        checks["B6_refuses_nested_named"] = False
    except B.BlockifyRefusal as e:
        checks["B6_refuses_nested_named"] = "nested" in str(e)

    print()
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print(f"\nBLOCKS: real code decomposed into logic-block DATA (reads/"
          f"writes exact), every block functionalized over its free reads, "
          f"the chain recomposed to IDENTICAL behavior (early returns "
          f"included), emitted as BASE→META→SUPER onion source — and GP now "
          f"mutates the block data itself and recompiles. The first step "
          f"exists. {len(checks)} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
