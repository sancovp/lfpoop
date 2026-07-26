"""The UCO retrofit — LFPOOP's compiler loop on the universal chain ontology.

uco (sancovp/universal-chain-ontology): Link / Chain(Link) / Compiler(Chain)
— the homoiconic composition primitives, zero-dep. Here:

  * every Manual loop verb is a VerbLink;
  * the Compiler Loop is a uco.Chain of them (a Chain IS a Link, so the loop
    nests anywhere);
  * LfpoopCompiler is a uco.Compiler — the D:D→D seat: a Chain whose output
    (context['compiled']) is itself a Link (the loop-chain it builds);
  * meta_fixpoint_check() is compoctopus's MetaCompiler move: apply the
    compiler to a description of itself and verify compiled == hand-written,
    exactly — "the D:D→D fixed point is reached";
  * drive_node() connects the three layers: executing the UCO loop-chain
    applies domain.closure_step to a Node-state — one UCO cycle = one rung of
    the Kleene chain, so running the chain IS computing the fixpoint.
"""
from uco import Chain, Compiler, Link, LinkResult, LinkStatus

from . import domain
from . import ontology as O


class VerbLink(Link):
    """One Manual loop verb as a UCO Link. Conditional verbs no-op (and say
    so in context) unless witnessed_effect was truthy this cycle."""

    def __init__(self, verb, impl=None):
        if verb not in O.LOOP:
            raise ValueError(f"not a loop verb: {verb}")
        self.name = verb
        self.impl = impl

    async def execute(self, context=None, **_):
        ctx = dict(context or {})
        fired = not (self.name in O.CONDITIONAL_VERBS
                     and not ctx.get("witnessed_effect"))
        if fired and callable(self.impl):
            out = self.impl(ctx)
            if isinstance(out, dict):
                ctx = out
        if self.name == "witnessed_effect":
            ctx["witnessed_effect"] = bool(ctx.get("witnessed_effect", False))
        ctx.setdefault("trace", []).append((self.name, fired))
        return LinkResult(status=LinkStatus.SUCCESS, context=ctx)


def build_loop_chain(impls=None) -> Chain:
    """The Compiler Loop as a uco.Chain — verb order is the Manual's."""
    impls = impls or {}
    return Chain("lfpoop_loop", [VerbLink(v, impls.get(v)) for v in O.LOOP])


class _BuildLoop(Link):
    """The compile step: reads impls from context, emits the loop-chain."""
    name = "build_loop"

    async def execute(self, context=None, **_):
        ctx = dict(context or {})
        ctx["compiled"] = build_loop_chain(ctx.get("impls"))
        return LinkResult(status=LinkStatus.SUCCESS, context=ctx)


class LfpoopCompiler(Compiler):
    """The D:D→D seat on uco.Compiler: a Chain that PRODUCES the loop-chain
    (itself a Link) into context['compiled']."""

    def __init__(self):
        super().__init__("lfpoop_compiler", [_BuildLoop()])


async def meta_fixpoint_check() -> dict:
    """compoctopus meta.py's verification, here: compile the loop with the
    compiler and compare against the hand-built loop — exact describe()
    equality — then compile AGAIN from the compiled result's context
    (self-application) and verify idempotence. Both must hold for the
    fixed point to be called reached."""
    compiler = LfpoopCompiler()
    r1 = await compiler.execute({})
    compiled_1 = compiler.get_compiled(r1.context)
    hand = build_loop_chain()
    r2 = await compiler.execute(r1.context)
    compiled_2 = compiler.get_compiled(r2.context)
    return {
        "compiled_equals_handwritten":
            compiled_1.describe() == hand.describe(),
        "self_application_idempotent":
            compiled_1.describe() == compiled_2.describe(),
    }


def node_impls(state_box: dict):
    """Loop-verb impls that drive a domain State one Kleene rung per cycle.
    state_box = {"state": domain.State}; goldenize applies closure_step.
    witnessed_effect is TRUE iff the state is not yet the fixpoint — the
    loop's own conditional becomes the fixpoint test."""
    def observe(ctx):
        ctx["closure_answer"] = {
            "state": state_box["state"],
            "at_fixpoint": domain.closure_step(state_box["state"])
            == state_box["state"]}
        return ctx

    def witnessed_effect(ctx):
        ctx["witnessed_effect"] = not ctx["closure_answer"]["at_fixpoint"]
        return ctx

    def goldenize(ctx):
        state_box["state"] = domain.closure_step(state_box["state"])
        return ctx

    return {"observe": observe, "witnessed_effect": witnessed_effect,
            "goldenize": goldenize}


async def drive_node(start=None, max_cycles=64):
    """Run the UCO loop-chain until the domain fixpoint: one cycle = one F
    application. Returns (final_state, cycles, chain_of_states)."""
    box = {"state": start or domain.BOTTOM}
    loop = build_loop_chain(node_impls(box))
    states = [box["state"]]
    for cycle in range(1, max_cycles + 1):
        before = box["state"]
        await loop.execute({})
        if box["state"] == before:
            return box["state"], cycle, states
        states.append(box["state"])
    return box["state"], max_cycles, states
