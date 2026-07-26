"""ONION-V2 + kleene_climb tests — exact assertions, temp stores only.

Covers: assembly from ring DATA (create_model + add_method), the activation
semantics (soup refusal naming slots; heat exact; monotone bind; activation
at the substitution LFP), the carried-over v1 laws (requires gap, leak
refusal — both named), morph (bindings transported/dropped exactly),
data/JSON/XML round-trips INCLUDING binding state, MetaStack composability,
and kleene_climb at node grain (locate exact, refuse-naming-artifact,
rung advance recorded) + sdk grain (distance 7, next = skill).

Run: python3 tests/test_onion2_climb.py   (needs pydantic + pydantic_stack_core)
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lfpoop import onion2 as O2
from lfpoop import ontology as O
from lfpoop import codething as CT
from lfpoop.climb import kleene_climb, REQUIREMENTS
from lfpoop.onion import StackError


GREET = O2.RingSpec(
    name="Greet", adds=["greet"], requires=[],
    verbs=[O2.VerbSpec(name="greet", slots=["who", "salutation"],
                       source="return self.salutation + ', ' + self.who")])

SHOUT = O2.RingSpec(
    name="Shout", adds=["shout"], requires=["greet"],
    verbs=[O2.VerbSpec(name="shout", slots=[],
                       source="return self.greet().upper() + '!'")])

WHISPER = O2.RingSpec(
    name="Whisper", adds=["whisper"], requires=["greet"],
    verbs=[O2.VerbSpec(name="whisper", slots=["who"],
                       source="return '(' + self.who.lower() + ')'")])


def main():
    checks = {}

    # ── assembly + activation semantics ──
    inst = O2.assemble("Greeter", [SHOUT, GREET])
    checks["heat_exact_before"] = O2.heat(inst) == 2
    checks["soup_names_per_verb"] = (
        O2.soup(inst) == {"greet": ["who", "salutation"]})
    try:
        inst.get_method("greet")()
        checks["soup_refusal"] = False
    except O2.SoupError as e:
        checks["soup_refusal"] = "who" in str(e) and "salutation" in str(e)
    O2.bind(inst, "who", "world")
    checks["heat_drops_per_substitution"] = O2.heat(inst) == 1
    O2.bind(inst, "salutation", "hello")
    checks["activation_at_lfp"] = (
        O2.heat(inst) == 0
        and inst.get_method("greet")() == "hello, world"
        and inst.get_method("shout")() == "HELLO, WORLD!")
    try:
        O2.bind(inst, "who", "someone else")
        checks["monotone_bind"] = False
    except StackError as e:
        checks["monotone_bind"] = "who" in str(e) and "morph" in str(e)

    # ── the v1 laws carry over, named ──
    try:
        O2.assemble("Bad", [SHOUT])                # requires greet, absent
        checks["requires_gap_named"] = False
    except StackError as e:
        checks["requires_gap_named"] = "greet" in str(e) and "Shout" in str(e)
    leaky = O2.RingSpec(
        name="Leaky", adds=["sneak"], requires=[],
        verbs=[O2.VerbSpec(name="sneak", slots=[],
                           source="return self.secret")])
    try:
        O2.assemble("Leak", [leaky])
        checks["leak_refused_named"] = False
    except StackError as e:
        checks["leak_refused_named"] = "secret" in str(e) and "Leaky" in str(e)

    # ── morph: config swap, bindings transported/dropped exactly ──
    new_inst, report = O2.morph(inst, "Whisperer", [WHISPER, GREET])
    checks["morph_transport_exact"] = (
        report["transported"] == ["who", "salutation"]
        and report["dropped"] == []
        and type(new_inst).__name__ == "Whisperer"
        and new_inst.get_method("whisper")() == "(world)")
    solo = O2.assemble("Solo", [GREET])
    O2.bind(solo, "who", "x")
    O2.bind(solo, "salutation", "yo")
    bare = O2.RingSpec(name="Bare", adds=["noop"], requires=[],
                       verbs=[O2.VerbSpec(name="noop", slots=[],
                                          source="return 0")])
    _, rep2 = O2.morph(solo, "Nothing", [bare])
    checks["morph_drop_named"] = sorted(rep2["dropped"]) == ["salutation", "who"]

    # ── data / JSON / XML round-trips (binding state travels) ──
    data = O2.to_data(inst)
    clone = O2.from_data(data)
    checks["data_roundtrip_with_bindings"] = (
        O2.heat(clone) == 0
        and clone.get_method("shout")() == "HELLO, WORLD!"
        and O2.to_data(clone) == data)
    jclone = O2.from_data(O2.parse_json(json.dumps(data)))
    checks["json_is_thin_parser"] = O2.to_data(jclone) == data
    xml = """<onion name="Greeter">
      <ring name="Shout" adds="shout" requires="greet">
        <verb name="shout">return self.greet().upper() + '!'</verb></ring>
      <ring name="Greet" adds="greet" requires="">
        <verb name="greet" slots="who,salutation">return self.salutation + ', ' + self.who</verb></ring>
      <binding slot="who" value="world"/>
      <binding slot="salutation" value="hello"/></onion>"""
    xclone = O2.from_data(O2.parse_xml(xml))
    checks["xml_is_thin_parser"] = (
        xclone.get_method("shout")() == "HELLO, WORLD!"
        and O2.to_data(xclone) == data)

    # ── MetaStack composability (rings are RenderablePieces) ──
    from pydantic_stack_core import MetaStack
    ms = MetaStack(pieces=[GREET, SHOUT], separator="\n\n")
    r = ms.render()
    checks["metastack_composable"] = ("ring Greet(" in r and "ring Shout(" in r
                                      and "def greet(self" in r)

    # ── kleene_climb: node grain, on a TEMP store ──
    with tempfile.TemporaryDirectory() as td:
        store = CT.Store(os.path.join(td, "store.jsonl"))
        loc = kleene_climb("ghost", store)
        checks["climb_bottom"] = (
            loc["position"]["level"] == "function" and loc["distance"] == 22
            and loc["next"] == {"kind": "cooling", "name": "execution",
                                "requires": REQUIREMENTS["execution"]})
        rec = CT.mirror(main)                     # a REAL artifact, mirrored
        rec["name"] = "thing"
        rec["provenance"].append("materialized_in:test")
        rec["tests"].append("test_onion2_climb.py")
        rec["generated_documentation"].append("thing.md")
        rec["generated_packages"].append("thing.tar")
        store.append(rec)
        gauged = dict(rec)
        gauged["golden_history"] = [list(O.COOLING[:4]) + O.COOLING[5:]]
        store.append(gauged)                      # gauge: 6/7, handler's absent
        loc = kleene_climb("thing", store)
        checks["climb_locates_gauge"] = (
            loc["position"]["level"] == "function"
            and set(loc["position"]["witnessed"]) == set(O.COOLING) - {
                "independent_witnessing"}
            and loc["next"] == {"kind": "cooling",
                                "name": "independent_witnessing",
                                "requires":
                                    REQUIREMENTS["independent_witnessing"]})
        took = kleene_climb("thing", store, step=True)
        checks["climb_refuses_fabrication"] = (
            not took["taken"] and "accept_witness" in took["refusal"])
        CT.accept_witness(store, "thing", "external:test-handler:accept=yes")
        evolved = dict(gauged)
        evolved["graph_identity"] = "different-source-hash"
        store.append(evolved)                     # second identity: evolution
        loc = kleene_climb("thing", store)
        checks["climb_handler_and_rites"] = (
            "independent_witnessing" in loc["position"]["witnessed"]
            and sorted(loc["position"]["rites"]) == sorted(O.AGENT_RITES)
            and loc["next"] == {"kind": "rung", "name": "program",
                                "requires": REQUIREMENTS["rung"]})
        took = kleene_climb("thing", store, step=True, witness="test")
        after = kleene_climb("thing", store)
        checks["climb_takes_rung_recorded"] = (
            took["taken"] and took["position"]["level"] == "program"
            and after["position"]["level"] == "program"
            and any("transition:function->program:by:test" in p
                    for r in store.history("thing")
                    for p in r.get("provenance", [])))

    # ── kleene_climb: the SDK locating ITSELF (repo store, read-only) ──
    sdk = kleene_climb("sdk")
    checks["climb_sdk_distance_7"] = (
        sdk["distance"] == 7
        and sdk["position"]["level"] == "graph_entity"
        and sdk["next"] == {"kind": "rung", "name": "skill",
                            "requires": REQUIREMENTS["rung"]})
    sdk_step = kleene_climb("sdk", step=True)
    checks["climb_sdk_step_refuses"] = (
        not sdk_step["taken"] and "DERIVED" in sdk_step["refusal"])

    print()
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print(f"\nONION-V2 + kleene_climb: rings are DATA (RenderablePiece), "
          f"classes are generated (create_model + add_method), a method "
          f"activates at the LFP of substitutions (soup named until ground), "
          f"morph transports bindings across a config swap, JSON/XML are thin "
          f"parsers into the same data, and kleene_climb locates/answers/"
          f"steps honestly at node AND sdk grain. {len(checks)} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
