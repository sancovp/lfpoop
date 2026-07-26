"""LFPOOP ontology — the Manual AS DATA. Stdlib only. Imports nothing external.

Every list here is the Manual's own text, verbatim order, snake_cased. This
module is the single source of truth; prolog.py PROJECTS it to lfpoop.pl so
the identical ontology is referable from Prolog. The node/closure semantics
implemented: the one question (next_admissible_closure), the no-skip law
(admissible transition = exactly the next rung), goldenization (hot until
every cooling step is witnessed), append-only provenance, agentification
(the six rites), and the compiler loop's verb order with its
witnessed_effect conditional.
"""
from dataclasses import dataclass, field

THE_QUESTION = "what is my next admissible closure?"

# Realization Ladder — realization levels of one identity.
LADDER = [
    "function", "program", "graph_entity", "skill", "manual", "agent",
    "application", "distribution", "golden_artifact", "compiler_improvement",
]

# Architecture chain.
ARCHITECTURE = [
    "code_thing", "graph_mirror_entity", "runtime_object", "actor",
    "network", "compiler", "meta_compiler", "repository_ecology",
]

# Goldenization — every artifact begins HOT; cooled through these, in order.
COOLING = [
    "execution", "testing", "relational_validation", "observation",
    "independent_witnessing", "provenance", "append_only_crystallization",
]

# Compiler Loop — verb order; goldenize/improve_compiler fire only on
# witnessed_effect (the conditional is data too: see CONDITIONAL_VERBS).
LOOP = [
    "observe", "classify", "infer_next_closures", "materialize", "execute",
    "test", "graph", "quarantine", "witnessed_effect", "goldenize",
    "improve_compiler",
]
CONDITIONAL_VERBS = ["goldenize", "improve_compiler"]  # gated on witnessed_effect

# Conversation Pipeline.
PIPELINE = [
    "conversation", "claim", "skill", "manual", "agent",
    "terminal_application", "web_application", "desktop_application",
    "wearable_runtime", "observation", "provenance", "crystallization",
    "goldenization", "compiler_update",
]

# Agentification — the six rites; an executable object that has received all
# six IS an agent.
AGENT_RITES = [
    "explanation", "evolution", "testing", "export", "review", "graph_identity",
]

# Repository Organization — what each node stores.
NODE_FIELDS = [
    "provenance", "realization_level", "graph_identity", "adapters",
    "generated_documentation", "generated_agents", "generated_packages",
    "tests", "golden_history",
]


def next_level(level: str):
    """The rung above, or None at the top."""
    i = LADDER.index(level)
    return LADDER[i + 1] if i + 1 < len(LADDER) else None


def admissible_transition(from_level: str, to_level: str) -> bool:
    """The no-skip law: the only admissible move is the next rung."""
    return next_level(from_level) == to_level


@dataclass
class Node:
    """One identity climbing the ladder. Provenance is append-only: entries
    can be added, never removed or rewritten (the list is private; read via
    the provenance property, which returns a copy)."""

    name: str
    realization_level: str = "function"
    graph_identity: str = ""
    adapters: list = field(default_factory=list)
    generated_documentation: list = field(default_factory=list)
    generated_agents: list = field(default_factory=list)
    generated_packages: list = field(default_factory=list)
    tests: list = field(default_factory=list)
    golden_history: list = field(default_factory=list)
    _provenance: list = field(default_factory=list, repr=False)
    _witnessed: dict = field(default_factory=dict, repr=False)  # cooling step -> witness
    _rites: dict = field(default_factory=dict, repr=False)      # rite -> witness

    @property
    def provenance(self):
        return list(self._provenance)

    def _record(self, entry: str):
        self._provenance.append(entry)

    # ── goldenization ──
    @property
    def heat(self) -> float:
        """1.0 = fully hot (nothing witnessed), 0.0 = fully cooled."""
        return 1.0 - len(self._witnessed) / len(COOLING)

    @property
    def golden(self) -> bool:
        return all(step in self._witnessed for step in COOLING)

    def cool(self, step: str, witness: str):
        if step not in COOLING:
            raise ValueError(f"not a cooling step: {step}")
        if not witness:
            raise ValueError("cooling requires a witness")
        self._witnessed[step] = witness
        self._record(f"cooled:{step}:by:{witness}")
        if self.golden:
            self.golden_history.append(dict(self._witnessed))
            self._record("crystallized:append_only")

    # ── the one question ──
    def next_admissible_closure(self) -> dict:
        """Every object asks exactly one question. The answer, as data."""
        return {
            "question": THE_QUESTION,
            "level": self.realization_level,
            "next_level": next_level(self.realization_level),
            "unwitnessed_cooling": [s for s in COOLING if s not in self._witnessed],
            "missing_rites": [r for r in AGENT_RITES if r not in self._rites],
            "golden": self.golden,
        }

    def advance(self, witness: str):
        """Move exactly one rung (the no-skip law), witnessed."""
        nxt = next_level(self.realization_level)
        if nxt is None:
            raise ValueError("already at the top of the ladder")
        if not witness:
            raise ValueError("a transition requires a witness")
        self._record(f"transition:{self.realization_level}->{nxt}:by:{witness}")
        self.realization_level = nxt
        return nxt

    # ── agentification ──
    def receive_rite(self, rite: str, witness: str):
        if rite not in AGENT_RITES:
            raise ValueError(f"not a rite: {rite}")
        self._rites[rite] = witness
        self._record(f"rite:{rite}:by:{witness}")

    @property
    def is_agent(self) -> bool:
        return all(r in self._rites for r in AGENT_RITES)


def run_loop(compiler, cycles: int = 1):
    """The Compiler Loop as a driver: calls each verb in the Manual's order;
    goldenize/improve_compiler fire only when witnessed_effect() returned
    truthy. Returns the trace as data: [(verb, fired, result), ...]."""
    trace = []
    for _ in range(cycles):
        effect = False
        for verb in LOOP:
            fn = getattr(compiler, verb, None)
            if verb in CONDITIONAL_VERBS and not effect:
                trace.append((verb, False, None))
                continue
            result = fn() if callable(fn) else None
            if verb == "witnessed_effect":
                effect = bool(result)
            trace.append((verb, True, result))
    return trace
