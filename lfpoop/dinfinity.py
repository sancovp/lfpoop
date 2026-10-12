"""D∞ — Scott's inverse-limit domain, built as a PROOF OBJECT (stdlib only).

Why this module exists
----------------------
`domain.py` gives a finite Scott domain D and a step F with lfp(F)=gfp(F)=⊤
(the "one entity" — the least AND greatest fixpoint coincide because F is
branchless). That answers "what is the top" for ONE domain. It does NOT yet
answer the recursion Isaac keeps naming — the *tower of orders* (World →
Formula1Stable → Racetrack → Championship), where each order is an OPTIMIZER
over the one below and "from the top it is one entity." The mathematical home
of that recursion is **Scott's D∞**: a domain isomorphic to its own space of
continuous self-maps,

        D∞  ≅  [D∞ → D∞].

An element of such a domain *is* a function on elements — including itself. So
self-application `x·x` is well typed; "from the top it's one entity" is the
statement that point-nature and function-nature are the same thing. This is
also the exact home of `chains.py`'s "D:D→D seat" (the compoctopus
MetaCompiler): a `D:D→D` is an endo-map that is *also* an element only when
D≅[D→D].

The construction (Scott 1972), finitely
---------------------------------------
An **embedding-projection pair** (ep-pair) D ⇄ E is (e:D→E, p:E→D), both
monotone, with

        p ∘ e = id_D          (e is a section — faithful)
        e ∘ p ⊑ id_E          (p is a retraction — below identity)

so D is a *retract* (a faithful sub-domain) of E. The **function-space
functor** sends D to [D→D] (monotone self-maps, ordered pointwise, ⊥ = the
constant-⊥ map) and lifts an ep-pair A⇄B to [A→A] ⇄ [B→B] by
e'(f)=e∘f∘p, p'(g)=p∘g∘e. Starting from any base D₀ with the canonical
ep-pair D₀ ⇄ [D₀→D₀] (e₀(x)=λ_. x the constant map, p₀(f)=f(⊥)), the **tower**

        D₀ ⇄ D₁ ⇄ D₂ ⇄ …            D_{n+1} = [D_n → D_n]

has D∞ = its inverse limit; the ep-pairs make the shift "×1 level = take the
function space" converge to the isomorphism D∞ ≅ [D∞ → D∞].

The finite witness (what is PROVEN here, exhaustively)
-----------------------------------------------------
The tower's own embedding e_n : D_n → D_{n+1}=[D_n→D_n] *is* the map "reincarnate
the point x as a function D_n→D_n" (e_n(x) = λz. e_{n-1}(x(p_{n-1}z))). So
eps[n] is literally the ep-pair  D_n ⇄ [D_n→D_n]  and:

  * **η exact, every level:**  p_n(e_n(x)) = x for all x∈D_n — view a point as a
    function, read it back, recover the point exactly. (point ↪ function,
    faithfully recoverable; point ≡ function holds ONLY in the limit — at every
    finite level the points are a strict subset of the functions.)
  * **retract exact, every level:** e_n∘p_n ⊑ id — every self-map of D_n is
    approximated from below by a point; the ones it misses are exactly the
    |D_{n+1}|−|D_n| NEW elements first appearing at level n+1. The defect is
    strictly positive at every finite stage and vanishes only in the limit —
    that is the honest content of "≅ holds at D∞, not at any finite stage."
  * **self-application total + lawful:** app(n,x,z) = e_{n-1}(x(p_{n-1}z)) is
    defined for ALL x,z∈D_n (n≥1), monotone in both — in particular app(n,x,x)
    exists for every x. Everything can eat itself. Its semantics are pinned by
    laws that a broken app would fail (tested): left-strictness
    app(n,⊥,z)=⊥; the embedded identity acts as the identity on representables
    app(n,id,e(w))=e(w) and as the retract-closure in general app(n,id,z)=e(p(z))⊑z;
    and app discriminates in both arguments (it is not any constant map).
    NOTE app is DEFINED as the unfolding of the functor embedding — "app equals
    applying x's function-incarnation" is definitional, not a theorem; the
    laws above are the non-circular content.

The infinite ≅ itself is Scott's theorem; here the finite stages that limit to
it are checked exhaustively on tractable bases (Sierpiński, small chains,
flat), and the tower is attached for one rung to lfpoop's OWN realization
ladder (`ontology.LADDER`) so D₀ is the SDK's real quality domain, not a toy.

Stdlib only. Order-theory conventions match `domain.py` (⊑ = information order).
"""
from dataclasses import dataclass, field
from typing import Callable

from . import ontology as O


