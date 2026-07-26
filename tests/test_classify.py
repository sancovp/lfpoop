"""classify tests — CLASS-IFY: curried function → class, on real code, exact.

K1  wilson (REAL SDK code), curried over z: Wilson(z=1.96)(k, n) equals
    wilson(k, n, 1.96) over a sweep (THE SHADOW LAW through the class);
    a different binding is a different instance with different behavior —
    partial application reified as construction.
K2  soup/monotone/heat on the class: unbound call refused naming the slot;
    rebind refused; heat 1→0; non-slot bind refused (residue is the call's).
K3  the emitted CLASS SOURCE is standalone code out — exec'd in a clean
    namespace (plus the impl's own needs) and carries __curried__/
    __residue__ as data.
K4  the decider wires in: with a config context, class_ify chooses slots
    itself via the curry plan (api_key curries, month stays residue).
K5  the GROUP case (apionize as code out): two functions sharing an
    alphabet → one class, methods run the real impls with bound state,
    per-method soup named.
K6  refusal: nothing curries → refused by name (a class with no bound
    state is just the function).

Run: python3 tests/test_classify.py
"""
import inspect
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lfpoop import classify as K
from lfpoop.gp import wilson


def main():
    checks = {}
    wsrc = inspect.getsource(wilson)

    # K1 — the class IS the curried function; shadow over a real sweep.
    csrc, meta = K.class_ify(wsrc, slots=["z"])
    Wilson = K.compile_class(csrc, meta, {"math": math})
    w196 = Wilson(z=1.96)
    w300 = Wilson(z=3.0)
    sweep = [(k, n) for n in (2, 10, 58) for k in range(0, n + 1,
                                                       max(1, n // 5))]
    checks["K1_shadow_through_class"] = (
        all(w196(k, n) == wilson(k, n, 1.96) for (k, n) in sweep)
        and all(w300(k, n) == wilson(k, n, 3.0) for (k, n) in sweep)
        and w300(5, 58) != w196(5, 58)
        and meta["curried"] == ["z"] and meta["residue"] == ["k", "n"])

    # K2 — soup / monotone / heat / alphabet discipline.
    cold = Wilson()
    checks["K2a_heat"] = (cold.heat == 1 and w196.heat == 0
                          and cold.soup == ["z"])
    try:
        cold(5, 58)
        checks["K2b_soup_refused_named"] = False
    except RuntimeError as e:
        checks["K2b_soup_refused_named"] = "'z'" in str(e)
    cold.bind("z", 2.0)
    checks["K2c_bind_activates"] = (cold.heat == 0
                                    and cold(5, 58) == wilson(5, 58, 2.0))
    try:
        cold.bind("z", 9.9)
        checks["K2d_monotone"] = False
    except ValueError as e:
        checks["K2d_monotone"] = "monotone" in str(e)
    try:
        Wilson().bind("k", 5)
        checks["K2e_residue_not_bindable"] = False
    except KeyError as e:
        checks["K2e_residue_not_bindable"] = "curried alphabet" in str(e)

    # K3 — code out: standalone source with metadata as data.
    checks["K3_code_out_standalone"] = (
        "class Wilson:" in csrc and "_impl_wilson" in csrc
        and Wilson.__curried__ == ("z",)
        and Wilson.__residue__ == ("k", "n"))

    # K4 — the decider chooses the slots (alphabets → classify).
    src = """
def send_report(api_key, month):
    return ('sent', api_key, month)
"""
    csrc4, m4 = K.class_ify(src, context={"config_slots": ["api_key"]})
    Sender = K.compile_class(csrc4, m4)
    checks["K4_decider_chooses_slots"] = (
        m4["curried"] == ["api_key"] and m4["residue"] == ["month"]
        and Sender(api_key="K7")("07") == ("sent", "K7", "07"))

    # K5 — the group case: one shared alphabet, many residue methods.
    fa = "def fetch(api_key, base_url, uid):\n    return ('GET', base_url, uid, api_key)\n"
    fb = "def push(api_key, base_url, payload):\n    return ('POST', base_url, payload, api_key)\n"
    gsrc, gm = K.class_ify_group("toy_api", [fa, fb],
                                 slots=["api_key", "base_url"])
    Api = K.compile_class(gsrc, gm)
    api = Api(api_key="K", base_url="https://x")
    checks["K5_group_class"] = (
        api.fetch(uid="7") == ("GET", "https://x", "7", "K")
        and api.push(payload="p") == ("POST", "https://x", "p", "K")
        and gm["methods"]["fetch"]["residue"] == ["uid"])
    try:
        Api(api_key="K").push(payload="p")
        checks["K5b_group_soup_named"] = False
    except RuntimeError as e:
        checks["K5b_group_soup_named"] = "base_url" in str(e)

    # K6 — nothing curries → refused.
    try:
        K.class_ify("def add(a, b):\n    return a + b\n", slots=[])
        checks["K6_refuses_no_curry"] = False
    except K.ClassifyRefusal as e:
        checks["K6_refuses_no_curry"] = "nothing curries" in str(e)

    print()
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print(f"\nCLASSIFY (for real this time): a curried function BECOMES a "
          f"class — construction binds the curried alphabet (monotone, "
          f"soup-named, heat-counted), the call applies the residue, the "
          f"emitted source is standalone code out with the alphabets as "
          f"data, the decider picks the slots, and the group case is one "
          f"class with many residue methods. {len(checks)} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
