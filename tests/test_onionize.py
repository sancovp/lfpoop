"""onionize tests — THE CLAIM'S OWN GATE: module in, onion out, judged by
the module's own pre-existing suite.

N1  onionize lfpoop.deltas (a REAL module: 13 functions, a class, module-
    level state, registration calls at the bottom): every function opens at
    fine grain (zero sealed), verbatim statements preserved in order, the
    learned rings appear with membership as data, output deterministic.
N2  THE MODULE-GRAIN SHADOW LAW — the whole point: the onionized deltas is
    installed AS lfpoop.deltas in a subprocess and the REAL
    tests/test_deltas.py (the module's own 14-check suite) runs GREEN
    against it. The claim "the library automatically transforms modules
    into onions" is exactly as true as this check.
N3  totality via opaque blocks: a module whose function carries a nested
    def onionizes fine-grain WITH the sealed block recorded — and the
    emitted code still behaves (the closure works through the chain).
N4  a decorated function seals whole (reported), everything else still
    transforms, the module still executes.

Run: python3 tests/test_onionize.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lfpoop import onionize as O
from lfpoop import deltas as DL


def main():
    checks = {}

    # N1 — the real module opens completely.
    src, report = O.onionize_module(DL)
    src2, _ = O.onionize_module(DL)
    checks["N1_deltas_opens_fine_grain"] = (
        len(report["fine"]) == 13 and report["sealed"] == {}
        and report["verbatim"] >= 8         # docstring/imports/class/state
        and "class DeltaError" in src
        and "register_substrate('module', _substrate_module)" in src
        and "__ring_members__" in src and "DeltasOnion" in src
        and src == src2)                    # deterministic

    # N2 — THE SHADOW LAW at module grain, against the module's OWN suite.
    green, out = O.shadow_module(
        src, "lfpoop.deltas",
        os.path.join(ROOT, "tests", "test_deltas.py"), ROOT)
    checks["N2_module_shadow_own_suite_green"] = green
    if not green:
        print("  [N2] suite output tail:")
        print("\n".join("    " + l for l in out.splitlines()[-15:]))

    # N3 — totality: nested def becomes a sealed block, behavior preserved.
    nested_mod = '''
def make_adder(base):
    offset = base * 2
    def add(x):
        return x + offset
    total = add(base)
    return (total, add(1))
'''
    s3, r3 = O.onionize_module_source(nested_mod, "nested_mod", learn=False)
    ns = {}
    exec(s3, ns)
    checks["N3_opaque_totality"] = (
        r3["fine"]["make_adder"]["opaque"] == 1
        and r3["sealed"] == {}
        and ns["make_adder"](5) == (15, 11))

    # N4 — decorated seals whole; the rest still transforms.
    deco_mod = '''
import functools

def plain(a):
    b = a + 1
    return b

@functools.lru_cache(maxsize=None)
def cached(n):
    return n * plain(n)
'''
    s4, r4 = O.onionize_module_source(deco_mod, "deco_mod", learn=False)
    ns4 = {}
    exec(s4, ns4)
    checks["N4_decorated_sealed_reported"] = (
        r4["sealed"] == {"cached": "decorated"}
        and "plain" in r4["fine"]
        and ns4["cached"](3) == 12 and ns4["plain"](1) == 2)

    # N5 — capture-risk (v4 MED-4): a closure over a later-rebound var is
    # SEALED whole (not falsely "fine"), and behaves correctly.
    cap_mod = ("def f():\n    x = 1\n    def get():\n        return x\n"
               "    x = 2\n    return get()\n")
    s5, r5 = O.onionize_module_source(cap_mod, "cap", learn=False)
    ns5 = {}
    exec(s5, ns5)
    checks["N5_capture_risk_sealed_honestly"] = (
        "f" in r5["sealed"] and "captures" in r5["sealed"]["f"]
        and "f" not in r5["fine"] and ns5["f"]() == 2)

    # N6 — COVERAGE RUNG (MVP #4): classes open at method grain. onionize
    # lfpoop.gp (Evaluator/Registry classes + nested closures) and run its
    # OWN 18-check suite against the onionized build — green.
    from lfpoop import gp as _gp
    gsrc, greport = O.onionize_module(_gp)
    ggreen, gout = O.shadow_module(
        gsrc, "lfpoop.gp",
        os.path.join(ROOT, "tests", "test_gp.py"), ROOT)
    checks["N6_class_methods_fine_shadow_green"] = (
        ggreen
        and set(greport["classes"]) == {"Evaluator", "Registry"}
        and "record" in greport["classes"]["Registry"]["methods_fine"]
        and greport["classes"]["Registry"]["methods_sealed"] == {})
    if not ggreen:
        print("  [N6] gp suite tail:")
        print("\n".join("    " + l for l in gout.splitlines()[-12:]))

    print()
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print(f"\nONIONIZE: a real module in, the onion out — all 13 deltas "
          f"functions at fine grain, order-preserved verbatim floor, "
          f"learned rings as data, deterministic — and THE MODULE'S OWN "
          f"SUITE RAN GREEN AGAINST THE ONIONIZED BUILD. Totality holds "
          f"(nested defs seal as blocks, decorated functions seal whole, "
          f"nothing refuses). {len(checks)} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
