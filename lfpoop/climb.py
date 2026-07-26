"""kleene_climb — the ONE instruction. Stdlib only; belongs to the core.

kleene_climb(subject, store, step=False) unifies the pieces that already
exist (ontology.next_admissible_closure, domain.kleene/sdk_state, the
compiler's per-artifact gauge checks) into one callable that:

  1. LOCATES you — reads the REAL position from artifacts: the SDK itself
     via domain.sdk_state(); any named artifact via its own store records
     (level from its latest record; witnessed cooling = the union of its
     recorded golden_history gauge passes, plus independent_witnessing iff
     an EXTERNAL witness record exists; rites via codething.agentify).
     No artifact, no claim — locate never trusts a label it can't derive.
  2. ANSWERS the one question — the next admissible closure (deterministic
     schedule: cooling → rites → the next rung → fixpoint) plus EXACTLY
     which artifact/check that closure requires (REQUIREMENTS, data).
  3. optionally TAKES the step (step=True) — and the only step it can ever
     take is the RUNG ADVANCE, because cooling and rites are DERIVED from
     artifacts: if the artifact existed the state would already contain the
     step. So: next is cooling/rite → REFUSE, naming the artifact to
     produce (kleene_climb never fabricates); next is the rung → append a
     witnessed transition record to the store (the no-skip law, recorded).

soup()/heat() in onion2 are this same instruction at METHOD grain (the
substitution LFP); this module is it at NODE grain (the realization LFP).
"""
from . import domain as D
from . import ontology as O
from .codething import Store, agentify, external_witnesses

# What each closure REQUIRES — the answer's "exactly which checks" half.
REQUIREMENTS = {
    "execution": "a compiler run whose execute verb imported the artifact "
                 "(a store record from a real materialized run)",
    "testing": "a green suite AND its process re-run, recorded in a gauge "
               "pass (golden_history)",
    "relational_validation": "the artifact's declared relations pass the "
                             "assembly gate (rings validate), gauge-recorded",
    "observation": "the artifact mirrored into the append-only store",
    "independent_witnessing": "an EXTERNAL accept_witness record — the "
                              "handler seat; never self-grantable",
    "provenance": "≥2 distinct provenance entries on the node's record",
    "append_only_crystallization": "a prior record for the node in the "
                                   "append-only store (history ≥ 1)",
    "explanation": "the node's OWN generated documentation artifact",
    "evolution": "≥2 distinct source identities in the node's history",
    "export": "the node's OWN generated package artifact",
    "review": "an external witness accepted it (the handler seat)",
    "graph_identity": "a content-hash identity on the node's record",
    "rung": "everything below witnessed; advance is recorded, witnessed, "
            "one rung only (the no-skip law)",
}


def _node_state(name: str, store: Store) -> D.State:
    """A stored artifact located in the domain — derived, never trusted."""
    hist = [r for r in store.history(name) if r.get("kind") != "witness"]
    if not hist:
        return D.BOTTOM
    latest = hist[-1]
    level = O.LADDER.index(latest.get("realization_level", "function"))
    witnessed = set()
    for rec in hist:
        for gauge_pass in rec.get("golden_history", []):
            witnessed |= {s for s in gauge_pass if s in O.COOLING}
    ext = external_witnesses(store, name)
    if ext:
        witnessed.add("independent_witnessing")
    else:
        witnessed.discard("independent_witnessing")   # never self-derived
    rites = agentify(name, store)["granted"]
    return D.State.make(level, witnessed, rites)


def _next_closure(s: D.State) -> dict:
    nxt = D.closure_step(s)
    if nxt == s:
        return {"kind": "fixpoint", "name": None, "requires": None}
    if set(nxt.witnessed) - set(s.witnessed):
        (name,) = set(nxt.witnessed) - set(s.witnessed)
        return {"kind": "cooling", "name": name,
                "requires": REQUIREMENTS[name]}
    if set(nxt.rites) - set(s.rites):
        (name,) = set(nxt.rites) - set(s.rites)
        return {"kind": "rite", "name": name, "requires": REQUIREMENTS[name]}
    return {"kind": "rung", "name": O.LADDER[nxt.level],
            "requires": REQUIREMENTS["rung"]}


def kleene_climb(subject: str = "sdk", store: Store = None,
                 step: bool = False, witness: str = "kleene_climb") -> dict:
    """WHERE AM I / WHAT'S NEXT / (optionally) TAKE IT. Returns data:
    {subject, position:{level,witnessed,rites}, distance, next, taken,
    refusal}."""
    if subject == "sdk":
        state = D.sdk_state(store.path if store else None)
    else:
        if store is None:
            store = Store()
        state = _node_state(subject, store)
    nxt = _next_closure(state)
    distance = len(D.kleene(state)) - 1
    taken, refusal = False, None
    if step:
        if subject == "sdk":
            refusal = ("the SDK's state is DERIVED from repository "
                       "artifacts — kleene_climb writes no repo artifacts; "
                       "produce the artifact and re-locate")
        elif nxt["kind"] == "fixpoint":
            refusal = "already at the fixpoint — nothing to take"
        elif nxt["kind"] in ("cooling", "rite"):
            refusal = (f"cannot take {nxt['kind']} {nxt['name']}: it is "
                       f"derived from artifacts, never fabricated — "
                       f"produce: {nxt['requires']}")
        else:                                      # the rung: recordable
            hist = [r for r in store.history(subject)
                    if r.get("kind") != "witness"]
            rec = dict(hist[-1])
            frm = rec.get("realization_level", "function")
            to = O.LADDER[state.level + 1]
            rec["realization_level"] = to
            rec["provenance"] = rec.get("provenance", []) + [
                f"transition:{frm}->{to}:by:{witness}"]
            store.append(rec)
            taken = True
            state = _node_state(subject, store)
            nxt = _next_closure(state)
            distance = len(D.kleene(state)) - 1
    return {
        "subject": subject,
        "question": O.THE_QUESTION,
        "position": {"level": O.LADDER[state.level],
                     "witnessed": list(state.witnessed),
                     "rites": list(state.rites)},
        "distance": distance,
        "next": nxt,
        "taken": taken,
        "refusal": refusal,
    }
