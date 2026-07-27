"""blocks — THE FIRST STEP: code in → logic-block data → LFPOOPy code out.

The object Isaac kept naming and this SDK kept skipping: a transformer that
takes OTHER CODE IN and gives CODE OUT, where the out-code is entirely
composed of LOGIC BLOCKS, progressively functionalized, curried, and rolled
up into an onion of classes BASE→META→SUPER, chained. Everything else in
LFPOOP (GP over code, the onion runtime, the compiler loop) stands ON this:
genetic programming without homoiconic data about the code is not genetic
programming.

The pipeline:

  blockify(fn)      every top-level statement of the function body becomes a
                    LOGIC BLOCK *thing*: {kind, reads, writes, source,
                    lineno} — reads = the free names the block consumes,
                    writes = the names it binds (AST-derived, both exact).
                    Control statements (if/for/while) are single compound
                    blocks; a `return` anywhere inside is honored via the
                    early-return protocol below. HOMOICONIC: blocks are
                    plain data (to_data/from_data) and regenerate source.

  functionalize     each block becomes a FUNCTION of exactly its reads,
                    returning exactly its writes — "bind all the way to a
                    function" applied at statement grain. A block that hits
                    an original `return` returns that value directly; a
                    block that runs off its end returns the sentinel pair
                    ('__w__', (<writes>)). This is the progressive
                    functionalization; the currying is that each block's
                    free variables became its parameters.

  classify          the v0 classification (syntactic, honestly labeled):
                    binding (Assign/AugAssign/AnnAssign) · control
                    (If/For/While) · return (Return) · effect_or_compute
                    (Expr containing a Call) · other.

  emit(fn)          CODE OUT — real Python source with three floors:
                      BASE   the block functions (one def per logic block)
                      META   the chain: the original signature re-entered,
                             dataflow-threaded through the base blocks
                             (each call feeds the next block's reads from
                             the accumulated environment — the composition
                             IS the currying closed over the chain)
                      SUPER  the onion class: base ring dict + the chained
                             meta verb bound as the method
                    compile_fn() executes the emitted source and returns
                    the rebuilt callable — the SHADOW LAW: it must behave
                    identically to the original (tested on real functions,
                    exact equality over probe sweeps).

  GP re-grounding   the block list IS the genome substrate: mutate a
                    block's source (a delta over block data), re-emit,
                    recompile, measure. Code-as-data all the way down.

v0 scope, stated: top-level statement grain (compound statements are one
block each); module-level globals/builtins resolve through the original
function's __globals__; nested defs/closures/async are out of scope and
refuse loudly. Stdlib only.
"""
import ast
import inspect
import textwrap

_SENTINEL = "'__w__'"


class BlockifyRefusal(ValueError):
    """Code this v0 cannot decompose honestly — named, never mangled."""


def _names(node, ctx):
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ctx):
            out.append(n.id)
    return out


