"""LFPOOP-OWL — everything recursively renders its own ontology. Stdlib only.

Every LFPOOP construct already IS a DL statement, so render_owl is not an
adapter, it is a READING:

  * the realization ladder = a subsumption chain: AtLeast_<rung> classes,
    AtLeast_program ⊑ AtLeast_function … — the Scott order on levels IS
    DL subsumption (knowing ≥s2 implies knowing ≥s1 whenever s1 ⊑ s2);
  * a State / Node = an INDIVIDUAL with boolean property assertions
    (witnessed_<step>, rite_<rite> — all thirteen asserted explicitly, true
    or false, so hasValue restrictions can classify);
  * golden / is_agent = DEFINED (equivalent) classes — Golden ≡ Node ⊓ the
    seven witnessed hasValue-true restrictions; Agent ≡ Node ⊓ the six rite
    restrictions — classification of individuals is a REASONER's job
    (host-gated: the lab has owlready2 but no Java, so Pellet runs on host);
  * a ring's adds/requires/verbs = an OWL class with property restrictions
    (hasValue on cap_/verb_ individuals; verb source + slots ride the verb
    individual as data — the round trip is closed by rings_from_owl);
  * a store = one individual per node, located via the SAME derivation
    kleene_climb uses (no artifact, no claim — the OWL says what the store
    can prove).

THE PRINCIPLE: render_owl is STRUCTURAL RECURSION — a piece renders itself;
a composite renders BY composing its parts' renders (an assembled onion's
fragments literally contain its rings' fragments; the SDK document is the
colimit of all sub-renders). The thing and its description are one structure
at every grain. render (text) / describe (tree) / render_owl (ontology) =
one functor, three targets.

Import side effect: render_owl() is stamped as a METHOD on ontology.Node,
domain.State and codething.Store (and onion2's RingSpec/VerbSpec when
pydantic is present) — every class renders its own ontology.
"""
import xml.etree.ElementTree as ET

from . import domain as D
from . import ontology as O
from .climb import _node_state
from .codething import Store

IRI = "https://github.com/sancovp/lfpoop/lfpoop.owl"
XSD_BOOL = "http://www.w3.org/2001/XMLSchema#boolean"
XSD_STR = "http://www.w3.org/2001/XMLSchema#string"

_HEADER = (
    '<?xml version="1.0"?>\n'
    '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n'
    '         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"\n'
    '         xmlns:owl="http://www.w3.org/2002/07/owl#"\n'
    f'         xml:base="{IRI}"\n'
    f'         xmlns="{IRI}#">\n'
    f'  <owl:Ontology rdf:about="{IRI}"/>\n')


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ── the TBox: the ontology renders ITSELF ───────────────────────────────────

def _bool_props():
    return ([f"witnessed_{s}" for s in O.COOLING]
            + [f"rite_{r}" for r in O.AGENT_RITES])


def render_tbox():
    """The Manual's structure as DL — the ontology's own render_owl."""
    fr = ['  <owl:Class rdf:about="#Node"/>',
          '  <owl:Class rdf:about="#Ring"/>',
          '  <owl:Class rdf:about="#Capability"/>',
          '  <owl:Class rdf:about="#Verb"/>']
    # the ladder as a subsumption chain (leq on levels IS ⊑)
    prev = "Node"
    for rung in O.LADDER:
        fr.append(f'  <owl:Class rdf:about="#AtLeast_{rung}">\n'
                  f'    <rdfs:subClassOf rdf:resource="#{prev}"/>\n'
                  f'  </owl:Class>')
        prev = f"AtLeast_{rung}"
    for p in _bool_props():
        fr.append(f'  <owl:DatatypeProperty rdf:about="#{p}">\n'
                  f'    <rdfs:domain rdf:resource="#Node"/>\n'
                  f'    <rdfs:range rdf:resource="{XSD_BOOL}"/>\n'
                  f'  </owl:DatatypeProperty>')
    for p in ("adds", "requires", "has_verb"):
        fr.append(f'  <owl:ObjectProperty rdf:about="#{p}"/>')
    for p in ("verb_name", "verb_source", "verb_slots", "bound"):
        fr.append(f'  <owl:DatatypeProperty rdf:about="#{p}"/>')

    def _defined(name, props):
        rs = "\n".join(
            f'        <owl:Restriction>\n'
            f'          <owl:onProperty rdf:resource="#{p}"/>\n'
            f'          <owl:hasValue rdf:datatype="{XSD_BOOL}">true'
            f'</owl:hasValue>\n'
            f'        </owl:Restriction>' for p in props)
        return (f'  <owl:Class rdf:about="#{name}">\n'
                f'    <owl:equivalentClass>\n'
                f'      <owl:Class><owl:intersectionOf '
                f'rdf:parseType="Collection">\n'
                f'        <owl:Class rdf:about="#Node"/>\n{rs}\n'
                f'      </owl:intersectionOf></owl:Class>\n'
                f'    </owl:equivalentClass>\n'
                f'  </owl:Class>')
    # golden / is_agent as DEFINED classes — the reasoner's job, not code's
    fr.append(_defined("Golden", [f"witnessed_{s}" for s in O.COOLING]))
    fr.append(_defined("Agent", [f"rite_{r}" for r in O.AGENT_RITES]))
    return fr


