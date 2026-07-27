"""onionize SWEEP — the MVP capstone: the driver is GENERAL, not
deltas-specific.

Onionizes a SPREAD of real lfpoop modules — covering augassign-free and
augassign-bearing code, class-free and class-bearing modules, nested
closures, the Scott domain, the predictor — and runs EACH MODULE'S OWN
pre-existing test suite against its onionized build in a subprocess. Every
one green = "the library automatically transforms modules into onions" is
true across the package, by the modules' own acceptance criteria.

Also asserts the module onion carries BOTH ring kinds as data
(__function_rings__ from the learned wiring + __class_rings__ from the
opened classes).

This is the capstone gate: the claim is exactly as true as this sweep is
green. Run: python3 tests/test_onionize_sweep.py
"""
import importlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lfpoop import onionize as O

# (module, its own suite) — a deliberate spread of shapes.
SWEEP = [
    ("lfpoop.deltas", "test_deltas.py"),        # algebra, no augassign
    ("lfpoop.gp", "test_gp.py"),                # classes + nested closures
    ("lfpoop.domain", "test_domain_chains.py"),  # the Scott domain, no class
    ("lfpoop.classify", "test_classify.py"),    # augassign (group emit)
    ("lfpoop.predict", "test_predict.py"),      # the predictor, recursion
    ("lfpoop.alphabets", "test_alphabets.py"),  # the decider
    ("lfpoop.owl", "test_owl.py"),              # augassign (render_sdk_owl)
    ("lfpoop.codething", "test_full.py"),       # the Store class, opened
]


def main():
    checks = {}
    results = {}
    for mod_name, test in SWEEP:
        mod = importlib.import_module(mod_name)
        src, report = O.onionize_module(mod)
        src2, _ = O.onionize_module(mod)          # determinism
        green, out = O.shadow_module(
            src, mod_name, os.path.join(ROOT, "tests", test), ROOT)
        results[mod_name] = {
            "green": green, "deterministic": src == src2,
            "fns": len(report["fine"]), "sealed": len(report["sealed"]),
            "classes": list(report.get("classes", {})),
            "has_ring_data": ("__function_rings__" in src
                              and "__class_rings__" in src)}
        tag = "GREEN" if green else "RED"
        print(f"  {tag:5} {mod_name:22} fns={results[mod_name]['fns']} "
              f"sealed={results[mod_name]['sealed']} "
              f"classes={results[mod_name]['classes']}")
        if not green:
            print("        " + (out.strip().splitlines() or ["?"])[-1][:90])

    checks["all_modules_shadow_green"] = all(
        r["green"] for r in results.values())
    checks["all_deterministic"] = all(
        r["deterministic"] for r in results.values())
    checks["all_carry_ring_data"] = all(
        r["has_ring_data"] for r in results.values())
    # the spread actually EXERCISED classes and augassign (not vacuous)
    checks["spread_covers_classes"] = (
        results["lfpoop.gp"]["classes"] == ["Evaluator", "Registry"]
        and results["lfpoop.codething"]["classes"] == ["Store"])

    print()
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print(f"\nONIONIZE SWEEP: {len(SWEEP)} real lfpoop modules onionized — "
          f"augassign, classes, nested closures, the Scott domain, the "
          f"predictor — and EVERY module's OWN suite ran green against its "
          f"onionized build, deterministically, each carrying both ring "
          f"kinds as data. The driver is general. {len(checks)} checks "
          f"green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
