# LFPOOP — Least-Fixed-Point Object-Oriented Programming

The [LFPOOP Manual](MANUAL.md) as **data**, in both Python and Prolog, plus the
machinery it describes — standalone, stdlib-only (one dep:
[uco](https://github.com/sancovp/universal-chain-ontology)).

Every object answers one question: **"what is my next admissible closure?"**

## The pipeline: any Python module → its LFPOOPy onion

LFPOOP reads other code and emits its canonical onion form, learns its own
structure, and predicts admissible combinations — the transform is total and
proven by the transformed module's OWN test suite:

```
code IN  →  blocks (statement → logic-block data, functionalized/curried)
         →  classify (curried function → CLASS; alphabets decide the curry)
         →  rollup (which functions/classes group — LEARNED from the wiring)
         →  onionize (the driver: any module → self-contained onion source)
         →  shadow (the module's OWN suite runs green against the onion)
         →  predict (given the pool, enumerate admissible compositions + residues)
CODE OUT ·  and the LLM writes the next candidate through envelope (checked claims)
```

Proven: **8 real lfpoop modules onionized and each passed its own test suite
against the onionized build** (`tests/test_onionize_sweep.py`) — augassign,
classes, nested closures, the Scott domain, the predictor. The driver is
general, not example-specific.

## What's in the box

| module | what it is |
|---|---|
| `lfpoop/ontology.py` | the Manual as Python data: the realization ladder, the 7 cooling steps, the compiler-loop verbs, the 6 agentification rites, `Node`, `next_level`, `admissible_transition` |
| `lfpoop/prolog.py` | the SAME source projected to `lfpoop.pl` (`next_admissible_closure/3`, `golden/1`, `is_agent/1`, `state_leq/2`, `kleene/2`) — roundtrip-tested |
| `lfpoop/domain.py` | the state space as a Scott domain: `leq`, `lub`, a monotone+inflationary `closure_step`, the Kleene chain to ⊤ — and `sdk_state()`, the SDK locating **itself** in its own domain from real artifacts |
| `lfpoop/chains.py` | the compiler loop as a uco `Chain`; executing the chain IS computing the fixpoint (`drive_node`'s state sequence == the Kleene chain, exactly) |
| `lfpoop/onion.py` | onion runtime stacking: `@ring` layers with declared alphabets, `stack()` runtime class synthesis that REFUSES undeclared capability access naming the leak, a curried composer, `to_data`/`stack_from_data` |
| `lfpoop/codething.py` | real artifacts mirrored to Node records (content-hash graph identity), an append-only store, `agentify()` (the six rites, granted only against a node's own artifacts), and `accept_witness` — the handler seat |
| `lfpoop/compiler.py` | the loop verbs for real: quarantined materialize, subprocess test, process-witness, `goldenize` = a 6/7 **gauge** (the 7th cooling step belongs to an external handler — the compiler cannot self-goldenize) |
| `lfpoop/selfapply.py` | the compiler compiling the SDK's own source through its own loop |
| `lfpoop/climb.py` | **`kleene_climb`** — the ONE instruction: locate yourself from real artifacts, answer the one question (next admissible closure + exactly which check it requires), optionally take the step (only the rung is takeable — cooling and rites are derived from artifacts, never fabricated) |
| `lfpoop/onion2.py` | ONION-V2 (optional extra `lfpoop[onion2]`): rings as `RenderablePiece` DATA, classes generated via `create_model` + runtime `add_method` — and the **activation semantics**: a verb is a template with slots; `bind()` is one monotone substitution; the method activates at the LFP of substitutions (`soup()`/`heat()` name what's unbound); `morph()` swaps the config and transports surviving bindings; JSON/XML are thin parsers into the same data |
| `lfpoop/template_mixins.py` | vendored verbatim: the original TemplateAttributeMixin/TemplateMethodMixin kit (runtime method/attribute attachment) |
| `lfpoop/deltas.py` | the treeshell category_theory shape with the laws as TESTS: typed delta ops (override/add/exclude) whose composition is closed + associative (exhaustively verified, refusals agreeing) and satisfies the action law; genes-as-deltas with `crossover` (conflicts surfaced by name, never silently merged); `fork()` with lineage recorded and witness history honestly stripped (non-transferability); a substrate fibration whose preservation check is BEHAVIORAL |
| `lfpoop/blocks.py` | **THE FIRST STEP — code in, LFPOOPy code out**: every logic block of a real function becomes a logic-block THING (kind/reads/writes/source — homoiconic data), each block is functionalized over exactly its free reads (currying at statement grain), the chain recomposes them by dataflow to IDENTICAL behavior (shadow-law tested, early returns included), and the emitted source is BASE (block defs) → META (the chain) → SUPER (the onion class). GP mutates the block data itself and recompiles — genetic programming on code-as-data |
| `lfpoop/rollup.py` | **the roll-up learner (MVP ①)**: which functions roll into which rings is LEARNED, not authored — the AST call graph + real traces of the module's own green suite are the wiring, mechanical Hebbian mutators propose moves/merges, Newman modularity is the fitness, and gp.evolve climbs from ⊥ (every function a singleton) to the learned grouping; `emit_rollup` writes the ring classes out with membership as data, shadow-law identical |
| `lfpoop/predict.py` | **the combination predictor (MVP ③)** — prediction as deduction: `predict(pool)` answers the one question for every unit at once (active / buildable / blocked), keeping the two residue kinds distinct (capability residue = what must ARRIVE; binding residue = what must be BOUND); `closure` = the capability LFP; `derivations`/`residue` enumerate how a target can be made and the minimal named demand set; units normalize from rings, class-ified classes, and bare callables — the ontology is the input |
| `lfpoop/onionize.py` | **THE DRIVER: any Python module in → the LFPOOPy onion out** — every plain function blockified in totality mode (unopenable statements seal as opaque blocks; decorated functions seal whole — granularity recorded, nothing refuses), emitted as BASE blocks + META chains under the original names, verbatim floor order-preserved, the learned roll-up appended as ring classes + the module onion; `shadow_module` = the module-grain shadow law: the module's OWN test suite runs against the onionized build in a subprocess — the claim is exactly as true as that gate is green. Classes open at METHOD grain (plain methods fine-grain, decorated/capture-risk sealed); verified on lfpoop.deltas AND lfpoop.gp (Evaluator/Registry classes) against their own suites |
| `lfpoop/classify.py` | **CLASS-IFY (the real ②): a curried function BECOMES a class** — construction binds the curried alphabet (monotone, soup-named, heat-counted), the call applies the residue; emitted as standalone source (code out) carrying `__curried__`/`__residue__` as data; `class_ify_group` = one shared alphabet, many residue methods (apionize as code out) |
| `lfpoop/alphabets.py` | the curry DECIDER feeding class-ification: every free name → one alphabet (chain / ring / config / ambient:pure / ambient:effect / demand); `curry_plan` issues per-name actions; effects localized to the single block that carries them (the one law at name grain) |
| `lfpoop/envelope.py` | **the candidate envelope — LLM code as checked claims**: candidates arrive as `{source, seat, answers_demand, rationale, declares{reads,writes,ring}}`; everything derivable is cross-checked against the AST and the learned wiring (confabulated declares and unsupported placement claims are refused naming the exact diff, both directions); intent is required and recorded verbatim (the LLM's global thinking becomes graph); admitted candidates are cold, content-addressed genomes |
| `lfpoop/apionize.py` | **the API→onion compiler**: an array of callables in, the entire curried onion API out — signatures introspected, the config alphabet factored (heuristic candidates or an authoritative declared mask), one slotted verb generated per callable invoking the real implementation; the product is an ordinary onion (soup names the missing credentials; binding them IS activating the API) |
| `lfpoop/gp.py` | genetic programming as a suite: content-addressed delta-program genomes with pedigree, a SEALED evaluator (mutators receive the train view only — the Goodhart guard is the API), fitness vectors with Wilson intervals (±1-of-58 is visibly noise), pluggable selection (hillclimb/tournament/μ+λ/Pareto), `evolve()` with dedup + bestiary + budget, and promotion through the handler seat — the loop cannot crown its own output |
| `lfpoop/owl.py` | **everything recursively renders its own ontology**: the ladder as a DL subsumption chain (leq IS ⊑), golden/is_agent as DEFINED classes (a reasoner's job), States/Nodes/stores as individuals, rings as restricted classes — `render_owl()` stamped on every class, composites render by composing their parts' renders, `rings_from_owl` closes the loop the other way, `render_sdk_owl()` emits the whole SDK as ONE ontology |

`.lfpoop/store.jsonl` is the SDK's own crystallized provenance: it currently
models itself at **distance 7** from its own fixpoint, every step from a real
artifact or a recorded external witness.

## Run the tests

```bash
python3 tests/test_lfpoop.py         # the Manual-as-data + Prolog roundtrip
python3 tests/test_domain_chains.py  # the Scott domain + UCO retrofit
python3 tests/test_full.py           # onion + compiler + gauge/handler + 15→9→7
python3 tests/test_onion2_climb.py   # ONION-V2 activation semantics + kleene_climb
python3 tests/test_owl.py            # the recursive self-ontology (owlready2 load iff present)
python3 tests/test_deltas.py         # the delta algebra laws + crossover + fork + fibration
python3 tests/test_gp.py             # the GP suite: genomes/fitness/selection/bestiary/promotion
python3 tests/test_apionize.py       # the API→onion compiler (needs the onion2 extra)
python3 tests/test_blocks.py         # the first step: code→blocks→code, shadow-proven; GP on code-as-data
python3 tests/test_rollup.py         # the roll-up learner: containment structure learned from real wiring
python3 tests/test_envelope.py       # the candidate envelope: LLM code as checked claims
python3 tests/test_classify.py       # CLASS-IFY: curried function → class, shadow-proven
python3 tests/test_alphabets.py      # the curry decider: alphabets drive the actions
python3 tests/test_onionize.py       # THE DRIVER: module → onion, judged by the module's own suite
python3 tests/test_predict.py        # the combination predictor: prediction as deduction
python3 tests/test_onionize_sweep.py # THE CAPSTONE: 8 real modules → onions, each judged by its own suite
```

MIT.
