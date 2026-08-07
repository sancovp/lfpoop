"""D∞ tests — the inverse-limit tower as a PROOF OBJECT.

Every claim is checked exhaustively on tractable bases (Sierpiński, small
chains, flat) and for one rung on lfpoop's OWN realization ladder. What is
proven here, mechanically:

  * funspace(D) is EXACTLY the monotone self-maps (sound + complete vs a
    brute-force enumeration), correctly sized;
  * the ep-pair laws p∘e = id and e∘p ⊑ id hold EXHAUSTIVELY on every rung;
    monotonicity is all-pairs where |D| ≤ 400 and by-construction certificate
    above that (valid() REFUSES a skipped check with no certificate — the
    2026-08-07 verifier's counterexample is a regression test here);
  * the function-space functor PRESERVES ep-pairs (the tower is ep-pairs);
  * η is EXACT at every level — a point embeds as a function and is read back
    exactly (a faithful section; point ≡ function only in the limit);
  * self-application app(n,x,z) is TOTAL, monotone, and LAWFUL: left-strict
    (app(⊥,z)=⊥), the embedded identity is the identity on representables and
    the retract-closure in general (app(id,z) ⊑ z), it discriminates in both
    arguments (no constant app passes), and it matches an INDEPENDENTLY
    reimplemented oracle at rung 1. ("app = applying x's function-incarnation"
    is definitional — the functor embedding IS app's unfolding — so it is NOT
    asserted as a theorem; the laws are the non-circular content. The
    2026-08-07 verifier caught the earlier circular check.)

The infinite iso D∞ ≅ [D∞→D∞] itself is Scott's limit theorem; these are the
finite stages that ascend to it. The defect (|D_{n+1}|−|D_n|) is strictly
positive at every finite stage and vanishes only in the limit.

Run: python3 tests/test_dinfinity.py
"""
import math
import os
import sys
from itertools import product

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lfpoop import dinfinity as X


def _brute_monotone(D):
    """All monotone self-maps by naive filter of D^D — the independent oracle
    that funspace() is checked against (only for tiny D)."""
    E = D.elements
    out = set()
    for img in product(E, repeat=len(E)):
        if all(D.leq(img[D.index(a)], img[D.index(b)])
               for a in E for b in E if D.leq(a, b)):
            out.add(img)
    return out


