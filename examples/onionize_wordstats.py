"""onionize_wordstats — drive the WHOLE lfpoop pipeline over wordstats.

Run: python3 examples/onionize_wordstats.py

Takes the plain wordstats.py (which lfpoop has never seen), and:
  1. ONIONIZE it → writes examples/wordstats_onion.py (checked in, so you
     can read the transformed code on GitHub);
  2. SHADOW it → runs wordstats' OWN suite against the onion (must be green);
  3. CLASS-IFY the curried word_count → a class where stopwords is bound at
     construction and text/… stay the call surface;
  4. PREDICT over the functions as a pool → the derivation of `summary`.

Prints what lfpoop LEARNED, EMITTED, and PREDICTED — and exits non-zero if
the shadow law is not green (the example is only valid if the onion behaves).
"""
import inspect
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from lfpoop import onionize as O
from lfpoop import classify as K
from lfpoop import predict as P
import wordstats


def banner(t):
    print("\n" + "=" * 68 + "\n" + t + "\n" + "=" * 68)


def main():
    banner("1. ONIONIZE — wordstats.py → its LFPOOPy onion")
    src, report = O.onionize_module(wordstats)
    onion_path = os.path.join(HERE, "wordstats_onion.py")
    with open(onion_path, "w") as f:
        f.write(src)
    print(f"  wrote {os.path.relpath(onion_path, ROOT)}")
    print(f"  functions opened fine-grain: {sorted(report['fine'])}")
    for fn, info in sorted(report["fine"].items()):
        note = f" ({info['opaque']} opaque)" if info["opaque"] else ""
        print(f"      {fn}: {info['blocks']} blocks{note}")
    print(f"  classes opened: "
          f"{ {c: list(v['methods_fine']) for c, v in report.get('classes', {}).items()} }")
    print(f"  verbatim floor: {report['verbatim']} statements")
    print(f"  LEARNED function rings (from the call wiring): "
          f"{report.get('rings')}")
    print(f"  class rings: {report.get('class_rings')}")

    banner("2. SHADOW — wordstats' OWN suite vs the onionized build")
    green, out = O.shadow_module(
        src, "wordstats", os.path.join(HERE, "test_wordstats.py"), HERE)
    print("\n".join("  " + l for l in out.strip().splitlines()))
    print(f"  --> shadow law: {'GREEN' if green else 'RED'}")

    banner("3. CLASS-IFY — the curried word_count(text, stopwords)")
    csrc, meta = K.class_ify(inspect.getsource(wordstats.word_count),
                             slots=["stopwords"])
    print(f"  curried (bound at construction): {meta['curried']}")
    print(f"  residue (the call surface):      {meta['residue']}")
    WordCount = K.compile_class(csrc, meta, {"tokenize": wordstats.tokenize})
    wc = WordCount(stopwords={"the", "a", "and"})
    print(f"  WordCount(stopwords=…)('The cat and cat') = "
          f"{wc('The cat and cat')}")

    banner("4. PREDICT — compose the pool; derive `summary`-shaped output")
    pool = [
        P.unit("tokenize", provides=["tokens"], requires=["text"]),
        P.unit("word_count", provides=["counts"],
               requires=["tokens"], slots=["stopwords"]),
        P.unit("top_words", provides=["ranked"], requires=["counts"],
               slots=["k"]),
        P.unit("total_words", provides=["total"], requires=["tokens"],
               slots=["stopwords"]),
        P.unit("summary", provides=["report"],
               requires=["ranked", "total"]),
    ]
    pred = P.predict(pool, base=["text"], bound=["stopwords", "k"])
    for name, verdict in pred.items():
        extra = ""
        if verdict["capability_residue"]:
            extra = f"  needs-arrival: {verdict['capability_residue']}"
        if verdict["binding_residue"]:
            extra += f"  needs-binding: {verdict['binding_residue']}"
        print(f"  {name:12} {verdict['status']}{extra}")
    d = P.derivations(pool, "report", base=["text"])[0]
    print(f"  derivation of `report`: {' -> '.join(d['chain'])}")

    banner("VERDICT")
    if not green:
        print("  the onion did NOT preserve behavior — example INVALID")
        return 1
    print("  wordstats — code lfpoop had never seen — was read into its "
          "onion,\n  its own suite passed against the transformed build, its "
          "curried\n  function became a class, and its composition was "
          "predicted by\n  deduction. The onion is checked in at "
          "examples/wordstats_onion.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
