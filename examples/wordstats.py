"""wordstats — a tiny text-analytics program: THE LFPOOP EXAMPLE SUBJECT.

This is PLAIN PYTHON. It imports nothing from lfpoop. It is the "other code"
LFPOOP reads and transforms — the point of the example is that lfpoop takes
THIS, that it has never seen, and emits its onion (examples/wordstats_onion.py),
proven by wordstats' OWN test suite (examples/test_wordstats.py) running green
against the onionized build.

It is deliberately shaped to exercise the whole pipeline:
  * an internal CALL CHAIN (top_words → word_count → tokenize → normalize)
    so rollup has real wiring to learn;
  * a CURRIED CONFIG param (`stopwords`, shared across four functions) so
    classify/apionize have an alphabet to factor;
  * an AUGASSIGN accumulator (`n += 1`) — the shadow path the v4 verifier
    found and we fixed;
  * a LAMBDA inside a statement (the sort key) — sealed as an opaque block;
  * a CLASS with methods — opened at method grain.
"""
import re

_WORD = re.compile(r"[a-z']+")


def normalize(text):
    return text.lower().strip()


def tokenize(text):
    norm = normalize(text)
    return _WORD.findall(norm)


def word_count(text, stopwords):
    counts = {}
    for tok in tokenize(text):
        if tok in stopwords:
            continue
        counts[tok] = counts.get(tok, 0) + 1
    return counts


def total_words(text, stopwords):
    n = 0
    for tok in tokenize(text):
        if tok not in stopwords:
            n += 1                       # augassign — the fixed shadow path
    return n


def top_words(text, stopwords, k):
    counts = word_count(text, stopwords)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:k]


class Report:
    """A stateful reporter — its stopwords are its bound configuration."""

    def __init__(self, stopwords):
        self.stopwords = stopwords

    def summary(self, text, k):
        total = total_words(text, self.stopwords)
        top = top_words(text, self.stopwords, k)
        return {"total": total, "top": top}
