"""The Prolog projection — the SAME ontology, referable from Prolog.

render() PROJECTS ontology.py's literals into lfpoop.pl (facts + the closure
predicates); parse(text) reads the facts back into the identical Python
structures. The roundtrip test (parse(render()) == the source lists) is what
"refer to this as data in both Python and Prolog" cashes out to: one source,
two substrates, provably the same data. Stdlib only; no swipl needed to
render or parse (running the .pl needs any Prolog, optionally)."""
import os
import re

from . import ontology as O

PL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lfpoop.pl")

RULES = """
% ── The one question, computed ──────────────────────────────────────────
% next_level(?L1, ?L2): L2 is the rung above L1.
next_level(L1, L2) :- ladder(I1, L1), I2 is I1 + 1, ladder(I2, L2).

% admissible_transition(?L1, ?L2): the no-skip law.
admissible_transition(L1, L2) :- next_level(L1, L2).

% golden(+Witnessed): every cooling step is witnessed.
golden(Witnessed) :-
    forall(cooling_step(_, S), memberchk(S, Witnessed)).

% next_admissible_closure(+Level, +Witnessed, -closure(Next, Missing)):
% the Manual's one question, answered as a term.
next_admissible_closure(Level, Witnessed, closure(Next, Missing)) :-
    ( next_level(Level, Next) -> true ; Next = none ),
    findall(S, (cooling_step(_, S), \\+ memberchk(S, Witnessed)), Missing).

% is_agent(+Rites): all six rites received.
is_agent(Rites) :- forall(agent_rite(_, R), memberchk(R, Rites)).

% loop_fires(+Verb, +Effect): conditional verbs fire only on witnessed effect.
loop_fires(V, _) :- loop_verb(_, V), \\+ conditional_verb(V).
loop_fires(V, true) :- conditional_verb(V).

% ── The domain: fixpoint + Scott order (same schedule as domain.py) ─────
% A state is state(LevelIndex, WitnessedSorted, RitesSorted).
ladder_top(T) :- findall(I, ladder(I, _), Is), max_list(Is, T).
all_cooling(W) :- findall(S, cooling_step(_, S), L), msort(L, W).
all_rites(R) :- findall(S, agent_rite(_, S), L), msort(L, R).
bottom_state(state(0, [], [])).
top_state(state(T, W, R)) :- ladder_top(T), all_cooling(W), all_rites(R).

subset_of([], _).
subset_of([X|Xs], Ys) :- memberchk(X, Ys), subset_of(Xs, Ys).

% state_leq: the information order (product of chain x powerset x powerset).
state_leq(state(L1,W1,R1), state(L2,W2,R2)) :-
    L1 =< L2, subset_of(W1, W2), subset_of(R1, R2).

% closure_step: F — cooling (Manual order) -> rites -> next rung -> fixpoint.
closure_step(state(L,W,R), state(L,W2,R)) :-
    cooling_step(_, S), \\+ memberchk(S, W), !, msort([S|W], W2).
closure_step(state(L,W,R), state(L,W,R2)) :-
    agent_rite(_, S), \\+ memberchk(S, R), !, msort([S|R], R2).
closure_step(state(L,W,R), state(L2,W,R)) :-
    ladder_top(T), L < T, !, L2 is L + 1.
closure_step(S, S).

% kleene: the chain from S to the least fixpoint above S.
kleene(S, [S]) :- closure_step(S, S2), S2 == S, !.
kleene(S, [S|Chain]) :- closure_step(S, S2), kleene(S2, Chain).
"""


def _facts(name, items):
    return "\n".join(f"{name}({i}, {v})." for i, v in enumerate(items))


def render() -> str:
    parts = [
        "% lfpoop.pl — GENERATED from lfpoop/ontology.py. DO NOT HAND-EDIT.",
        "% The LFPOOP Manual as Prolog data; same source as the Python side.",
        ":- module(lfpoop, [ladder/2, architecture_stage/2, cooling_step/2,",
        "                   loop_verb/2, conditional_verb/1, pipeline_stage/2,",
        "                   agent_rite/2, node_field/2, the_question/1,",
        "                   next_level/2, admissible_transition/2, golden/1,",
        "                   next_admissible_closure/3, is_agent/1, loop_fires/2,",
        "                   state_leq/2, closure_step/2, kleene/2,",
        "                   bottom_state/1, top_state/1]).",
        "",
        f"the_question('{O.THE_QUESTION}').",
        "",
        _facts("ladder", O.LADDER), "",
        _facts("architecture_stage", O.ARCHITECTURE), "",
        _facts("cooling_step", O.COOLING), "",
        _facts("loop_verb", O.LOOP), "",
        "\n".join(f"conditional_verb({v})." for v in O.CONDITIONAL_VERBS), "",
        _facts("pipeline_stage", O.PIPELINE), "",
        _facts("agent_rite", O.AGENT_RITES), "",
        _facts("node_field", O.NODE_FIELDS), "",
        RULES,
    ]
    return "\n".join(parts)


_FACT = re.compile(r"^(\w+)\((?:(\d+),\s*)?([a-z_]+)\)\.$")


def parse(text: str) -> dict:
    """Read the facts back: {predicate: [atoms in index order]}."""
    out = {}
    for line in text.split("\n"):
        m = _FACT.match(line.strip())
        if not m:
            continue
        pred, idx, atom = m.group(1), m.group(2), m.group(3)
        out.setdefault(pred, []).append((int(idx) if idx else 0, atom))
    return {p: [a for _, a in sorted(v)] for p, v in out.items()}


def write(path: str = PL_PATH) -> str:
    with open(path, "w") as f:
        f.write(render())
    return path
