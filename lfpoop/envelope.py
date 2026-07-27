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
    # subtract only builtins the source does NOT itself reference as a
    # global dependency is impossible to know syntactically — but a name
    # that is ALSO stored is a local, not a builtin. We keep builtin names
    # that are LOADED-not-stored out of reads UNLESS flagged: the honest
    # position (v4 verifier MED-3) is that builtin-shadowing globals exist,
    # so we report reads as (loads - stores) and mark which are builtin-
    # named, rather than silently dropping them.
    external = sorted(loads - stores)
    reads = [n for n in external if n not in _BUILTINS]
    builtin_shadowed = [n for n in external if n in _BUILTINS]
    return {"reads": reads, "writes": [meta["name"]],
            "builtin_shadowed": builtin_shadowed,
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

    # declared vs derived — exact, both directions, named. Reads are
    # checked against derived reads PLUS the builtin-shadowed set, so a
    # truthful declaration of a global that shadows a builtin name (id,
    # list, sum, type...) is admitted, not falsely refused (v4 MED-3).
    for field in ("reads", "writes"):
        declared = set(declares.get(field, []))
        derived = set(truth[field])
        allowed_extra = (set(truth.get("builtin_shadowed", []))
                         if field == "reads" else set())
        undeclared = derived - declared
        overclaimed = declared - derived - allowed_extra
        if undeclared or overclaimed:
            raise EnvelopeRefusal(
                f"declared {field} do not match the code: "
                f"undeclared {sorted(undeclared)}, "
                f"overclaimed {sorted(overclaimed)} — "
                f"the envelope is a claim and the claim is false")

    # placement hypothesis vs wiring mass (when a learned structure exists).
    ring = declares.get("ring")
    if ring and known_rings:
        if ring not in known_rings:
            raise EnvelopeRefusal(f"declared ring {ring!r} does not exist "
                                  f"in the known structure")
        mass = _ring_mass(truth["reads"], known_rings)
        claimed = mass.get(ring, 0)
        top = max(mass.values()) if mass else 0
        # support floor: a candidate with reads must have wiring into its
        # declared ring; and the claim holds only if the declared ring is
        # the UNIQUE max — a tie means the wiring does not disambiguate, so
        # it does not go to the claimant (v4 verifier MED-5).
        contenders = sorted(r for r, m in mass.items() if m >= claimed
                            and r != ring)
        if claimed == 0 and truth["reads"]:
            raise EnvelopeRefusal(
                f"declared ring {ring!r} holds NONE of the candidate's "
                f"reads {truth['reads']} — the wiring gives no support for "
                f"the placement claim")
        if claimed < top or contenders:
            raise EnvelopeRefusal(
                f"declared ring {ring!r} holds {claimed} of the candidate's "
                f"reads but ring(s) {contenders or [max(sorted(mass), key=lambda r: mass[r])]} "
                f"hold >= that (the wiring does not uniquely support the "
                f"placement claim)")

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