# ─────────────────────────── finite pointed posets ───────────────────────────
@dataclass
class Domain:
    """A finite poset with a least element ⊥. Elements must be hashable and
    canonically ordered (the tuple index is the address used by function
    representations). `leq` is the ⊑ (information / approximation) order."""
    elements: tuple
    leq: Callable            # (a, b) -> bool, the ⊑ order
    bottom: object
    name: str = ""
    _index: dict = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        self.elements = tuple(self.elements)
        self._index = {e: i for i, e in enumerate(self.elements)}

    def __len__(self):
        return len(self.elements)

    def index(self, x):
        return self._index[x]

    # ── laws (checked, never assumed) ──
    def is_poset(self) -> bool:
        E = self.elements
        refl = all(self.leq(a, a) for a in E)
        anti = all(a == b for a in E for b in E
                   if self.leq(a, b) and self.leq(b, a))
        trans = all(self.leq(a, c) for a in E for b in E for c in E
                    if self.leq(a, b) and self.leq(b, c))
        return refl and anti and trans

    def has_bottom(self) -> bool:
        return all(self.leq(self.bottom, x) for x in self.elements)


def _linear_extension(D: Domain):
    """Indices ordered so a ⊑ b (a≠b) ⇒ a precedes b — sort by down-set size."""
    E = D.elements
    down = [sum(1 for b in E if D.leq(b, a)) for a in E]
    return sorted(range(len(E)), key=lambda i: down[i])


def monotone_maps(D: Domain):
    """Every monotone self-map D→D, each as a tuple `img` with
    img[D.index(x)] = f(x). Backtracking that assigns outputs respecting
    monotonicity against all already-assigned arguments."""
    E = D.elements
    n = len(E)
    order = _linear_extension(D)
    img = [None] * n
    out = []

    def bt(k):
        if k == n:
            out.append(tuple(img))
            return
        i = order[k]
        for cand in E:
            ok = True
            for j in range(n):
                if img[j] is None:
                    continue
                if D.leq(E[j], E[i]) and not D.leq(img[j], cand):
                    ok = False
                    break
                if D.leq(E[i], E[j]) and not D.leq(cand, img[j]):
                    ok = False
                    break
            if ok:
                img[i] = cand
                bt(k + 1)
                img[i] = None

    bt(0)
    return out


def apply_fn(D: Domain, f_img, x):
    """Apply a monotone-map element `f_img` (of funspace(D)) to x∈D."""
    return f_img[D.index(x)]


def funspace(D: Domain, name: str = None) -> Domain:
    """[D→D] — the domain of monotone self-maps, ordered pointwise, with
    ⊥ = the constant-⊥ map."""
    maps = monotone_maps(D)
    bottom = tuple(D.bottom for _ in D.elements)

    def leq(f, g):
        return all(D.leq(f[i], g[i]) for i in range(len(D)))

    return Domain(maps, leq, bottom, name or f"[{D.name}→{D.name}]")


# ─────────────────────────── embedding-projection pairs ──────────────────────
@dataclass
class EPPair:
    """(e:src→tgt, p:tgt→src) — an embedding-projection pair. `src` is a
    retract of `tgt`; when tgt = funspace(src) it is the point↔function pair.

    `mono_certificate` is a BY-CONSTRUCTION proof (a stated one-liner) that e
    and p are monotone, set only by constructors that actually warrant it
    (base_ep, lift_ep). It matters when a side is too large for the all-pairs
    check: valid() accepts a SKIPPED monotonicity check only against a
    certificate — a skipped check with no certificate is a FAIL, never a pass
    (the 2026-08-07 verifier finding: None must not coerce to True)."""
    src: Domain
    tgt: Domain
    e: Callable
    p: Callable
    name: str = ""
    mono_certificate: str = ""

    def check(self, check_mono_upto: int = 400) -> dict:
        """Verify the ep-pair laws. retract (p∘e=id, over ALL of src) and
        below (e∘p⊑id, over ALL of tgt) are always exhaustive. Monotonicity is
        all-pairs when the side is ≤ check_mono_upto elements, else None
        (= NOT checked here; see mono_certificate)."""
        retract = all(self.p(self.e(x)) == x for x in self.src.elements)   # η exact
        below = all(self.tgt.leq(self.e(self.p(y)), y)                      # ⊑ id
                    for y in self.tgt.elements)
        defect = sum(1 for y in self.tgt.elements if self.e(self.p(y)) != y)
        e_mono = (_is_monotone(self.src, self.tgt, self.e)
                  if len(self.src) <= check_mono_upto else None)
        p_mono = (_is_monotone(self.tgt, self.src, self.p)
                  if len(self.tgt) <= check_mono_upto else None)
        return dict(retract=retract, below=below, defect=defect,
                    src=len(self.src), tgt=len(self.tgt),
                    e_mono=e_mono, p_mono=p_mono,
                    mono_certificate=self.mono_certificate or None)

    def valid(self, **kw) -> bool:
        """True iff the laws are PROVEN: retract + below exhaustively, and
        each monotonicity conjunct either checked True or covered by a
        by-construction certificate. A skipped check without a certificate
        fails — this method never trusts silence."""
        c = self.check(**kw)
        mono_ok = all(m is True or (m is None and bool(self.mono_certificate))
                      for m in (c["e_mono"], c["p_mono"]))
        return c["retract"] and c["below"] and mono_ok


