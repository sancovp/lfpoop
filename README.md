# LFPOOP — Least-Fixed-Point Object-Oriented Programming

The [LFPOOP Manual](MANUAL.md) as **data**, in both Python and Prolog, plus the
machinery it describes — standalone, stdlib-only (one dep:
[uco](https://github.com/sancovp/universal-chain-ontology)).

Every object answers one question: **"what is my next admissible closure?"**

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

`.lfpoop/store.jsonl` is the SDK's own crystallized provenance: it currently
models itself at **distance 7** from its own fixpoint, every step from a real
artifact or a recorded external witness.

## Run the tests

```bash
python3 tests/test_lfpoop.py         # the Manual-as-data + Prolog roundtrip
python3 tests/test_domain_chains.py  # the Scott domain + UCO retrofit
python3 tests/test_full.py           # onion + compiler + gauge/handler + 15→9→7
```

MIT.