def main():
    checks = {}
    SIER, C2, FLAT, LAD = (X.sierpinski(), X.chain(2),
                           X.flat(("a", "b")), X.ladder_domain())

    # ── base domains are finite pointed posets (exhaustive) ──
    checks["bases_are_posets_with_bottom"] = all(
        D.is_poset() and D.has_bottom() for D in (SIER, C2, FLAT, LAD))

    # ── funspace = EXACTLY the monotone maps (sound + complete), sized ──
    fs_ok = True
    for D, n in ((SIER, 3), (C2, 10), (FLAT, 11)):
        produced = set(X.monotone_maps(D))
        if produced != _brute_monotone(D) or len(produced) != n:
            fs_ok = False
    checks["funspace_sound_and_complete"] = fs_ok
    # the ladder: 10-chain → non-decreasing length-10 sequences = C(19,10).
    checks["funspace_ladder_count_exact"] = (
        len(X.funspace(LAD)) == math.comb(2 * len(LAD) - 1, len(LAD)) == 92378)
    # funspace is itself a pointed poset with const-⊥ as bottom.
    F = X.funspace(SIER)
    checks["funspace_is_pointed_poset"] = (
        F.is_poset() and F.has_bottom()
        and F.bottom == tuple(SIER.bottom for _ in SIER.elements))

    # ── the base ep-pair D ⇄ [D→D] holds EXHAUSTIVELY on every base ──
    base_ok, defect_ok = True, True
    for D in (SIER, C2, FLAT, LAD):
        ep, Fn = X.base_ep(D)
        c = ep.check()
        if not (c["retract"] and c["below"]):
            base_ok = False
        if c["e_mono"] is False or c["p_mono"] is False:
            base_ok = False
        if c["defect"] != len(Fn) - len(D):          # = functions minus points
            defect_ok = False
    checks["base_ep_laws_exhaustive_all_bases"] = base_ok
    checks["defect_equals_functions_minus_points"] = defect_ok

    # ── the functor PRESERVES ep-pairs: lift(base_ep(𝕆)) is a valid ep-pair
    #    over D2 (10 elements), exhaustively ──
    ep0, _ = X.base_ep(SIER)
    ep1, _FA, _FB = X.lift_ep(ep0)
    c1 = ep1.check()
    checks["functor_preserves_eppair_exhaustive"] = (
        c1["retract"] and c1["below"]
        and c1["e_mono"] is not False and c1["p_mono"] is not False)

    # ── the tower over 𝕆: sizes 2,3,10 and every rung an exact ep-pair ──
    t = X.Tower(SIER, height=2)
    r = t.report()
    checks["tower_sizes_2_3_10"] = [rg["size"] for rg in r["rungs"]] == [2, 3, 10]
    checks["tower_every_rung_eta_exact"] = all(
        rg["eta_exact"] for rg in r["rungs"][:-1])
    checks["tower_every_rung_retract"] = all(
        rg["retract"] for rg in r["rungs"][:-1])
    # the defect is the size gap |D_{n+1}|−|D_n| — strictly positive at every
    # finite rung (the retract is NOT the iso until the limit).
    checks["tower_defect_equals_size_gap"] = (
        r["rungs"][0]["defect"] == 3 - 2 and r["rungs"][1]["defect"] == 10 - 3
        and all(rg["defect"] >= 1 for rg in r["rungs"][:-1]))

    # ── η EXACT, every level, EVERY element: point→function→point = id ──
    #    (the faithful point↔function identity — the finite shadow of the iso)
    eta = True
    for n in range(t.height):                        # levels with an ep-pair up
        Dn = t.domains[n]
        for x in Dn.elements:
            if t.as_point(n, t.as_function(n, x)) != x:
                eta = False
    checks["eta_exact_every_element_every_level"] = eta

    # β on representables: a function that IS a reincarnated point round-trips
    # exactly (function→point→function = id on the embedding's image).
    beta_img = True
    for n in range(t.height):
        Dn = t.domains[n]
        for x in Dn.elements:
            f = t.as_function(n, x)                   # f ∈ image(e_n)
            if t.as_function(n, t.as_point(n, f)) != f:
                beta_img = False
    checks["beta_exact_on_representable_functions"] = beta_img

    # ── self-application app(n,x,z): TOTAL, monotone, and LAWFUL. Exhaustive
    #    on D1 (3) and D2 (10). NOTE: we deliberately do NOT assert
    #    app == apply(as_function(x), z) — both sides unfold to the identical
    #    e∘apply∘p expression, so that "check" is f(a)==f(a) (circular; the
    #    2026-08-07 verifier's blocking finding). The laws below are the
    #    non-circular semantics: each would FAIL under a constant-⊥ app, a
    #    constant-element app, or a transposed/wrong-ep app. ──
    total, mono = True, True
    strict, ident_repr, ident_retract, discr_z, discr_x = True, True, True, True, True
    for n in range(1, t.height + 1):
        Dn, Dm = t.domains[n], t.domains[n - 1]
        idm = tuple(Dm.elements)                     # the identity of D_{n-1},
        for x in Dn.elements:                        # as an element of D_n
            for z in Dn.elements:
                if t.app(n, x, z) not in Dn._index:  # totality: lands in D_n
                    total = False
        # monotone in each argument (exhaustive)
        for x in Dn.elements:
            for z1 in Dn.elements:
                for z2 in Dn.elements:
                    if Dn.leq(z1, z2) and not Dn.leq(t.app(n, x, z1),
                                                     t.app(n, x, z2)):
                        mono = False
        for z in Dn.elements:
            for x1 in Dn.elements:
                for x2 in Dn.elements:
                    if Dn.leq(x1, x2) and not Dn.leq(t.app(n, x1, z),
                                                     t.app(n, x2, z)):
                        mono = False
        # LAW 1 — left-strictness: ⊥ applied to anything is ⊥.
        for z in Dn.elements:
            if t.app(n, Dn.bottom, z) != Dn.bottom:
                strict = False
        # LAW 2 — the embedded identity IS the identity on representables …
        for w in Dm.elements:
            ew = t.as_function(n - 1, w)
            if t.app(n, idm, ew) != ew:
                ident_repr = False
        # … and the retract-closure in general: app(id, z) ⊑ z, always.
        for z in Dn.elements:
            if not Dn.leq(t.app(n, idm, z), z):
                ident_retract = False
        # LAW 3 — app discriminates in BOTH arguments (no constant map).
        if len({t.app(n, x, z) for x in Dn.elements
                for z in Dn.elements}) < 2:
            discr_z = discr_x = False
        else:
            if not any(len({t.app(n, x, z) for z in Dn.elements}) >= 2
                       for x in Dn.elements):
                discr_z = False
            if not any(len({t.app(n, x, z) for x in Dn.elements}) >= 2
                       for z in Dn.elements):
                discr_x = False
    checks["self_application_total_every_element"] = total
    checks["self_application_monotone_both_args"] = mono
    checks["app_left_strict"] = strict
    checks["app_identity_on_representables"] = ident_repr
    checks["app_identity_is_retract_closure"] = ident_retract
    checks["app_discriminates_both_args"] = discr_z and discr_x

    # LAW 4 — an INDEPENDENT oracle at rung 1: app reimplemented from the raw
    # definition (const-map embed, eval-at-⊥ project) with no Tower/eps code.
    D0, D1 = t.domains[0], t.domains[1]
    ora_e0 = lambda v: tuple(v for _ in D0.elements)              # noqa: E731
    ora_p0 = lambda f: f[D0.index(D0.bottom)]                     # noqa: E731
    ora_app = lambda x, z: ora_e0(x[D0.index(ora_p0(z))])         # noqa: E731
    checks["app_matches_independent_oracle_rung1"] = all(
        t.app(1, x, z) == ora_app(x, z)
        for x in D1.elements for z in D1.elements)

    # the headline: EVERY element eats ITSELF (n≥1) — total, well-typed, and
    # NON-VACUOUS: the self-application image is not a single constant (and
    # contains ⊥, from ⊥ eating itself).
    eats = all(t.app(n, x, x) in t.domains[n]._index
               for n in range(1, t.height + 1) for x in t.domains[n].elements)
    self_img = {t.app(t.height, x, x) for x in t.domains[t.height].elements}
    checks["everything_eats_itself"] = (
        eats and len(self_img) >= 2
        and t.domains[t.height].bottom in self_img)

    # ── valid() must never trust silence (regression: the verifier's
    #    counterexample — a skipped monotonicity check coerced to a pass) ──
    epc, Fc = X.base_ep(C2)
    checks["valid_accepts_certified_skip"] = epc.valid(check_mono_upto=0)
    stripped = X.EPPair(epc.src, epc.tgt, epc.e, epc.p, name="uncertified")
    checks["valid_rejects_uncertified_skip"] = not stripped.valid(
        check_mono_upto=0)
    # a computed-False monotonicity beats ANY certificate: the verifier's
    # concrete non-monotone p (eval-at-0 except p((1,1,2))=0) — retract and
    # below still hold exhaustively, so ONLY the mono conjunct can catch it.
    bad_at = (1, 1, 2)
    assert bad_at in Fc._index, "counterexample element must exist"
    bad_p = lambda f: 0 if f == bad_at else X.apply_fn(C2, f, C2.bottom)  # noqa: E731
    bad = X.EPPair(C2, Fc, epc.e, bad_p, name="bad-p",
                   mono_certificate="a LIE — computed False must beat this")
    bc = bad.check()
    checks["valid_rejects_nonmonotone_p_despite_certificate"] = (
        bc["retract"] and bc["below"] and bc["p_mono"] is False
        and not bad.valid())
    # the base certificate's ⊥-conjunct claim, verified exhaustively on C2:
    # f ⊑ g pointwise implies f(⊥) ⊑ g(⊥).
    ib = C2.index(C2.bottom)
    checks["funspace_order_contains_bottom_conjunct"] = all(
        C2.leq(f[ib], g[ib])
        for f in Fc.elements for g in Fc.elements if Fc.leq(f, g))

    # ── SDK attachment: the tower rooted at lfpoop's realization ladder —
    #    retract + below verified EXHAUSTIVELY over all 92,378 self-maps;
    #    monotonicity at this size rides the by-construction certificate
    #    (which valid() requires and records) ──
    tl = X.Tower(LAD, height=1)
    cl = tl.eps[0].check()
    checks["sdk_ladder_rung_retract_below_exhaustive"] = (
        cl["retract"] and cl["below"] and len(tl.domains[1]) == 92378
        and cl["mono_certificate"] is not None and tl.eps[0].valid())

    print()
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print(f"\nD∞: the inverse-limit tower is an exact ep-pair at every finite "
          f"level (η exact, retract ⊑ id — a faithful retract, NOT yet the "
          f"iso), the functor preserves the ep-pair laws, and self-application "
          f"is total, lawful (strict · identity-on-representables · "
          f"discriminating · oracle-matched), and monotone — every element is "
          f"also a self-map that can eat itself. The iso D∞≅[D∞→D∞] is the "
          f"limit these ascend to. {len(checks)} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