def _kind(stmt):
    if isinstance(stmt, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
        return "binding"
    if isinstance(stmt, (ast.If, ast.For, ast.While)):
        return "control"
    if isinstance(stmt, ast.Return):
        return "return"
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        return "effect_or_compute"
    return "other"


def blockify(fn):
    """The function's body as LOGIC BLOCK data. Returns (blocks, meta):
    meta = {name, params, defaults_src, globals} for re-emission."""
    src = textwrap.dedent(inspect.getsource(fn))
    return blockify_source(src, fn.__globals__)


_OPAQUE_NODES = (ast.AsyncFunctionDef, ast.Lambda, ast.Global,
                 ast.Nonlocal, ast.FunctionDef, ast.ClassDef)


def _needs_opaque(stmt):
    return any(isinstance(n, _OPAQUE_NODES) for n in ast.walk(stmt))


def blockify_source(src, globals_ns=None, opaque=False):
    """blockify from SOURCE TEXT (the candidate-envelope intake path —
    exec'd code has no inspect.getsource). Same contract as blockify.

    opaque=True — THE TOTALITY MODE (the onionize driver's setting): a
    statement the decomposer cannot honestly open (nested def/lambda/
    class/global) becomes ONE SEALED BLOCK (kind='opaque') with derived
    reads/writes but unexpanded interior — the transform stays total and
    the honesty lives in GRANULARITY, recorded on the block. Caveat,
    stated: a sealed closure over a chain variable captures the value at
    its block; the shadow law is the arbiter. opaque=False (default)
    keeps the v0 refusal."""
    src = textwrap.dedent(src)
    tree = ast.parse(src)
    fdef = tree.body[0]
    if not isinstance(fdef, ast.FunctionDef):
        raise BlockifyRefusal("input must be a plain function")
    if not opaque:
        for n in ast.walk(fdef):
            if isinstance(n, _OPAQUE_NODES) and n is not fdef:
                raise BlockifyRefusal(
                    f"v0 refuses nested defs/lambdas/global tricks "
                    f"(line {getattr(n, 'lineno', '?')}) — out of scope, "
                    f"not silently mangled (onionize uses opaque=True)")
    a = fdef.args
    params = ([x.arg for x in getattr(a, "posonlyargs", [])]
              + [x.arg for x in a.args]
              + ([a.vararg.arg] if a.vararg else [])
              + [x.arg for x in a.kwonlyargs]
              + ([a.kwarg.arg] if a.kwarg else []))   # the FULL signature
    body = [s for s in fdef.body
            if not (isinstance(s, ast.Expr)
                    and isinstance(s.value, ast.Constant)
                    and isinstance(s.value.value, str))]   # drop docstring
    blocks, bound = [], set(params)
    for i, stmt in enumerate(body):
        reads = sorted({n for n in _names(stmt, ast.Load)
                        if n in bound})            # free w.r.t. the chain
        writes = {n for n in _names(stmt, ast.Store)}
        # names scoped INSIDE the statement never reach the chain:
        # comprehension targets (py3 comprehensions have their own scope)
        # and `except ... as e` names (deleted at handler exit)
        scoped = set()
        for n in ast.walk(stmt):
            if isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp,
                              ast.GeneratorExp)):
                for gen in n.generators:
                    scoped.update(_names(gen.target, ast.Store))
            if isinstance(n, ast.ExceptHandler) and n.name:
                scoped.add(n.name)
        writes -= scoped
        for n in ast.walk(stmt):                   # defs/classes/imports
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)) \
                    and n is not stmt or (n is stmt and isinstance(
                        n, (ast.FunctionDef, ast.ClassDef))):
                writes.add(n.name)
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                writes.update(a.asname or a.name.split(".")[0]
                              for a in n.names)
        writes = sorted(writes)
        kind = ("opaque" if opaque and _needs_opaque(stmt)
                else _kind(stmt))
        if kind in ("control", "opaque"):
            # a CONDITIONAL write must pass the prior value through when
            # its branch does not fire — so already-bound write targets
            # are also reads (found live: `if k == n: hi = 1.0`)
            reads = sorted(set(reads) | (set(writes) & bound))
        blocks.append({"i": i, "kind": kind,
                       "reads": reads, "writes": writes,
                       "source": ast.unparse(stmt)})
        bound |= set(writes)
    sig = ast.unparse(fdef.args)
    return blocks, {"name": fdef.name, "params": params,
                    "signature": sig, "globals": globals_ns or {}}


def functionalize(block, prefix="block"):
    """One block → one function of exactly its reads (source text). The
    tail returns only the writes ACTUALLY BOUND at runtime (a dict from
    locals()) — a zero-iteration loop target or an unfired conditional
    write simply doesn't come back, exactly like the original scope
    (found live: `for k in path[:-1]` with an empty path)."""
    args = ", ".join(block["reads"])
    body = textwrap.indent(block["source"], "    ")
    tail = (f"    _loc = locals()\n"
            f"    return ({_SENTINEL}, "
            f"{{w: _loc[w] for w in {tuple(block['writes'])!r} "
            f"if w in _loc}})")
    return (f"def {prefix}_{block['i']}({args}):\n{body}\n{tail}\n")


