% lfpoop.pl — GENERATED from lfpoop/ontology.py. DO NOT HAND-EDIT.
% The LFPOOP Manual as Prolog data; same source as the Python side.
:- module(lfpoop, [ladder/2, architecture_stage/2, cooling_step/2,
                   loop_verb/2, conditional_verb/1, pipeline_stage/2,
                   agent_rite/2, node_field/2, the_question/1,
                   next_level/2, admissible_transition/2, golden/1,
                   next_admissible_closure/3, is_agent/1, loop_fires/2,
                   state_leq/2, closure_step/2, kleene/2,
                   bottom_state/1, top_state/1]).

the_question('what is my next admissible closure?').

ladder(0, function).
ladder(1, program).
ladder(2, graph_entity).
ladder(3, skill).
ladder(4, manual).
ladder(5, agent).
ladder(6, application).
ladder(7, distribution).
ladder(8, golden_artifact).
ladder(9, compiler_improvement).

architecture_stage(0, code_thing).
architecture_stage(1, graph_mirror_entity).
architecture_stage(2, runtime_object).
architecture_stage(3, actor).
architecture_stage(4, network).
architecture_stage(5, compiler).
architecture_stage(6, meta_compiler).
architecture_stage(7, repository_ecology).

cooling_step(0, execution).
cooling_step(1, testing).
cooling_step(2, relational_validation).
cooling_step(3, observation).
cooling_step(4, independent_witnessing).
cooling_step(5, provenance).
cooling_step(6, append_only_crystallization).

loop_verb(0, observe).
loop_verb(1, classify).
loop_verb(2, infer_next_closures).
loop_verb(3, materialize).
loop_verb(4, execute).
loop_verb(5, test).
loop_verb(6, graph).
loop_verb(7, quarantine).
loop_verb(8, witnessed_effect).
loop_verb(9, goldenize).
loop_verb(10, improve_compiler).

conditional_verb(goldenize).
conditional_verb(improve_compiler).

pipeline_stage(0, conversation).
pipeline_stage(1, claim).
pipeline_stage(2, skill).
pipeline_stage(3, manual).
pipeline_stage(4, agent).
pipeline_stage(5, terminal_application).
pipeline_stage(6, web_application).
pipeline_stage(7, desktop_application).
pipeline_stage(8, wearable_runtime).
pipeline_stage(9, observation).
pipeline_stage(10, provenance).
pipeline_stage(11, crystallization).
pipeline_stage(12, goldenization).
pipeline_stage(13, compiler_update).

agent_rite(0, explanation).
agent_rite(1, evolution).
agent_rite(2, testing).
agent_rite(3, export).
agent_rite(4, review).
agent_rite(5, graph_identity).

node_field(0, provenance).
node_field(1, realization_level).
node_field(2, graph_identity).
node_field(3, adapters).
node_field(4, generated_documentation).
node_field(5, generated_agents).
node_field(6, generated_packages).
node_field(7, tests).
node_field(8, golden_history).


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
    findall(S, (cooling_step(_, S), \+ memberchk(S, Witnessed)), Missing).

% is_agent(+Rites): all six rites received.
is_agent(Rites) :- forall(agent_rite(_, R), memberchk(R, Rites)).

% loop_fires(+Verb, +Effect): conditional verbs fire only on witnessed effect.
loop_fires(V, _) :- loop_verb(_, V), \+ conditional_verb(V).
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
    cooling_step(_, S), \+ memberchk(S, W), !, msort([S|W], W2).
closure_step(state(L,W,R), state(L,W,R2)) :-
    agent_rite(_, S), \+ memberchk(S, R), !, msort([S|R], R2).
closure_step(state(L,W,R), state(L2,W,R)) :-
    ladder_top(T), L < T, !, L2 is L + 1.
closure_step(S, S).

% kleene: the chain from S to the least fixpoint above S.
kleene(S, [S]) :- closure_step(S, S2), S2 == S, !.
kleene(S, [S|Chain]) :- closure_step(S, S2), kleene(S2, Chain).
