"""envelope — the candidate envelope: LLM code as CHECKED CLAIMS (§0a addendum).

The LLM's output under LFPOOP is never bare code — it is a WRAPPED CANDIDATE:

    {"source": <one function def, as text>,
     "seat": "llm:<who>",                     # who proposed (required)
     "answers_demand": "<gap/queue id>",      # what gap this fills (required)
     "rationale": "<the global thinking>",    # intent, ontologized (required)
     "declares": {"reads": [...],             # external names it depends on
                  "writes": [...],            # names it defines
                  "ring": "<placement hypothesis>" | None},
     "predicted_fitness_direction": "up|neutral" (optional),
     "implements": [ontology refs] (optional)}

INTAKE LAW: the envelope is a CLAIM, not a trusted channel —
  * everything DERIVABLE is cross-checked against derivation:
      declared reads  vs the AST-exact free external names of the source
      declared writes vs the names the source defines
      declared ring   vs the wiring mass (the candidate must not claim a
                      ring when another known ring holds more of its reads)
    a mismatch is a REFUSAL NAMING THE DIFF BOTH WAYS — the LLM's
    confabulation is caught mechanically at the door;
  * the NON-DERIVABLE fields (seat, answers_demand, rationale) are REQUIRED
    — a candidate without intent is inadmissible, because capturing the
    LLM's global thinking as graph is the point;
  * an admitted candidate becomes a content-addressed GENOME (a delta
    adding the function to the code substrate), COLD by construction —
    population evaluation and the handler seat decide its life;
  * the envelope itself is recorded verbatim in the store (kind:
    candidate_envelope) — the intent survives the chat context.

Stdlib + lfpoop.{blocks, gp, deltas, codething}.
"""
import ast
import builtins
import textwrap

from . import blocks as B
from . import deltas as DL
from . import gp as GP

_REQUIRED = ("source", "seat", "answers_demand", "rationale")
_BUILTINS = set(dir(builtins))


class EnvelopeRefusal(ValueError):
    """An inadmissible candidate — carries the named reason/diff."""


def derive(source):
    """The AST-exact truth about the candidate: its free external READS
    (names loaded that are neither params, locals, nor builtins) and its
    WRITES (the name it defines). Also blockifies (v0 refusals propagate)."""
    blocks, meta = B.blockify_source(source)
    tree = ast.parse(textwrap.dedent(source))
    fdef = tree.body[0]
    loads, stores = set(), set(meta["params"])
    for n in ast.walk(fdef):
        if isinstance(n, ast.Name):
            if isinstance(n.ctx, ast.Load):
                loads.add(n.id)
            elif isinstance(n.ctx, ast.Store):
                stores.add(n.id)
    reads = sorted(loads - stores - _BUILTINS)
    return {"reads": reads, "writes": [meta["name"]],
            "blocks": blocks, "meta": meta}


def _ring_mass(reads, known_rings):
    """How much of the candidate's reads each known ring holds."""
    return {ring: len(set(reads) & set(members))
            for ring, members in known_rings.items()}


def intake(candidate, known_rings=None, store=None):
    """The door. Returns (genome, record) or raises EnvelopeRefusal naming
    exactly what was wrong. Nothing about the claim is trusted; everything
    checkable is checked."""
    missing = [f for f in _REQUIRED if not candidate.get(f)]
    if missing:
        raise EnvelopeRefusal(
            f"candidate missing required intent fields {missing} — a "
            f"candidate without seat/demand/rationale is inadmissible")
    truth = derive(candidate["source"])
    declares = candidate.get("declares", {})

    # declared vs derived — exact, both directions, named.
    for field in ("reads", "writes"):
        declared = set(declares.get(field, []))
        derived = set(truth[field])
        if declared != derived:
            raise EnvelopeRefusal(
                f"declared {field} do not match the code: "
                f"undeclared {sorted(derived - declared)}, "
                f"overclaimed {sorted(declared - derived)} — "
                f"the envelope is a claim and the claim is false")

    # placement hypothesis vs wiring mass (when a learned structure exists).
    ring = declares.get("ring")
    if ring and known_rings:
        if ring not in known_rings:
            raise EnvelopeRefusal(f"declared ring {ring!r} does not exist "
                                  f"in the known structure")
        mass = _ring_mass(truth["reads"], known_rings)
        best = max(sorted(mass), key=lambda r: mass[r])
        if mass[best] > mass.get(ring, 0):
            raise EnvelopeRefusal(
                f"declared ring {ring!r} holds {mass.get(ring, 0)} of the "
                f"candidate's reads but ring {best!r} holds {mass[best]} — "
                f"the wiring does not support the placement claim")

    name = truth["meta"]["name"]
    genome = GP.genome(
        [DL.delta("add", ("functions", name),
                  {"source": candidate["source"]})],
        candidate["seat"], reads=candidate["answers_demand"])
    record = {"kind": "candidate_envelope", "name": genome["id"],
              "genome_id": genome["id"], "function": name,
              "seat": candidate["seat"],
              "answers_demand": candidate["answers_demand"],
              "rationale": candidate["rationale"],
              "declares": declares,
              "derived": {"reads": truth["reads"],
                          "writes": truth["writes"],
                          "n_blocks": len(truth["blocks"])},
              "predicted_fitness_direction":
                  candidate.get("predicted_fitness_direction"),
              "implements": candidate.get("implements", [])}
    if store is not None:
        store.append(record)
    return genome, record