def emit(fn, class_name=None):
    """CODE OUT: the LFPOOPy source — BASE block functions, META chain,
    SUPER onion class. Returns (source_text, meta)."""
    blocks, meta = blockify(fn)
    name = meta["name"]
    class_name = class_name or (name.title().replace("_", "") + "Onion")
    lines = [f"# GENERATED by lfpoop.blocks — LFPOOPy form of {name}",
             f"# BASE: {len(blocks)} logic blocks, functionalized (curried "
             f"over their free reads)"]
    for b in blocks:
        lines.append(functionalize(b, prefix=f"_{name}_blk"))
    lines.append(f"# META: the chain — dataflow-threaded composition")
    lines.append(f"def {name}({meta['signature']}):")
    for p in meta["params"]:
        pass
    for b in blocks:
        args = ", ".join(f"{r}={r}" for r in b["reads"])
        lines.append(f"    _r = _{name}_blk_{b['i']}({args})")
        lines.append(f"    if not (isinstance(_r, tuple) and len(_r) == 2 "
                     f"and _r[0] == {_SENTINEL}):")
        lines.append(f"        return _r        # the block hit an original "
                     f"return")
        for w in b["writes"]:
            lines.append(f"    if '{w}' in _r[1]: {w} = _r[1]['{w}']")
    lines.append("    return None")
    lines.append("")
    lines.append(f"# SUPER: the onion class — base ring + the chained verb")
    lines.append(f"class {class_name}:")
    lines.append(f"    __ring_base__ = " + repr(
        [f"_{name}_blk_{b['i']}" for b in blocks]))
    lines.append(f"    __ring_meta__ = {name!r}")
    lines.append(f"    {name} = staticmethod({name})")
    lines.append("")
    return "\n".join(lines), {**meta, "blocks": blocks,
                              "class_name": class_name}


def compile_fn(source, meta):
    """Execute the emitted source; return (rebuilt_fn, onion_class). The
    original function's module globals resolve free names (math, max...)."""
    ns = dict(meta["globals"])
    exec(source, ns)
    cls = ns[meta["class_name"]]
    return getattr(cls, meta["name"]), cls


def roundtrip(fn, class_name=None):
    """code in → block data → code out → callable. The shadow pair."""
    source, meta = emit(fn, class_name)
    rebuilt, cls = compile_fn(source, meta)
    return rebuilt, source, meta, cls


# ── the GP grounding: mutate BLOCK DATA, re-emit, recompile ─────────────────

def emit_from_blocks(blocks, meta):
    """Re-emit from (possibly mutated) block data — the genome→phenotype
    compile step for CODE genomes."""
    class _Shim:                                   # emit() wants a function;
        pass                                       # feed the data directly
    name = meta["name"]
    class_name = meta.get("class_name",
                          name.title().replace("_", "") + "Onion")
    lines = [f"# GENERATED by lfpoop.blocks (from block data)"]
    for b in blocks:
        lines.append(functionalize(b, prefix=f"_{name}_blk"))
    lines.append(f"def {name}({meta['signature']}):")
    for b in blocks:
        args = ", ".join(f"{r}={r}" for r in b["reads"])
        lines.append(f"    _r = _{name}_blk_{b['i']}({args})")
        lines.append(f"    if not (isinstance(_r, tuple) and len(_r) == 2 "
                     f"and _r[0] == {_SENTINEL}):")
        lines.append(f"        return _r")
        for w in b["writes"]:
            lines.append(f"    if '{w}' in _r[1]: {w} = _r[1]['{w}']")
    lines.append("    return None")
    lines.append(f"class {class_name}:")
    lines.append(f"    {name} = staticmethod({name})")
    src = "\n".join(lines)
    return src, {**meta, "blocks": blocks, "class_name": class_name}
