"""onionize — THE DRIVER: any Python module in → the LFPOOPy onion out.

Composes the whole pipeline into one call:

  onionize_module_source(src)
      walks the module's top-level statements IN ORDER:
        * a plain FunctionDef → blockified in TOTALITY MODE (statements it
          cannot open become sealed opaque blocks — granularity recorded,
          never refusal), then emitted as BASE block functions + the META
          chain UNDER THE ORIGINAL NAME (so every intra-module reference
          keeps working);
        * a decorated/async function → carried VERBATIM (sealed whole,
          reported coarse);
        * everything else (imports, constants, classes, module-level
          calls) → VERBATIM, in place — order preserved, because module
          semantics ARE their statement order.
      then appends the learned ROLL-UP (rollup.learn over the module's own
      static wiring, seeded/deterministic): one Ring class per learned
      ring, members bound to the RE-EMITTED in-file functions (no facade
      over the original — the output is self-contained), and one module
      onion class carrying the rings as data.

  shadow_module(out_source, fullname, test_path)
      THE MODULE-GRAIN SHADOW LAW: in a SUBPROCESS, install the onionized
      source as the module under its real import name and run the module's
      OWN pre-existing test suite against it. Green = the transform is
      real; anything else names the break. This is the acceptance test of
      the claim "the library automatically transforms modules into
      onions" — the claim is exactly as true as this gate is green.

Every output is deterministic for a given input (seeded learner, no
timestamps). Report says, per function: fine / fine-with-opaque(k) /
sealed(reason). Stdlib + lfpoop.{blocks, rollup}.
"""
import ast
import inspect
import os
import random
import subprocess
import sys
import tempfile
import textwrap

from . import blocks as B
from . import rollup as R

_SENT = B._SENTINEL


def _emit_function(blocks, meta):
    """BASE block defs + the META chain def named as the ORIGINAL."""
    name = meta["name"]
    lines = []
    for b in blocks:
        lines.append(B.functionalize(b, prefix=f"_{name}_blk"))
    lines.append(f"def {name}({meta['signature']}):")
    for b in blocks:
        args = ", ".join(f"{r}={r}" for r in b["reads"])
        lines.append(f"    _r = _{name}_blk_{b['i']}({args})")
        lines.append(f"    if not (isinstance(_r, tuple) and len(_r) == 2 "
                     f"and _r[0] == {_SENT}):")
        lines.append(f"        return _r")
        for w in b["writes"]:
            lines.append(f"    if '{w}' in _r[1]: {w} = _r[1]['{w}']")
    lines.append("    return None")
    lines.append("")
    return "\n".join(lines)


def _emit_method(blocks, meta, cls, mname):
    """Returns (module_level_block_fns, class_body_method). Block fns live
    at MODULE scope (bare-name callable from the method); the method body
    (nested in the class) threads them — self flows as a normal chain var."""
    prefix = f"_{cls}_{mname}_blk"
    base = "".join(B.functionalize(b, prefix=prefix) for b in blocks)
    lines = [f"    def {mname}({meta['signature']}):"]
    for b in blocks:
        args = ", ".join(f"{r}={r}" for r in b["reads"])
        lines.append(f"        _r = {prefix}_{b['i']}({args})")
        lines.append(f"        if not (isinstance(_r, tuple) and "
                     f"len(_r) == 2 and _r[0] == {_SENT}):")
        lines.append(f"            return _r")
        for w in b["writes"]:
            lines.append(f"        if '{w}' in _r[1]: {w} = _r[1]['{w}']")
    lines.append("        return None")
    return base, "\n".join(lines)


def _emit_class(node):
    """A ClassDef opened at fine grain: each plain method blockified
    (opaque mode); decorated/property methods and non-def members kept
    verbatim. Returns (source, report) — the class is a natural ring."""
    cls = node.name
    header = [ast.unparse(d) for d in []]
    deco = "".join(f"@{ast.unparse(d)}\n" for d in node.decorator_list)
    bases = ast.unparse(node).splitlines()[len(node.decorator_list)]
    lines = [deco.rstrip("\n")] if deco else []
    lines.append(bases if bases.endswith(":") else bases)
    report = {"methods_fine": {}, "methods_sealed": {}, "verbatim": 0}
    module_base = []
    body_has = False
    for m in node.body:
        if isinstance(m, ast.FunctionDef) and not m.decorator_list:
            try:
                blocks, meta = B.blockify_source(ast.unparse(m), opaque=True)
            except B.BlockifyRefusal:
                lines.append(textwrap.indent(ast.unparse(m), "    "))
                report["methods_sealed"][m.name] = "blockify refused"
                body_has = True
                continue
            if any(b.get("capture_risk") for b in blocks):
                lines.append(textwrap.indent(ast.unparse(m), "    "))
                report["methods_sealed"][m.name] = "capture risk"
                body_has = True
                continue
            base_fns, method_body = _emit_method(blocks, meta, cls,
                                                 m.name)
            module_base.append(base_fns)
            lines.append(method_body)
            report["methods_fine"][m.name] = {
                "blocks": len(blocks),
                "opaque": sum(1 for b in blocks if b["kind"] == "opaque")}
            body_has = True
        else:
            lines.append(textwrap.indent(ast.unparse(m), "    "))
            report["verbatim"] += 1
            body_has = True
    if not body_has:
        lines.append("    pass")
    return "".join(module_base) + "\n".join(lines) + "\n", report