def _is_monotone(src: Domain, tgt: Domain, f: Callable) -> bool:
    E = src.elements
    return all(tgt.leq(f(a), f(b)) for a in E for b in E if src.leq(a, b))


def base_ep(D: Domain):
    """The canonical D ⇄ [D→D]: e(x)=λ_. x (constant map), p(f)=f(⊥).
    Monotone by construction — the certificate states the proof."""
    F = funspace(D)

    def e(x):
        return tuple(x for _ in D.elements)          # the constant-x map

    def p(f):
        return apply_fn(D, f, D.bottom)              # evaluate at ⊥

    cert = ("e(x)=const_x: x⊑y ⇒ const_x ⊑ const_y pointwise. "
            "p(f)=f(⊥): f⊑g pointwise INCLUDES f(⊥)⊑g(⊥) as its ⊥-coordinate "
            "conjunct (funspace's order is pointwise by definition).")
    return EPPair(D, F, e, p, name=f"{D.name} ⇄ [{D.name}→{D.name}]",
                  mono_certificate=cert), F


def lift_ep(ep: EPPair):
    """The function-space functor on an ep-pair A⇄B → [A→A] ⇄ [B→B]:
    e'(g)=e∘g∘p, p'(h)=p∘h∘e. Preserves the ep-pair laws (algebraic
    consequence of p∘e=id and e∘p⊑id)."""
    A, B = ep.src, ep.tgt
    FA, FB = funspace(A), funspace(B)

    def E(g):                                        # g ∈ [A→A]  ↦  e∘g∘p ∈ [B→B]
        return tuple(ep.e(apply_fn(A, g, ep.p(b))) for b in B.elements)

    def P(h):                                        # h ∈ [B→B]  ↦  p∘h∘e ∈ [A→A]
        return tuple(ep.p(apply_fn(B, h, ep.e(a))) for a in A.elements)

    cert = ("e′(g)=e∘g∘p and p′(h)=p∘h∘e are compositions of monotone maps "
            "(e,p monotone by the source pair's certificate/check; apply_fn is "
            "monotone in the map argument under the pointwise order), and "
            "composition preserves monotonicity."
            + (f" [source: {ep.mono_certificate}]" if ep.mono_certificate else ""))
    return EPPair(FA, FB, E, P, name=f"[{A.name}→·] ⇄ [{B.name}→·]",
                  mono_certificate=cert), FA, FB


# ─────────────────────────────────── the tower ───────────────────────────────
class Tower:
    """The inverse-limit tower D₀ ⇄ D₁ ⇄ … ⇄ D_N approximating D∞.

    domains[n] = D_n   (D_{n+1} = [D_n → D_n])
    eps[n]     = the ep-pair D_n ⇄ D_{n+1}, which — since D_{n+1}=[D_n→D_n] —
                 IS the point↔function pair at level n.
    """

    def __init__(self, D0: Domain, height: int):
        self.domains = [D0]
        self.eps = []
        ep, D1 = base_ep(D0)
        self.domains.append(D1)
        self.eps.append(ep)
        for _ in range(1, height):
            ep, _FA, FB = lift_ep(self.eps[-1])
            self.domains.append(FB)                  # D_{n+1} = funspace(D_n)
            self.eps.append(ep)

    @property
    def height(self):
        return len(self.domains) - 1

    def as_function(self, n: int, x):
        """x∈D_n reincarnated as a self-map D_n→D_n (an element of D_{n+1})."""
        return self.eps[n].e(x)

    def as_point(self, n: int, f):
        """Read a self-map f∈[D_n→D_n]=D_{n+1} back down to a point of D_n."""
        return self.eps[n].p(f)

    def app(self, n: int, x, z):
        """Self-application at level n≥1:  x·z = e_{n-1}( x( p_{n-1}(z) ) ).
        x∈D_n=[D_{n-1}→D_{n-1}] is used AS a function; z∈D_n is the argument.
        Total for all x,z — in particular app(n,x,x) (x eats itself)."""
        if n < 1:
            raise ValueError("self-application needs n ≥ 1 (D_n must be a "
                             "function space)")
        below = self.eps[n - 1]                      # D_{n-1} ⇄ D_n
        arg = below.p(z)                             # project z into D_{n-1}
        res = apply_fn(self.domains[n - 1], x, arg)  # x as [D_{n-1}→D_{n-1}]
        return below.e(res)                          # embed the result into D_n

    def report(self) -> dict:
        """Sizes + the ep-pair verdict per rung. `defect` at rung n counts the
        D_n self-maps that are NOT embedded points — the |D_{n+1}|−|D_n| NEW
        elements first appearing at D_{n+1}. It is strictly positive at every
        finite rung; the retract becomes the iso only in the limit."""
        rungs = []
        for n, ep in enumerate(self.eps):
            c = ep.check()
            rungs.append(dict(level=n, size=len(self.domains[n]),
                              fun_size=len(self.domains[n + 1]),
                              eta_exact=c["retract"], retract=c["below"],
                              defect=c["defect"]))
        rungs.append(dict(level=self.height,
                          size=len(self.domains[self.height]),
                          fun_size=None, eta_exact=None, retract=None,
                          defect=None))
        return dict(base=self.domains[0].name, height=self.height, rungs=rungs)


