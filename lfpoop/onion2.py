"""ONION-V2 — the onion runtime riding the ORIGINAL kits, everything as data.

v1 (onion.py) synthesizes classes from @ring-decorated CODE. v2 makes the ring
itself DATA and adds the ACTIVATION SEMANTICS — the atom of the whole kit:

  * a RING is a RenderablePiece MODEL (pydantic_stack_core): name, adds,
    requires, and its VERBS — each verb a template: source + declared SLOTS;
  * assemble() generates the class via pydantic create_model (the owl22python
    move) and attaches each verb at runtime via the vendored
    TemplateMethodMixin.add_method — nobody hand-writes the assembled class;
  * A METHOD ACTIVATES THROUGH SETTING ATTRIBUTES THAT MAKE AN LFP OF
    SUBSTITUTIONS: a verb with unbound slots is SOUP — calling it refuses,
    naming exactly the unbound slots; bind() is one MONOTONE substitution step
    (a binding added, never removed — rebinding refuses); the verb activates
    exactly when its free-slot set is empty. heat = the free-variable count;
    ground = cold = callable ("bind all the way to a function");
  * morph() re-fixes the LFP under a swapped ring stack: identity lives in
    the config, the class is merely its render — bindings whose slots survive
    are TRANSPORTED, the rest are named as dropped;
  * to_data()/from_data() round-trip the WHOLE assembly INCLUDING its binding
    state; parse_json()/parse_xml() are thin parsers into the same data —
    the substrate is format-agnostic (OWL arrives with render_owl / LFPOOP-OWL).

v1's laws carry over unchanged as the composition gate: requires validated
inside-out with the gap named; every self.X a verb's body touches must be in
adds ∪ requires ∪ slots or the assembly REFUSES naming the leak.

Requires pydantic + pydantic_stack_core (the one optional-extra module in the
SDK; the core stays stdlib+uco). kleene_climb at method grain = soup()/heat().
"""
import ast
import json
import textwrap
import xml.etree.ElementTree as ET
from typing import List

from pydantic import BaseModel, Field, create_model
from pydantic_stack_core import RenderablePiece

from .onion import StackError
from .template_mixins import TemplateAttributeMixin, TemplateMethodMixin


class SoupError(StackError):
    """A verb called before its substitution LFP closed — carries the
    unbound slots by name."""


# ── the ring as DATA ────────────────────────────────────────────────────────

class VerbSpec(RenderablePiece):
    """One verb: a method TEMPLATE with declared slots. `source` is the body
    (a function body over `self`); `slots` are the attribute names the body
    reads that must be BOUND on the instance before the verb activates."""
    name: str
    source: str
    slots: List[str] = Field(default_factory=list)

    def render(self) -> str:
        sig = f"def {self.name}(self, *args, **kwargs):"
        body = textwrap.indent(textwrap.dedent(self.source).strip(), "    ")
        slots = f"  # slots: {self.slots}" if self.slots else ""
        return f"{sig}{slots}\n{body}"


class RingSpec(RenderablePiece):
    """A ring as a data model: declared alphabet + its verb templates.
    MetaStack-composable; render() is the declaration projection."""
    name: str
    adds: List[str] = Field(default_factory=list)
    requires: List[str] = Field(default_factory=list)
    verbs: List[VerbSpec] = Field(default_factory=list)

    def render(self) -> str:
        head = (f"ring {self.name}(adds={self.adds}, "
                f"requires={self.requires}):")
        vs = "\n".join(textwrap.indent(v.render(), "  ") for v in self.verbs)
        return f"{head}\n{vs}" if self.verbs else head


# ── assembly (create_model + add_method, gated like v1) ─────────────────────

class OnionBase(BaseModel, TemplateAttributeMixin, TemplateMethodMixin):
    """The generated classes' base: a pydantic model that accepts runtime
    attributes (substitutions) and runtime methods (the mixins)."""
    model_config = {"extra": "allow", "arbitrary_types_allowed": True}


def _verb_accesses(source: str):
    """Every self.X the verb body touches — AST-scanned, enforced not
    trusted (same law as v1's _body_accesses)."""
    wrapped = ("def _verb(self, *args, **kwargs):\n"
               + textwrap.indent(textwrap.dedent(source).strip() or "pass",
                                 "    "))
    tree = ast.parse(wrapped)          # raises on unparsable source: fail loud
    used = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "self"
                and not node.attr.startswith("_")):
            used.add(node.attr)
    return used


def _compile_verb(verb: VerbSpec):
    ns = {}
    code = ("def {n}(self, *args, **kwargs):\n".format(n=verb.name)
            + textwrap.indent(textwrap.dedent(verb.source).strip() or "pass",
                              "    "))
    exec(code, {}, ns)                  # the template, made callable
    return ns[verb.name]


def _slot_gate(verb: VerbSpec, fn):
    """The activation gate: refuse while the substitution LFP is open."""
    def gated(self, *args, **kwargs):
        missing = [s for s in verb.slots if s not in _ledger(self)]
        if missing:
            raise SoupError(
                f"verb {verb.name} is SOUP: unbound slots {missing} — "
                f"bind() each (one substitution per step); the verb "
                f"activates at the LFP of substitutions")
        return fn(self, *args, **kwargs)
    gated.__name__ = verb.name
    gated.__verb_slots__ = tuple(verb.slots)
    return gated


