"""apionize — THE API→ONION COMPILER.

INPUT: an API — an array of callables.
OUTPUT: the entire onion API of it — generated, curried, gated.

The mechanism (nothing hand-written per API, ever):

  1. INTROSPECT every callable's real signature (inspect.signature).
  2. FACTOR THE CURRY — two modes, honestly split:
     * HEURISTIC (default): a parameter recurring across callables is a
       CANDIDATE config slot. This is a proposal, not truth — an API of
       send-variants shares to_email/subject/body, which are per-call DATA
       (found live on jwout, 2026-07-26). Signatures cannot decide
       "invariant across calls"; that is semantics.
     * AUTHORITATIVE (config_mask): the API's DECLARED config contract —
       for a real client API this is a READING of its config schema (e.g.
       jwout's mask comes from client.json's own keys: from_name,
       reply_to, ...), governor-reviewable like the capability map.
     Either way: config params become bind-once SLOTS; the rest stays the
     per-call residue of each verb.
  3. GENERATE one slotted VerbSpec per callable: its body fills the curried
     parameters from the bound slots (self.<slot>), lets explicit call-time
     kwargs override, and invokes the REAL underlying callable.
  4. ASSEMBLE through onion2 (create_model + add_method + the alphabet/leak
     gate) — so the product is an ordinary onion: verbs are SOUP until the
     substitution LFP closes (SoupError names the unbound slots), bind() is
     monotone, heat() is the free-slot count, morph()/to_data() work, and
     kleene_climb-at-method-grain (soup()) answers "what is this API still
     missing" BY NAME.

So: hand it Instantly's client, jwout's verbs, any array of callables — the
compiler emits the organ. Binding the credentials IS activating the API;
until compliance/config slots bind, the send verb does not conduct. This is
the piece the DTO's motor_connector should carry (an onionized organ, not a
name) — the brain re-entry rides on this module.

Requires the onion2 extra (pydantic). VAR_POSITIONAL/VAR_KEYWORD params are
ignored for factoring (they are pass-through by construction).
"""
import inspect

from . import onion2 as O2


def analyze(callables, config_mask=None, min_shared=2):
    """The factoring pass: (config_slots, per-callable param report)."""
    sigs = {}
    for fn in callables:
        params = [p for p in inspect.signature(fn).parameters.values()
                  if p.kind not in (inspect.Parameter.VAR_POSITIONAL,
                                    inspect.Parameter.VAR_KEYWORD)]
        sigs[fn.__name__] = params
    if config_mask is not None:
        config = set(config_mask)
    else:
        counts = {}
        for params in sigs.values():
            for p in params:
                counts[p.name] = counts.get(p.name, 0) + 1
        config = {n for n, c in counts.items() if c >= min_shared}
    report = {}
    for name, params in sigs.items():
        report[name] = {
            "curried": sorted(p.name for p in params if p.name in config),
            "call_args": [p.name for p in params if p.name not in config],
            "required_call_args": [
                p.name for p in params
                if p.name not in config and p.default is inspect.Parameter.empty],
        }
    return sorted(config), report


def apionize(name, callables, config_mask=None, min_shared=2):
    """Compile the array of callables into the assembled onion instance.

    Returns (instance, report):
      instance — an onion2 assembly: one verb per callable, curried params
                 as slots; soup()/heat()/bind()/to_data() all apply.
      report   — {"config_slots": [...], "verbs": {name: {curried,
                 call_args, required_call_args}}}.
    """
    config_slots, verb_report = analyze(callables, config_mask, min_shared)
    impls = {fn.__name__: fn for fn in callables}
    verbs = []
    for fn in callables:
        n = fn.__name__
        curried = verb_report[n]["curried"]
        fill = "".join(f"kw.setdefault('{p}', self.{p})\n"
                       for p in curried)
        source = ("kw = dict(kwargs)\n" + fill
                  + f"return _IMPLS['{n}'](*args, **kw)")
        verbs.append(O2.VerbSpec(name=n, source=source, slots=curried))
    ring = O2.RingSpec(name=f"api_{name}",
                       adds=[fn.__name__ for fn in callables],
                       requires=[], verbs=verbs)
    inst = O2.assemble(name, [ring], verb_globals={"_IMPLS": impls})
    return inst, {"config_slots": config_slots, "verbs": verb_report}