# ────────────────────────────────── base domains ─────────────────────────────
def sierpinski() -> Domain:
    """𝕆 = {⊥ ⊑ ⊤}. The smallest non-trivial domain; the tower over it is
    the cleanest multi-level witness (|D_n| = 2, 3, 10, …)."""
    return Domain(("⊥", "⊤"), lambda a, b: a == "⊥" or b == "⊤", "⊥", "𝕆")


def chain(k: int) -> Domain:
    """The k+1 element chain 0 ⊑ 1 ⊑ … ⊑ k."""
    return Domain(tuple(range(k + 1)), lambda a, b: a <= b, 0, f"C{k}")


def flat(atoms) -> Domain:
    """The lifted flat domain: ⊥ below a set of pairwise-incomparable atoms
    (a NON-chain base — shows the construction is not linear-order specific)."""
    els = ("⊥",) + tuple(atoms)
    return Domain(els, lambda a, b: a == "⊥" or a == b, "⊥",
                  "flat" + str(len(atoms)))


def ladder_domain() -> Domain:
    """lfpoop's OWN realization ladder (`ontology.LADDER`) as a chain domain —
    the `level` coordinate of `domain.State`. This is the intended D₀ (the
    'car' / the artifact whose realization level is its fitness). Its full
    function space [ladder→ladder] has 92,378 elements — enumerable, so the
    base rung's retract (p∘e=id) and below (e∘p⊑id) laws are verified
    exhaustively over all of them; monotonicity at this size rides the
    by-construction certificate (all-pairs would be ~8.5e9 comparisons).
    Deeper rungs would be over that 92k-element domain (astronomically large),
    hence the multi-level proof runs on the tractable bases above and the SDK
    connection is proven for the first rung."""
    n = len(O.LADDER)
    return Domain(tuple(range(n)), lambda a, b: a <= b, 0, "ladder")


# ──────────────────────────────────── demo ───────────────────────────────────
def _fmt(rung):
    if rung["fun_size"] is None:
        return f"  D{rung['level']}: |{rung['size']}|   (top of truncation)"
    return (f"  D{rung['level']}: |{rung['size']:>5}|  ⇄ [D{rung['level']}→D{rung['level']}] "
            f"|{rung['fun_size']:>6}|   η-exact={rung['eta_exact']} "
            f"retract⊑id={rung['retract']}  defect(new at D{rung['level']+1}; "
            f"0 only in the limit)={rung['defect']}")


def demo():
    print("D∞ as an inverse-limit tower — the point↔function identity, per rung\n")
    # Sierpiński (|D_n| = 2,3,10) is the only base whose 3rd domain is still
    # enumerable, so it carries the multi-level tower; the 3-element bases show
    # the construction is not chain-specific at one rung each. (funspace of a
    # ≥10-element LATTICE is astronomically large — do not build it.)
    for base, height in ((sierpinski(), 2), (chain(2), 1), (flat(("a", "b")), 1)):
        t = Tower(base, height=height)
        r = t.report()
        print(f"tower over {r['base']} (height {r['height']}):")
        for rung in r["rungs"]:
            print(_fmt(rung))
        n = t.height                                   # the top usable level
        D = t.domains[n]
        total = all(t.app(n, x, x) in D.elements for x in D.elements)
        print(f"  self-application app({n},x,x) total over D{n}: {total} "
              f"({len(D)} elements, each eats itself)\n")

    # the SDK-rooted rung: D₀ = lfpoop's realization ladder
    lad = ladder_domain()
    t = Tower(lad, height=1)
    c = t.eps[0].check()
    print(f"tower over lfpoop's realization ladder: "
          f"|D0|={len(t.domains[0])}  |[ladder→ladder]|={len(t.domains[1])}  "
          f"η-exact={c['retract']}  retract⊑id={c['below']}")


if __name__ == "__main__":
    demo()