def assemble(name: str, rings: List[RingSpec], base_capabilities=()):
    """Generate the onion class from ring DATA and return an INSTANCE (the
    binding environment lives at instance grain). First-listed ring is
    outermost; validation is inside-out, refusals name the gap (v1's laws)."""
    available = set(base_capabilities)
    slot_union = set()
    for r in reversed(rings):                      # innermost first
        missing = [q for q in r.requires if q not in available]
        if missing:
            raise StackError(
                f"ring {r.name} requires {missing} — not provided by the "
                f"stack beneath it (refused; provide the capability or "
                f"reorder the rings)")
        for v in r.verbs:
            if v.name not in r.adds:
                raise StackError(
                    f"ring {r.name} defines verb {v.name} outside its "
                    f"declared adds {r.adds} (refused; declare it)")
            declared = set(r.adds) | set(r.requires) | set(v.slots)
            leaks = sorted(_verb_accesses(v.source) - declared)
            if leaks:
                raise StackError(
                    f"ring {r.name} verb {v.name} accesses undeclared "
                    f"capabilities {leaks} — a capability leak (refused; "
                    f"declare them in requires or slots)")
            slot_union |= set(v.slots)
        available |= set(r.adds)
    Model = create_model(name, __base__=OnionBase)
    inst = Model()
    inst.__dict__["_substitutions"] = {}           # the binding ledger
    inst.__dict__["__onion_spec__"] = {
        "name": name,
        "rings": [json.loads(r.model_dump_json()) for r in rings],
        "slots": sorted(slot_union),
    }
    for r in reversed(rings):                      # attach innermost first
        for v in r.verbs:
            inst.add_method(v.name, _slot_gate(v, _compile_verb(v)),
                            description=f"ring {r.name} verb (slots {v.slots})")
    return inst


# ── the substitution LFP (bind / heat / soup) ───────────────────────────────

def _ledger(inst) -> dict:
    return inst.__dict__.setdefault("_substitutions", {})


def bind(inst, slot: str, value):
    """ONE substitution step — monotone: a binding is added, never removed
    or replaced (rebinding refuses; changing config is morph()'s job)."""
    led = _ledger(inst)
    if slot in led:
        raise StackError(
            f"slot {slot} is already bound — substitutions are MONOTONE "
            f"(refused; to change configuration, morph())")
    led[slot] = value
    setattr(inst, slot, value)                     # the body reads self.<slot>
    return inst


def soup(inst) -> dict:
    """Per-verb unbound slots — kleene_climb at method grain: where each
    method is on its own substitution chain."""
    led = _ledger(inst)
    out = {}
    for vname, fn in inst.get_all_methods().items():
        missing = [s for s in getattr(inst.get_method(vname),
                                      "__verb_slots__", ())
                   if s not in led]
        if missing:
            out[vname] = missing
    return out


def heat(inst) -> int:
    """The free-variable count of the whole instance: how many distinct
    slots remain unbound. 0 = ground = cold = every verb active."""
    return len({s for missing in soup(inst).values() for s in missing})


# ── morph: re-fix the LFP under a swapped stack ─────────────────────────────

def morph(inst, name: str, new_rings: List[RingSpec], base_capabilities=()):
    """One class morphs into another at runtime through config swapping:
    build the new assembly, TRANSPORT every binding whose slot survives,
    name what dropped. Returns (new_instance, report)."""
    new_inst = assemble(name, new_rings, base_capabilities)
    new_slots = set(new_inst.__dict__["__onion_spec__"]["slots"])
    old = _ledger(inst)
    transported, dropped = [], []
    for slot, value in old.items():
        if slot in new_slots:
            bind(new_inst, slot, value)
            transported.append(slot)
        else:
            dropped.append(slot)
    return new_inst, {"transported": transported, "dropped": dropped,
                      "from": type(inst).__name__, "to": name}


# ── data round-trip + the thin format parsers ───────────────────────────────

def to_data(inst) -> dict:
    """The whole assembly INCLUDING its binding state, as plain data."""
    spec = inst.__dict__.get("__onion_spec__")
    if spec is None:
        raise StackError(f"{type(inst).__name__} is not an assembled onion")
    return {"name": spec["name"], "rings": spec["rings"],
            "bindings": dict(_ledger(inst))}


def from_data(data: dict):
    """Rebuild the identical instance — the activation state travels
    through data too."""
    rings = [RingSpec(**r) for r in data["rings"]]
    inst = assemble(data["name"], rings)
    for slot, value in data.get("bindings", {}).items():
        bind(inst, slot, value)
    return inst


def parse_json(text: str) -> dict:
    """JSON is a thin parser into the same data."""
    return json.loads(text)


def parse_xml(text: str) -> dict:
    """XML is a thin parser into the same data:
    <onion name=..><ring name=.. adds="a,b" requires="">
      <verb name=.. slots="x,y">body source</verb></ring>
      <binding slot=.. value=../></onion>"""
    root = ET.fromstring(text)
    def _csv(s):
        return [x for x in (s or "").split(",") if x]
    rings = []
    for r in root.findall("ring"):
        rings.append({
            "name": r.attrib["name"],
            "adds": _csv(r.attrib.get("adds")),
            "requires": _csv(r.attrib.get("requires")),
            "verbs": [{"name": v.attrib["name"],
                       "slots": _csv(v.attrib.get("slots")),
                       "source": textwrap.dedent(v.text or "").strip()}
                      for v in r.findall("verb")],
        })
    bindings = {b.attrib["slot"]: b.attrib["value"]
                for b in root.findall("binding")}
    return {"name": root.attrib["name"], "rings": rings,
            "bindings": bindings}
