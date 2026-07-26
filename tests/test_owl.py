"""LFPOOP-OWL tests — the recursive self-ontology, exact assertions.

Covers: the TBox (ladder = subsumption chain, EXACT edges; Golden/Agent as
defined classes), leq-on-levels IS subsumption (checked against the parsed
XML for all level pairs), State/Node individuals with all 13 booleans
explicit, structural recursion (an onion's render literally contains its
rings' renders), the OWL↔rings round trip closed BOTH ways (parse∘render =
identity on behavior AND on the re-render), store rendering via the
kleene_climb derivation, and the whole-SDK document.

owlready2 LOAD verification runs iff owlready2 is importable (the soma lab
env); Pellet/HermiT CLASSIFICATION is HOST-GATED (no Java in the lab) and
skips honestly here — the defined-class semantics are still asserted
structurally against the emitted XML.

Run: python3 tests/test_owl.py    (full: micromamba -n soma, owlready2)
"""
import os
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lfpoop import domain as D
from lfpoop import ontology as O
from lfpoop import owl as W
from lfpoop import onion2 as O2
from lfpoop import codething as CT
from lfpoop.onion2 import bind

RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"


def _ln(el):
    return el.tag.split("}")[-1]


def main():
    checks = {}

    # ── TBox: the ladder chain, exact ──
    doc = W.document()
    root = ET.fromstring(doc)                      # well-formed or raises
    edges = {}
    for el in root.iter():
        if _ln(el) == "Class" and el.attrib.get(f"{RDF}about", "").startswith("#AtLeast_"):
            name = el.attrib[f"{RDF}about"][1:]
            for sub in el:
                if _ln(sub) == "subClassOf" and f"{RDF}resource" in sub.attrib:
                    edges[name] = sub.attrib[f"{RDF}resource"][1:]
    expected = {"AtLeast_function": "Node"}
    for a, b in zip(O.LADDER, O.LADDER[1:]):
        expected[f"AtLeast_{b}"] = f"AtLeast_{a}"
    checks["ladder_chain_exact"] = edges == expected

    # leq on levels IS subsumption: for ALL level pairs, i<=j iff
    # AtLeast_j reaches AtLeast_i through the parsed subclass edges.
    def subsumed_by(sub, sup):                     # sub ⊑ sup ?
        cur = sub
        while cur in edges:
            if cur == sup:
                return True
            cur = edges[cur]
        return cur == sup
    ok = True
    for i in range(len(O.LADDER)):
        for j in range(len(O.LADDER)):
            dl = subsumed_by(f"AtLeast_{O.LADDER[j]}", f"AtLeast_{O.LADDER[i]}")
            if dl != (i <= j):
                ok = False
    checks["leq_is_subsumption_all_pairs"] = ok

    # Golden/Agent are DEFINED classes with exactly the right restrictions
    def defined_props(cname):
        props = set()
        for el in root.iter():
            if (_ln(el) == "Class"
                    and el.attrib.get(f"{RDF}about") == f"#{cname}"):
                for r in el.iter():
                    if _ln(r) == "onProperty":
                        props.add(r.attrib[f"{RDF}resource"][1:])
        return props
    checks["golden_agent_defined_exact"] = (
        defined_props("Golden") == {f"witnessed_{s}" for s in O.COOLING}
        and defined_props("Agent") == {f"rite_{r}" for r in O.AGENT_RITES})

    # ── individuals: all 13 booleans explicit ──
    def bools_of(xml, name):
        r = ET.fromstring(xml)
        for el in r.iter():
            if (_ln(el) == "NamedIndividual"
                    and el.attrib.get(f"{RDF}about") == f"#{name}"):
                return ({_ln(c): c.text for c in el
                         if _ln(c).startswith(("witnessed_", "rite_"))},
                        [c.attrib.get(f"{RDF}resource") for c in el
                         if _ln(c) == "type"])
        return {}, []
    top_doc = W.document(D.TOP)
    vals, types = bools_of(top_doc, "state")
    checks["top_state_all_true"] = (
        len(vals) == 13 and all(v == "true" for v in vals.values())
        and types == [f"#AtLeast_{O.LADDER[-1]}"])
    bot_doc = D.BOTTOM.render_owl()                # the stamped METHOD
    vals, types = bools_of(bot_doc, "state")
    checks["bottom_state_all_false_via_method"] = (
        len(vals) == 13 and all(v == "false" for v in vals.values())
        and types == ["#AtLeast_function"])

    # a Node renders its own ontology from its own public answer
    node = O.Node("thing_node")
    node.cool("execution", "test-witness")
    node.receive_rite("explanation", "test-witness")
    nd = node.render_owl()
    vals, _ = bools_of(nd, "thing_node")
    checks["node_renders_own_state"] = (
        vals["witnessed_execution"] == "true"
        and vals["witnessed_testing"] == "false"
        and vals["rite_explanation"] == "true"
        and vals["rite_review"] == "false")

    # ── rings: structural recursion + the closed round trip ──
    GREET = O2.RingSpec(
        name="Greet", adds=["greet"], requires=[],
        verbs=[O2.VerbSpec(name="greet", slots=["who", "salutation"],
                           source="return self.salutation + ', ' + self.who")])
    SHOUT = O2.RingSpec(
        name="Shout", adds=["shout"], requires=["greet"],
        verbs=[O2.VerbSpec(name="shout", slots=[],
                           source="return self.greet().upper() + '!'")])
    inst = O2.assemble("Greeter", [SHOUT, GREET])
    bind(inst, "who", "world")
    bind(inst, "salutation", "hello")
    onion_frags = W.render_onion(inst)
    joined = "\n".join(onion_frags)
    checks["recursion_contains_parts"] = all(
        frag in joined for ring in (SHOUT, GREET)
        for frag in W.render_ring(ring))
    odoc = W.document(inst)
    rings2 = W.rings_from_owl(odoc)
    checks["owl_to_rings_exact"] = (
        [r.name for r in rings2] == ["Shout", "Greet"]
        and rings2[1].verbs[0].slots == ["who", "salutation"]
        and rings2[0].requires == ["greet"])
    inst2 = O2.assemble("Greeter", rings2)
    bind(inst2, "who", "world")
    bind(inst2, "salutation", "hello")
    checks["roundtrip_behavior_and_render_fixpoint"] = (
        inst2.get_method("shout")() == "HELLO, WORLD!"
        and W.document(inst2) == odoc)

    # ── the store renders via the kleene_climb derivation ──
    with tempfile.TemporaryDirectory() as td:
        store = CT.Store(os.path.join(td, "store.jsonl"))
        rec = CT.mirror(main)
        rec["name"] = "thing"
        store.append(rec)
        gauged = dict(rec)
        gauged["golden_history"] = [["execution", "testing"]]
        store.append(gauged)
        sdoc = store.render_owl()
        vals, _ = bools_of(sdoc, "thing")
        checks["store_individual_derived"] = (
            vals["witnessed_execution"] == "true"
            and vals["witnessed_testing"] == "true"
            and vals["witnessed_independent_witnessing"] == "false"
            and vals["rite_graph_identity"] == "true")

    # ── the whole SDK, one ontology ──
    sdk_doc = W.render_sdk_owl()
    vals, types = bools_of(sdk_doc, "lfpoop_sdk")
    checks["sdk_document_honest"] = (
        len(vals) == 13 and all(v == "true" for v in vals.values())
        and types == ["#AtLeast_graph_entity"])

    # ── owlready2 load (lab env) / Pellet classification (HOST-GATED) ──
    try:
        import owlready2
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "lfpoop_sdk.owl")
            with open(p, "w") as f:
                f.write(sdk_doc)
            world = owlready2.World()
            onto = world.get_ontology(f"file://{p}").load()
            cls = {c.name for c in onto.classes()}
            ind = {i.name for i in onto.individuals()}
            sdk = [i for i in onto.individuals() if i.name == "lfpoop_sdk"][0]
            checks["owlready2_loads_and_reads"] = (
                {"Node", "Golden", "Agent", "AtLeast_function",
                 "AtLeast_compiler_improvement"} <= cls
                and "lfpoop_sdk" in ind
                and getattr(sdk, "witnessed_execution") == [True])
        import shutil
        if shutil.which("java"):
            with world.get_ontology(W.IRI):
                owlready2.sync_reasoner(world, infer_property_values=True)
            golden = {i.name for i in world[f"{W.IRI}#Golden"].instances()}
            checks["pellet_classifies_golden"] = "lfpoop_sdk" in golden
        else:
            print("  SKIP  pellet_classifies_golden (HOST-GATED: no Java in "
                  "the lab; run on host to reasoner-verify Golden/Agent)")
    except ImportError:
        print("  SKIP  owlready2 load (not importable here; run under the "
              "soma env for the load check)")

    print()
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print(f"\nLFPOOP-OWL: the ladder IS a subsumption chain (all pairs), "
          f"golden/agent are DEFINED classes, every class renders its own "
          f"ontology (structural recursion — composites contain their parts' "
          f"renders), OWL↔rings round-trips to a render fixpoint, and the "
          f"whole SDK emits ONE honest ontology. {len(checks)} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
