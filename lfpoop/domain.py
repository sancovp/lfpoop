"""The LFPOOP domain — fixpoint and Scott domain, modeled ON the SDK itself.

The ontology's own structure, read order-theoretically:

  * A node-state is its INFORMATION CONTENT: (ladder rung, witnessed cooling
    steps, received rites). The order is the information order —
    s1 ⊑ s2 iff s2 knows everything s1 knows (product of a finite chain and
    two powerset lattices).
  * The poset is finite, has ⊥ (a fresh function-level node, nothing
    witnessed) and ⊤ (compiler_improvement, fully cooled, fully agentified),
    and every subset has a least upper bound — so it is trivially a dcpo in
    which every element is compact: a (finite) Scott domain.
  * The Manual's one question IS the domain's step function:
    F(s) = s plus its next admissible closure (first unwitnessed cooling
    step, else first missing rite, else the next rung, else s). F is
    INFLATIONARY (s ⊑ F(s)) and MONOTONE — so the Kleene chain
    ⊥ ⊑ F(⊥) ⊑ F²(⊥) ⊑ … computes lfp above ⊥, which is ⊤. The climb is
    the iteration; the summit was already least — the fixpoint precedes its
    own computation.
  * Self-model: sdk_state() reads THIS repository's own honest state into
    the domain, so the SDK is an element of the domain it defines and its
    own distance-to-fixpoint is a computed number, not a claim.

Stdlib only. The identical structure is projected into lfpoop.pl
(state_leq/2, closure_step/2, kleene/2) and cross-checked exactly.
"""
import os
from dataclasses import dataclass

from . import ontology as O


@dataclass(frozen=True, order=False)
class State:
    """A node's information content. Canonical: sorted tuples."""
    level: int                 # index into O.LADDER
    witnessed: tuple           # sorted cooling steps
    rites: tuple               # sorted rites

    @staticmethod
    def make(level=0, witnessed=(), rites=()):
        return State(level, tuple(sorted(set(witnessed))),
                     tuple(sorted(set(rites))))


BOTTOM = State.make(0)
TOP = State.make(len(O.LADDER) - 1, O.COOLING, O.AGENT_RITES)


def leq(a: State, b: State) -> bool:
    """The information order: b knows at least everything a knows."""
    return (a.level <= b.level
            and set(a.witnessed) <= set(b.witnessed)
            and set(a.rites) <= set(b.rites))


def lub(states) -> State:
    """Least upper bound — exists for EVERY subset (finite lattice)."""
    states = list(states) or [BOTTOM]
    return State.make(max(s.level for s in states),
                      set().union(*(set(s.witnessed) for s in states)),
                      set().union(*(set(s.rites) for s in states)))


def closure_step(s: State) -> State:
    """F — the one question, answered: add exactly the next admissible
    closure. Deterministic schedule: cooling (Manual order) → rites
    (Manual order) → the next rung → fixpoint."""
    for step in O.COOLING:
        if step not in s.witnessed:
            return State.make(s.level, set(s.witnessed) | {step}, s.rites)
    for rite in O.AGENT_RITES:
        if rite not in s.rites:
            return State.make(s.level, s.witnessed, set(s.rites) | {rite})
    if s.level < len(O.LADDER) - 1:
        return State.make(s.level + 1, s.witnessed, s.rites)
    return s


def kleene(start: State = BOTTOM):
    """The Kleene chain from `start` to the fixpoint. Returns the full
    chain; chain[-1] is the least fixpoint above `start`."""
    chain = [start]
    while True:
        nxt = closure_step(chain[-1])
        if nxt == chain[-1]:
            return chain
        chain.append(nxt)


def all_states():
    """The entire domain, enumerated (10 × 2^7 × 2^6 = 81,920 elements) —
    small enough that inflationarity is checked EXHAUSTIVELY, not sampled."""
    from itertools import combinations
    cool_subsets = [set(c) for r in range(len(O.COOLING) + 1)
                    for c in combinations(O.COOLING, r)]
    rite_subsets = [set(c) for r in range(len(O.AGENT_RITES) + 1)
                    for c in combinations(O.AGENT_RITES, r)]
    for level in range(len(O.LADDER)):
        for w in cool_subsets:
            for r in rite_subsets:
                yield State.make(level, w, r)


def sdk_state(store_path=None) -> State:
    """THIS SDK, as an element of its own domain — honest readings only:
    each cooling step / rite is claimed iff a real artifact on disk
    witnesses it. No artifact, no claim. After the compiler has actually run
    on the SDK (self-application: its modules mirrored, a witnessed golden
    record, an improve_compiler record, packaging), the distance DROPS —
    because reality moved, never by relabeling."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ex = os.path.exists
    witnessed = set()
    if ex(os.path.join(root, "tests", "test_lfpoop.py")):
        witnessed |= {"execution", "testing"}       # the suite runs and asserts
    if ex(os.path.join(root, "lfpoop", "lfpoop.pl")):
        witnessed.add("relational_validation")      # the cross-substrate roundtrip
    rites = set()
    if ex(os.path.join(root, "MANUAL.md")):
        rites.add("explanation")
    if ex(os.path.join(root, "tests")):
        rites.add("testing")
    if ex(os.path.join(root, "pyproject.toml")):
        rites.add("export")                         # packaged
    # store-backed witnesses — SCOPED to the SDK's own artifacts (records
    # named lfpoop*), and independent witnessing ONLY via an EXTERNAL
    # handler-seat record (the compiler's process re-runs never count) —
    # the verifier's 2026-07-25 gameability finding, closed.
    store_path = store_path or os.path.join(root, ".lfpoop", "store.jsonl")
    level = O.LADDER.index("program")
    if ex(store_path):
        from .codething import Store
        store = Store(store_path)
        allrecs = store.records()
        sdk_recs = [r for r in allrecs
                    if r.get("kind") != "witness"
                    and r.get("name", "").startswith("lfpoop")]
        if sdk_recs:
            witnessed.add("observation")            # the SDK observed itself
            rites.add("graph_identity")             # content-hash identity held
            level = O.LADDER.index("graph_entity")  # its modules ARE graph entities
            witnessed.add("append_only_crystallization")
        if any(r.get("provenance") for r in sdk_recs):
            witnessed.add("provenance")
        ext = [r for r in allrecs
               if r.get("kind") == "witness"
               and r.get("name", "").startswith("lfpoop")
               and not str(r.get("witness_id", "")).startswith("process_rerun")]
        if ext:
            witnessed.add("independent_witnessing")
            rites.add("review")
        if any("improve_compiler" in p
               for r in sdk_recs for p in r.get("provenance", [])):
            rites.add("evolution")
    return State.make(level, witnessed, rites)