# ── individuals: State / Node / Store ───────────────────────────────────────

def render_state(state: D.State, name: str):
    """A domain element as an individual — all 13 booleans EXPLICIT."""
    lines = [f'  <owl:NamedIndividual rdf:about="#{_esc(name)}">',
             f'    <rdf:type rdf:resource='
             f'"#AtLeast_{O.LADDER[state.level]}"/>']
    for s in O.COOLING:
        v = "true" if s in state.witnessed else "false"
        lines.append(f'    <witnessed_{s} rdf:datatype="{XSD_BOOL}">'
                     f'{v}</witnessed_{s}>')
    for r in O.AGENT_RITES:
        v = "true" if r in state.rites else "false"
        lines.append(f'    <rite_{r} rdf:datatype="{XSD_BOOL}">'
                     f'{v}</rite_{r}>')
    lines.append('  </owl:NamedIndividual>')
    return ["\n".join(lines)]


def render_node(node: O.Node):
    """An ontology.Node reads its own public answer, then renders as a
    State individual (the composite delegates — structural recursion)."""
    a = node.next_admissible_closure()
    witnessed = [s for s in O.COOLING if s not in a["unwitnessed_cooling"]]
    rites = [r for r in O.AGENT_RITES if r not in a["missing_rites"]]
    st = D.State.make(O.LADDER.index(node.realization_level), witnessed, rites)
    return render_state(st, node.name)


def render_store(store: Store):
    """One individual per stored node — located exactly as kleene_climb
    locates it (derived from artifacts, never trusted)."""
    names = sorted({r.get("name") for r in store.records()
                    if r.get("kind") != "witness" and r.get("name")})
    fr = []
    for n in names:
        fr += render_state(_node_state(n, store), n)
    return fr


# ── rings / onions (lazy: pydantic side) ────────────────────────────────────

def render_ring(ring):
    """A RingSpec as an OWL class with property restrictions; its verbs as
    individuals carrying source+slots (so the loop closes: rings_from_owl)."""
    fr = []
    subs = []
    for cap in list(ring.adds) + list(ring.requires):
        fr.append(f'  <owl:NamedIndividual rdf:about="#cap_{_esc(cap)}">\n'
                  f'    <rdf:type rdf:resource="#Capability"/>\n'
                  f'  </owl:NamedIndividual>')
    for prop, caps in (("adds", ring.adds), ("requires", ring.requires)):
        for cap in caps:
            subs.append(
                f'    <rdfs:subClassOf><owl:Restriction>\n'
                f'      <owl:onProperty rdf:resource="#{prop}"/>\n'
                f'      <owl:hasValue rdf:resource="#cap_{_esc(cap)}"/>\n'
                f'    </owl:Restriction></rdfs:subClassOf>')
    for v in ring.verbs:
        vid = f"verb_{ring.name}_{v.name}"
        fr.append(
            f'  <owl:NamedIndividual rdf:about="#{_esc(vid)}">\n'
            f'    <rdf:type rdf:resource="#Verb"/>\n'
            f'    <verb_name rdf:datatype="{XSD_STR}">'
            f'{_esc(v.name)}</verb_name>\n'
            f'    <verb_source rdf:datatype="{XSD_STR}">'
            f'{_esc(v.source)}</verb_source>\n'
            f'    <verb_slots rdf:datatype="{XSD_STR}">'
            f'{_esc(",".join(v.slots))}</verb_slots>\n'
            f'  </owl:NamedIndividual>')
        subs.append(
            f'    <rdfs:subClassOf><owl:Restriction>\n'
            f'      <owl:onProperty rdf:resource="#has_verb"/>\n'
            f'      <owl:hasValue rdf:resource="#{_esc(vid)}"/>\n'
            f'    </owl:Restriction></rdfs:subClassOf>')
    fr.append(f'  <owl:Class rdf:about="#{_esc(ring.name)}">\n'
              f'    <rdfs:subClassOf rdf:resource="#Ring"/>\n'
              + "\n".join(subs) + '\n  </owl:Class>')
    return fr