def onionize_module_source(src, module_name="module", learn=True,
                           rng_seed=13, open_classes=True):
    """Module source in → (onion source, report)."""
    tree = ast.parse(textwrap.dedent(src))
    out = [f"# GENERATED by lfpoop.onionize — the LFPOOPy onion of "
           f"{module_name}"]
    report = {"fine": {}, "sealed": {}, "verbatim": 0}
    fn_names = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            fsrc = ast.unparse(node)
            if node.decorator_list:
                out.append(fsrc + "\n")
                report["sealed"][node.name] = "decorated"
                fn_names.append(node.name)
                continue
            try:
                blocks, meta = B.blockify_source(fsrc, opaque=True)
            except B.BlockifyRefusal as e:
                out.append(fsrc + "\n")
                report["sealed"][node.name] = str(e)
                fn_names.append(node.name)
                continue
            risk = [b["i"] for b in blocks if b.get("capture_risk")]
            if risk:
                # an unsound sealed-closure capture — DO NOT claim fine;
                # seal the whole function verbatim and report the reason
                # (totality is honest: coarser, never wrong) — v4 MED-4
                out.append(fsrc + "\n")
                report["sealed"][node.name] = (
                    f"closure captures a later-rebound var "
                    f"(blocks {risk}) — sealed to preserve behavior")
                fn_names.append(node.name)
                continue
            out.append(_emit_function(blocks, meta))
            report["fine"][node.name] = {
                "blocks": len(blocks),
                "opaque": sum(1 for b in blocks if b["kind"] == "opaque")}
            fn_names.append(node.name)
        elif isinstance(node, ast.ClassDef) and open_classes \
                and not node.decorator_list:
            csrc, crep = _emit_class(node)
            out.append(csrc)
            report.setdefault("classes", {})[node.name] = crep
        else:
            out.append(ast.unparse(node) + "\n")
            report["verbatim"] += 1

    if learn and fn_names:
        # the learned roll-up over the module's OWN static wiring, derived
        # straight from the parsed tree (self-contained by construction)
        fdefs = {n.name: n for n in tree.body
                 if isinstance(n, ast.FunctionDef)}
        edges = {}
        for name, node in fdefs.items():
            for c in ast.walk(node):
                if (isinstance(c, ast.Call)
                        and isinstance(c.func, ast.Name)
                        and c.func.id in fdefs and c.func.id != name):
                    edges[(name, c.func.id)] = edges.get(
                        (name, c.func.id), 0) + 1
        wiring = R.combine_wiring(edges, {})
        _, assign = R.learn_rollup(dict.fromkeys(fdefs), wiring,
                                   rng=random.Random(rng_seed))
        rings = {}
        for fn, r in assign.items():
            rings.setdefault(r, []).append(fn)
        out.append("# THE LEARNED ROLL-UP — rings from the module's own "
                   "wiring")
        ring_cls = []
        for r, members in sorted(rings.items()):
            cname = f"Ring_{r.replace('r_', '')}"
            ring_cls.append(cname)
            out.append(f"class {cname}:")
            out.append(f"    __ring_members__ = {sorted(members)!r}")
            for fn in sorted(members):
                out.append(f"    {fn} = staticmethod({fn})")
            out.append("")
        # a CLASS is a natural ring — its methods are its members; add the
        # opened classes to the ring roster so the module onion sees the
        # whole structure (functions-by-wiring + classes-as-authored-rings)
        class_rings = sorted(report.get("classes", {}))
        onion_name = (module_name.split('.')[-1].title().replace('_', '')
                      + "Onion")
        out.append(f"class {onion_name}:")
        out.append(f"    __function_rings__ = {ring_cls!r}")
        out.append(f"    __class_rings__ = {class_rings!r}")
        out.append(f"    __rings__ = {ring_cls + class_rings!r}")
        out.append("")
        report["rings"] = {r: sorted(m) for r, m in rings.items()}
        report["class_rings"] = {
            c: sorted(list(cr.get("methods_fine", {}))
                      + list(cr.get("methods_sealed", {})))
            for c, cr in report.get("classes", {}).items()}
    return "\n".join(out), report


def onionize_module(module, learn=True, rng_seed=13):
    return onionize_module_source(inspect.getsource(module),
                                  module.__name__, learn=learn,
                                  rng_seed=rng_seed)


_BOOTSTRAP = """
import importlib.util, sys
sys.path.insert(0, {pkg_root!r})
import {package}                                   # the real package first
spec = importlib.util.spec_from_file_location({fullname!r}, {onion_path!r})
mod = importlib.util.module_from_spec(spec)
sys.modules[{fullname!r}] = mod                    # the SWAP
spec.loader.exec_module(mod)
setattr({package}, {attr!r}, mod)
sys.path.insert(0, {test_dir!r})
import {test_mod} as T
sys.exit(T.main())
"""


def shadow_module(onion_source, fullname, test_path, pkg_root):
    """THE MODULE-GRAIN SHADOW LAW: run the module's OWN suite against the
    onionized build, in a subprocess. Returns (green, output)."""
    package, _, attr = fullname.rpartition(".")
    with tempfile.TemporaryDirectory() as td:
        onion_path = os.path.join(td, f"{attr}_onion.py")
        with open(onion_path, "w") as f:
            f.write(onion_source)
        boot = _BOOTSTRAP.format(
            pkg_root=pkg_root, package=package, fullname=fullname,
            onion_path=onion_path, attr=attr,
            test_dir=os.path.dirname(os.path.abspath(test_path)),
            test_mod=os.path.splitext(os.path.basename(test_path))[0])
        boot_path = os.path.join(td, "_boot.py")
        with open(boot_path, "w") as f:
            f.write(boot)
        r = subprocess.run([sys.executable, boot_path],
                           capture_output=True, text=True, timeout=600)
        return r.returncode == 0, (r.stdout + r.stderr)[-2000:]
