"""The onion runtime — the Mixin Rule, executable. Stdlib only.

Curried onion runtime stacking:
  * a RING is a categorical mixin with a DECLARED alphabet — what it adds,
    what it requires beneath it (the @ring decorator stamps the metadata and
    registers the ring by name, so assembly is data-driven);
  * stack() is RUNTIME class synthesis from a ring LIST — nobody hand-writes
    the assembled class; the first-listed ring is outermost (MRO order);
    stacking VALIDATES the alphabet chain inside-out and REFUSES with the gap
    named when a ring's requirement is unmet (refusal, not silent breakage);
  * curried(base) composes by partial application — each ring application
    binds one capability layer and returns a more-specialized constructor:
    the worker-binding spectrum as literal code;
  * to_data()/stack_from_data() round-trip an assembly through plain data —
    the class IS referable as data, which is what lets a graph decide the
    assembly at runtime.

Out-of-alphabet calls are AttributeError BY CONSTRUCTION (the method simply
does not exist on the assembled class) — capability security at the language
grain, not policy.
"""

RING_REGISTRY = {}


class StackError(ValueError):
    """A refused assembly — carries the named gap."""


def ring(adds=(), requires=()):
    """Declare a class as a categorical mixin (a ring) and register it."""
    def deco(cls):
        cls.__ring_adds__ = tuple(adds)
        cls.__ring_requires__ = tuple(requires)
        RING_REGISTRY[cls.__name__] = cls
        return cls
    return deco


def _capabilities(base):
    return {n for n in dir(base) if not n.startswith("_")}


def _body_accesses(ring_cls):
    """Every `self.X` attribute the ring's method bodies actually touch —
    AST-scanned so capability declarations are ENFORCED at assembly time,
    not trusted. Unscannable source (C ext, REPL) → empty (declared-only)."""
    import ast
    import inspect
    import textwrap
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(ring_cls)))
    except (OSError, TypeError, SyntaxError, IndentationError):
        return set()
    used = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "self"
                and not node.attr.startswith("_")):
            used.add(node.attr)
    return used


def stack(name, base, rings, ns=None):
    """Synthesize a class at runtime from a ring list (first = outermost).

    Validates inside-out: each ring's requires must be satisfied by the base
    plus the rings beneath it; an unmet requirement REFUSES with the gap
    named. The assembly is stamped with its own data (__ring_stack__) so any
    stacked class round-trips through to_data()."""
    available = _capabilities(base)
    for r in reversed(rings):          # innermost first
        missing = [req for req in getattr(r, "__ring_requires__", ())
                   if req not in available]
        if missing:
            raise StackError(
                f"ring {r.__name__} requires {missing} — not provided by the "
                f"stack beneath it (refused; provide the capability or "
                f"reorder the rings)")
        # ENFORCED capability (not just declared): every self.X the ring's
        # bodies touch must be in its own alphabet (adds ∪ requires). An
        # undeclared access is a LEAK and the assembly refuses, naming it.
        declared = (set(getattr(r, "__ring_adds__", ()))
                    | set(getattr(r, "__ring_requires__", ())))
        leaks = sorted(_body_accesses(r) - declared)
        if leaks:
            raise StackError(
                f"ring {r.__name__} accesses undeclared capabilities {leaks} "
                f"— a capability leak (refused; declare them in requires)")
        available |= set(getattr(r, "__ring_adds__", ()))
    cls = type(name, (*rings, base), dict(ns or {}))
    cls.__ring_stack__ = {"name": name, "base": base.__name__,
                          "rings": [r.__name__ for r in rings]}
    return cls


class Curried:
    """The curried composer: each call binds ONE ring and returns a new,
    more-specialized composer. .build(name) closes the composition."""

    def __init__(self, base, rings=()):
        self.base, self.rings = base, tuple(rings)

    def __call__(self, ring_cls):
        return Curried(self.base, (*self.rings, ring_cls))

    def build(self, name):
        # rings were applied inside-out; outermost-last → reverse for stack()
        return stack(name, self.base, list(reversed(self.rings)))


def curried(base):
    return Curried(base)


def to_data(cls) -> dict:
    """The assembly as plain data."""
    if not hasattr(cls, "__ring_stack__"):
        raise StackError(f"{cls.__name__} is not a stacked class")
    return dict(cls.__ring_stack__)


def stack_from_data(spec: dict, bases: dict):
    """Rebuild the identical class from data: ring names resolve through the
    registry; the base through the caller-supplied bases dict."""
    rings = []
    for rname in spec["rings"]:
        if rname not in RING_REGISTRY:
            raise StackError(f"unknown ring: {rname} (not registered)")
        rings.append(RING_REGISTRY[rname])
    if spec["base"] not in bases:
        raise StackError(f"unknown base: {spec['base']}")
    return stack(spec["name"], bases[spec["base"]], rings)
