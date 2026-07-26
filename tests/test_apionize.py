"""apionize laws — the API→onion compiler on fixture callables (algebra-style).

Run: python3 tests/test_apionize.py   (needs the onion2 extra)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lfpoop.apionize import analyze, apionize
from lfpoop import onion2 as O2


def get_user(api_key, base_url, user_id):
    return f"GET {base_url}/users/{user_id} [{api_key}]"


def post_note(api_key, base_url, user_id, text):
    return f"POST {base_url}/users/{user_id}/notes {text!r} [{api_key}]"


def ping(base_url):
    return f"PING {base_url}"


API = [get_user, post_note, ping]


def main():
    checks = {}

    # heuristic factoring: shared params = candidates, exact.
    cand, rep = analyze(API)
    checks["heuristic_exact"] = (cand == ["api_key", "base_url", "user_id"]
                                 and rep["ping"]["curried"] == ["base_url"]
                                 and rep["post_note"]["call_args"] == ["text"])

    # masked (authoritative) compile: user_id stays a call arg.
    inst, report = apionize("toy_api", API,
                            config_mask=["api_key", "base_url"])
    checks["mask_overrides_heuristic"] = (
        report["config_slots"] == ["api_key", "base_url"]
        and report["verbs"]["get_user"]["call_args"] == ["user_id"])

    # soup names the curry; heat = distinct unbound config slots.
    checks["soup_and_heat"] = O2.heat(inst) == 2
    try:
        inst.get_method("get_user")(user_id="7")
        checks["refuses_before_binding"] = False
    except O2.SoupError as e:
        checks["refuses_before_binding"] = ("api_key" in str(e)
                                            and "base_url" in str(e))

    # bind once; every verb activates; real invocation through the onion.
    O2.bind(inst, "api_key", "K")
    O2.bind(inst, "base_url", "https://api.example")
    checks["activation_and_execution"] = (
        inst.get_method("ping")() == "PING https://api.example"
        and inst.get_method("get_user")(user_id="7")
        == "GET https://api.example/users/7 [K]"
        and inst.get_method("post_note")(user_id="7", text="hi")
        == "POST https://api.example/users/7/notes 'hi' [K]")

    # call-time override beats the bound slot; organ round-trips as data.
    checks["override_and_data"] = (
        inst.get_method("ping")(base_url="http://other") == "PING http://other"
        and O2.to_data(inst)["bindings"] == {"api_key": "K",
                                             "base_url": "https://api.example"})

    print()
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print(f"\napionize: callables in, the curried onion API out — factoring "
          f"(heuristic candidates / authoritative mask), soup-by-name, "
          f"activation at the binding LFP, real invocation, data round-trip. "
          f"{len(checks)} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
