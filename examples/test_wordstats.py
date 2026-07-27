"""wordstats' OWN test suite — the acceptance criteria lfpoop must preserve.

shadow_module runs THIS (its main() returning 0) against the onionized
wordstats. Green here against the onion = the transform preserved behavior.

Run directly: python3 examples/test_wordstats.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wordstats import (normalize, tokenize, word_count, total_words,
                       top_words, Report)

SW = {"the", "a", "and"}
TEXT = "The cat and the dog. A cat!"


def main():
    checks = {}
    checks["normalize"] = normalize("  The CAT.  ") == "the cat."
    checks["tokenize"] = tokenize(TEXT) == [
        "the", "cat", "and", "the", "dog", "a", "cat"]
    checks["word_count"] = word_count(TEXT, SW) == {"cat": 2, "dog": 1}
    checks["total_words"] = total_words(TEXT, SW) == 3
    checks["top_words"] = top_words(TEXT, SW, 1) == [("cat", 2)]
    checks["report"] = Report(SW).summary(TEXT, 2) == {
        "total": 3, "top": [("cat", 2), ("dog", 1)]}

    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"FAILED: {failed}")
        return 1
    print(f"wordstats: {len(checks)} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