def render_onion(inst):
    """An assembled onion instance: its fragments CONTAIN its rings'
    fragments (the composite composes its parts' renders — the colimit),
    plus its class as the intersection of ring classes and ITSELF as an
    individual carrying its binding state."""
    from . import onion2 as O2
    data = O2.to_data(inst)
    fr = []
    ring_names = []
    for rd in data["rings"]:
        ring = O2.RingSpec(**rd)
        ring_names.append(ring.name)
        fr += render_ring(ring)                      # ← the recursion
    members = "\n".join(f'        <owl:Class rdf:about="#{_esc(n)}"/>'
                        for n in ring_names)
    fr.append(f'  <owl:Class rdf:about="#Onion_{_esc(data["name"])}">\n'
              f'    <owl:equivalentClass>\n'
              f'      <owl:Class><owl:intersectionOf '
              f'rdf:parseType="Collection">\n{members}\n'
              f'      </owl:intersectionOf></owl:Class>\n'
              f'    </owl:equivalentClass>\n'
              f'  </owl:Class>')
    binds = "\n".join(
        f'    <bound rdf:datatype="{XSD_STR}">'
        f'{_esc(k)}={_esc(v)}</bound>' for k, v in data["bindings"].items())
    fr.append(f'  <owl:NamedIndividual '
              f'rdf:about="#instance_{_esc(data["name"])}">\n'
              f'    <rdf:type rdf:resource="#Onion_{_esc(data["name"])}"/>\n'
              + (binds + "\n" if binds else "")
              + '  </owl:NamedIndividual>')
    return fr


def rings_from_owl(owl_text: str):
    """OWL → RingSpecs — the other direction, closing the loop (the
    owl22python move, on our own emission)."""
    from . import onion2 as O2
    root = ET.fromstring(owl_text)
    def ln(el):
        return el.tag.split("}")[-1]
    RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
    verbs = {}
    for el in root.iter():
        if ln(el) == "NamedIndividual":
            about = el.attrib.get(f"{RDF}about", "")
            if about.startswith("#verb_"):
                vname = src = slots = ""
                for c in el:
                    if ln(c) == "verb_name":
                        vname = c.text or ""
                    if ln(c) == "verb_source":
                        src = c.text or ""
                    if ln(c) == "verb_slots":
                        slots = c.text or ""
                # verb_name is authoritative (ids are underscore-lossy —
                # the 2026-07-26 verifier's finding); the id split is only
                # a fallback for documents emitted before verb_name existed
                verbs[about[1:]] = O2.VerbSpec(
                    name=vname or about[1:].split("_", 2)[2], source=src,
                    slots=[s for s in slots.split(",") if s])
    rings = []
    for el in root.iter():
        if ln(el) != "Class":
            continue
        about = el.attrib.get(f"{RDF}about", "")
        is_ring, adds, requires, ring_verbs = False, [], [], []
        for sub in el:
            if ln(sub) != "subClassOf":
                continue
            if sub.attrib.get(f"{RDF}resource") == "#Ring":
                is_ring = True
            for rest in sub:
                if ln(rest) != "Restriction":
                    continue
                prop = val = None
                for c in rest:
                    if ln(c) == "onProperty":
                        prop = c.attrib.get(f"{RDF}resource", "")[1:]
                    if ln(c) == "hasValue":
                        val = c.attrib.get(f"{RDF}resource", "")[1:]
                if prop == "adds":
                    adds.append(val[4:])             # cap_<name>
                elif prop == "requires":
                    requires.append(val[4:])
                elif prop == "has_verb":
                    ring_verbs.append(verbs[val])
        if is_ring:
            rings.append(O2.RingSpec(name=about[1:], adds=adds,
                                     requires=requires, verbs=ring_verbs))
    return rings


# ── the functor + the whole-SDK render ──────────────────────────────────────

def render_owl(obj):
    """ONE structural-recursion functor: fragments for any SDK thing."""
    if isinstance(obj, D.State):
        return render_state(obj, "state")
    if isinstance(obj, O.Node):
        return render_node(obj)
    if isinstance(obj, Store):
        return render_store(obj)
    if obj is O or getattr(obj, "__name__", "") == "lfpoop.ontology":
        return render_tbox()
    try:
        from . import onion2 as O2
        if isinstance(obj, O2.RingSpec):
            return render_ring(obj)
        if "__onion_spec__" in getattr(obj, "__dict__", {}):
            return render_onion(obj)
    except ImportError:
        pass
    raise TypeError(f"render_owl: no OWL reading for {type(obj).__name__}")


def document(*objs) -> str:
    """The colimit: TBox + every object's fragments, ONE ontology."""
    fr = render_tbox()
    for o in objs:
        fr += render_owl(o)
    return _HEADER + "\n".join(fr) + "\n</rdf:RDF>\n"


def render_sdk_owl(store_path=None) -> str:
    """The ENTIRE top-level onion as one ontology: the TBox, the SDK
    located in its own domain, and every node the store can prove."""
    store = Store(store_path) if store_path else Store()
    fr = render_tbox()
    fr += render_state(D.sdk_state(store.path), "lfpoop_sdk")
    fr += render_store(store)
    return _HEADER + "\n".join(fr) + "\n</rdf:RDF>\n"


# ── every class renders its own ontology (the import-time stamp) ────────────

def _self_document(self):
    return document(self)


O.Node.render_owl = _self_document
D.State.render_owl = _self_document
Store.render_owl = _self_document
try:
    from . import onion2 as _O2
    _O2.RingSpec.render_owl = _self_document
except ImportError:
    pass
