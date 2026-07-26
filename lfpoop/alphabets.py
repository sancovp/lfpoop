"""alphabets — the curry DECIDER (feeds class-ification): name → alphabet → action.

NB renamed from classify.py 2026-07-26: Isaac's "classify" means CLASS-IFY —
turn the curried function into a CLASS (lfpoop/classify.py, the real ②).
This module only DECIDES what curries; the transformer lives next door.

Every free name of a candidate/function/block falls into exactly one
ALPHABET, and the alphabet decides what the compiler DOES with it — this is
"classifies a certain way" made mechanical, and it is the one law
("code only for external effects; everything else is instruction") applied
at name grain:

  chain            bound by the dataflow (params / prior writes) — already
                   curried by blockify; not a global concern.
  ring:<r>         a member of a KNOWN ring (the learned roll-up) — the
                   name couples the code to that ring; placement follows
                   the mass of these.
  config           a known config slot (an apionize-style curried
                   alphabet) — CURRIES OUT into a bind-once slot.
  ambient:pure     stdlib computation (math, json, re, ...) — stays
                   ambient; imposes nothing.
  ambient:effect   the world (os, sys, subprocess, open, exec, ...) — the
                   ONE-LAW marker: anything touching these is CODE-side,
                   never instruction; effects localize to the blocks that
                   carry them.
  demand           resolvable nowhere — a GROWTH CONE: the name of what
                   must arrive before this code can close.

verdict(function) from its alphabet mix:  effectful ≻ open ≻
config_dependent ≻ ring_coupled ≻ pure  (first that applies).

curry_plan(source, context) — THE DRIVER: for each free name, the action:
  config → curry_to_slot · ring:<r> → bind_ring · ambient:pure → leave ·
  ambient:effect → isolate_effect · demand → demand. The plan is what
  apionize did for shared params, generalized to every free name by
  classification instead of frequency.

classify_blocks(source) localizes effects at BLOCK grain: each block's
global frees classified separately, so ONE effectful statement marks ONE
block, not the whole function — the split the one law needs.

The taxonomies (PURE_AMBIENT / EFFECT_AMBIENT / EFFECT_CALLS) are DATA —
a v0 curation, governor-extensible, honestly incomplete rather than
silently wrong. Stdlib + lfpoop.blocks.
"""
import ast
import builtins
import textwrap

from . import blocks as B

_BUILTINS = set(dir(builtins))

PURE_AMBIENT = {
    "math", "json", "re", "itertools", "functools", "textwrap", "hashlib",
    "ast", "inspect", "random", "string", "collections", "typing",
    "dataclasses", "copy", "enum", "decimal", "fractions", "statistics",
}
EFFECT_AMBIENT = {
    "os", "sys", "subprocess", "socket", "urllib", "http", "shutil",
    "sqlite3", "tempfile", "pathlib", "io", "threading", "signal", "time",
}
EFFECT_CALLS = {"open", "exec", "eval", "print", "input", "__import__"}


def _free_and_calls(source):
    tree = ast.parse(textwrap.dedent(source))
    fdef = tree.body[0]
    params = {a.arg for a in fdef.args.args}
    loads, stores, calls = set(), set(params), set()
    for n in ast.walk(fdef):
        if isinstance(n, ast.Name):
            (loads if isinstance(n.ctx, ast.Load) else stores).add(n.id)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            calls.add(n.func.id)
    free = sorted((loads - stores) - (_BUILTINS - EFFECT_CALLS))
    return free, calls, fdef, sorted(params)


def classify_name(name, context):
    """One free name → its alphabet."""
    context = context or {}
    for ring, members in (context.get("rings") or {}).items():
        if name in members:
            return f"ring:{ring}"
    if name in (context.get("config_slots") or ()):
        return "config"
    if name in EFFECT_AMBIENT or name in EFFECT_CALLS:
        return "ambient:effect"
    if name in PURE_AMBIENT:
        return "ambient:pure"
    if name in (context.get("known") or ()):
        return "known"
    return "demand"


def classify_source(source, context=None):
    """The function's alphabet map + verdict + placement."""
    free, calls, fdef, params = _free_and_calls(source)
    alphabet = {n: classify_name(n, context) for n in free}
    # a PARAM that names a known config slot IS the curried alphabet
    # showing up in the signature (apionize's case) — classify it too
    for pname in params:
        if pname in ((context or {}).get("config_slots") or ()):
            alphabet[pname] = "config"
    effectful = (any(c == "ambient:effect" for c in alphabet.values())
                 or bool(calls & EFFECT_CALLS))
    mass = {}
    for n, c in alphabet.items():
        if c.startswith("ring:"):
            mass[c[5:]] = mass.get(c[5:], 0) + 1
    placement = (max(sorted(mass), key=lambda r: mass[r])
                 if mass else None)
    if effectful:
        verdict = "effectful"
    elif any(c == "demand" for c in alphabet.values()):
        verdict = "open"
    elif any(c == "config" for c in alphabet.values()):
        verdict = "config_dependent"
    elif placement:
        verdict = f"ring_coupled:{placement}"
    else:
        verdict = "pure"
    return {"name": fdef.name, "alphabet": alphabet, "verdict": verdict,
            "placement": placement,
            "effect_calls": sorted(calls & EFFECT_CALLS)}


_ACTION = {"config": "curry_to_slot", "ambient:pure": "leave",
           "ambient:effect": "isolate_effect", "demand": "demand",
           "known": "leave"}


def curry_plan(source, context=None):
    """THE DRIVER: per free name, what the compiler does with it."""
    c = classify_source(source, context)
    plan = {}
    for n, alpha in c["alphabet"].items():
        plan[n] = (f"bind_ring:{alpha[5:]}" if alpha.startswith("ring:")
                   else _ACTION[alpha])
    return {"plan": plan, "verdict": c["verdict"],
            "placement": c["placement"],
            "slots": sorted(n for n, a in plan.items()
                            if a == "curry_to_slot"),
            "demands": sorted(n for n, a in plan.items()
                              if a == "demand")}


def classify_blocks(source, context=None):
    """Effect LOCALIZATION at block grain: each block's own global frees
    classified — one effectful statement marks one block, not the whole
    function."""
    blocks, meta = B.blockify_source(source)
    chainbound = set(meta["params"])
    out = []
    for b in blocks:
        node = ast.parse(b["source"]).body[0]
        loads = {n.id for n in ast.walk(node)
                 if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        calls = {n.func.id for n in ast.walk(node)
                 if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name)}
        glob = sorted((loads - chainbound - set(b["writes"]))
                      - (_BUILTINS - EFFECT_CALLS))
        alphabet = {n: classify_name(n, context) for n in glob}
        effectful = (any(c == "ambient:effect" for c in alphabet.values())
                     or bool(calls & EFFECT_CALLS))
        out.append({**b, "global_frees": alphabet,
                    "effect": effectful})
        chainbound |= set(b["writes"])
    return out
