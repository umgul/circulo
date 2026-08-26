# -*- coding: utf-8 -*-
"""Earned mastery: skill trees an agent has to earn, and can lose.

Most agent memories record what happened. This records what an agent has
become good at, as something it has to earn and can lose.

It does NOT verify anything: the felt verdict comes from the caller. What it
refuses to do is let self-certification be invisible — see ``Ring.judged_by``
and the ``self_judged`` field of ``Circulo.mastery_of``.

Five rules, each of which exists because its absence produced a specific
failure:

1. **Level is READ, never granted.** ``level`` is a label computed from two
   continuous quantities (depth and generativity). Nothing "unlocks". You
   cannot promote a tree; you can only give it evidence and see where it
   lands. A system that grants levels is a system whose levels mean whatever
   the granting code says they mean.

2. **Evidence has kinds, and they are not equal.** Reading about something,
   doing it, and making something new with it are different acts. Studying
   builds depth but generates nothing: an agent that only ever reads can
   approach the ceiling of depth and still never bear fruit, which is
   correct.

3. **A ring must be FELT to count.** Every piece of evidence carries a
   subjective reading. Below the gate, nothing is recorded — no ring, no
   depth, not even a touch of the timestamp. Hollow work must not look like
   work, or the tree grows on noise.

4. **Repeating the same evidence consolidates; it does not teach.** Identical
   evidence is discounted sharply. Without this, a loop that re-submits the
   same success reaches mastery on one fact.

5. **Unused mastery decays.** Dormant trees lose FLUENCY, not memory: the
   rings are never touched — they happened — but depth erodes after a grace
   period. A learning curve that only rises is not learning; it is a counter.
"""

from __future__ import annotations

import logging
import time
from math import isfinite
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)

__all__ = [
    "MasteryLevel", "LEVEL_NAMES", "Ring", "MasteryTree", "Circulo",
    "KIND_STUDY", "KIND_PRACTICE", "KIND_CREATION", "KIND_DISTILL",
    "read_level", "RING_FELT_FLOOR", "DORMANCY_DAYS", "FELT_WEIGHTS",
]


class MasteryLevel(IntEnum):
    """Names for regions of a continuum. They label; they do not gate."""
    SPROUT = 0      # first contact
    ROOTS = 1       # vocabulary that takes hold
    TRUNK = 2       # sustained depth
    CROWN = 3       # applied mastery
    FRUIT = 4       # makes something new


LEVEL_NAMES = {0: "SPROUT", 1: "ROOTS", 2: "TRUNK", 3: "CROWN", 4: "FRUIT"}

# ── Kinds of evidence ───────────────────────────────────────────────────────
KIND_STUDY = "study"          # took something in
KIND_PRACTICE = "practice"    # applied it
KIND_CREATION = "creation"    # made something that did not exist
KIND_DISTILL = "distill"      # compressed many encounters into one insight

# (depth_min, generativity_min) per level, checked high to low.
# FRUIT is the only level with a generativity requirement: you cannot reach it
# by reading, however much you read.
_LEVEL_BANDS = [
    (MasteryLevel.FRUIT, 0.80, 0.25),
    (MasteryLevel.CROWN, 0.65, 0.0),
    (MasteryLevel.TRUNK, 0.40, 0.0),
    (MasteryLevel.ROOTS, 0.15, 0.0),
]

# How much each kind moves DEPTH.
_KIND_DEPTH_GAIN = {
    KIND_STUDY: 0.16, KIND_PRACTICE: 0.20,
    KIND_CREATION: 0.26, KIND_DISTILL: 0.16,
}

# How much each kind moves GENERATIVITY. Understanding does not generate;
# applying does a little; creating does fully. Both tables must list the same
# kinds: `add_ring` refuses anything absent from them.
_GEN_FROM_MAKING = 0.22
_GEN_KIND_MULT = {
    KIND_CREATION: 1.0, KIND_PRACTICE: 0.30,
    KIND_STUDY: 0.0, KIND_DISTILL: 0.30,
}

# ── The felt verdict ────────────────────────────────────────────────────────
# Weights of the subjective reading attached to each piece of evidence.
# ``fulfils`` weighs most because self-realisation is what turns activity into
# growth, and it is the only component that feeds generativity.
FELT_WEIGHTS = {"projects": 0.25, "contributes": 0.25,
                "satisfies": 0.20, "fulfils": 0.30}
RING_FELT_FLOOR = 0.50        # below this the work is hollow: no ring forms

REPEAT_DISCOUNT = 0.25        # identical evidence consolidates, does not teach

# ── Forgetting ──────────────────────────────────────────────────────────────
DORMANCY_DAYS = 30.0          # grace period before disuse costs anything
FORGET_PER_MONTH = 0.90       # depth retained per dormant month thereafter


def read_level(depth: float, generativity: float) -> int:
    """Name where the continuum falls. Blocks nothing; only labels."""
    for _lvl, _d_min, _g_min in _LEVEL_BANDS:
        if depth >= _d_min and generativity >= _g_min:
            return int(_lvl)
    return int(MasteryLevel.SPROUT)


@dataclass
class Ring:
    """One full turn around a subject. Append-only: rings are never removed."""
    # The level the TREE was at when this happened — not a level this ring
    # belongs to. Three rings marked TRUNK are not "TRUNK-grade evidence";
    # they are three things that happened while the tree was already there.
    level_at_time: int
    kind: str
    ts: float
    evidence: str
    felt: dict[str, float] = field(default_factory=dict)
    context: list = field(default_factory=list)
    # OPTIONAL IDENTITY OF THE EVENT this ring records. When two rings carry
    # the same one, they are the same thing happening twice — however
    # differently it was worded. Without it the repeat check falls back to the
    # evidence text, which paraphrase defeats:
    #     "solved it with approach A"
    #     "successfully solved the problem using method A"
    # read as two separate pieces of evidence. Judging that they mean the same
    # needs semantics, and semantics is the caller's business; identity is
    # cheap, exact, and something the caller usually already has.
    event_id: str = ""
    # WHO PRODUCED THE FELT VERDICT. Defaults to "self": an agent grading its
    # own homework, which is the weakest evidence there is. Verification
    # belongs to the caller; what this field buys is that self-certification
    # is visible. Pass whatever actually judged ("pytest", "human-review").
    judged_by: str = "self"

    def composite(self) -> float:
        """The felt verdict, weighted over the components actually present.

        Missing components are not zeros. A caller that reports only what it
        can honestly read is not penalised for the silence — the weights are
        renormalised over what exists.
        """
        if not self.felt:
            return 0.0
        _live = {}
        for _k in FELT_WEIGHTS:
            _v = self.felt.get(_k)
            if _v is None:
                continue
            _v = float(_v)
            if not isfinite(_v):
                # NOT clamped: `min(1.0, nan)` is 1.0 in CPython, so a NaN
                # scored as PERFECT evidence, levelled the tree up and handed
                # it maximal generativity. A value that is not a number is not
                # a reading, so it is dropped like an absent one.
                log.warning("felt[%r] = %r is not a number; ignored. A ring "
                            "must not be built on it.", _k, _v)
                continue
            if not 0.0 <= _v <= 1.0:
                # Out of range means a different scale is being fed in (a
                # 0-100 score, a raw count). Clamping quietly would produce a
                # plausible-looking wrong number.
                log.warning("felt[%r] = %r is outside [0, 1]; clamping. Check "
                            "the scale you are passing in.", _k, _v)
                _v = max(0.0, min(1.0, _v))
            _live[_k] = _v
        if not _live:
            return 0.0
        _total = sum(FELT_WEIGHTS[_k] for _k in _live)
        if _total <= 0:
            return 0.0
        _s = sum(FELT_WEIGHTS[_k] * _live[_k] for _k in _live) / _total
        return max(0.0, min(1.0, _s))

    def passes_gate(self, floor: float = RING_FELT_FLOOR) -> bool:
        return self.composite() >= floor

    def fulfilment(self) -> Optional[float]:
        """The self-realisation reading, or ``None`` if it was not measured.

        Absence means "no generative evidence", not "measured zero" — the same
        rule :meth:`composite` follows. Only ``fulfils`` feeds generativity, so
        a caller that cannot honestly read it produces no generativity, which
        is different from having read a zero.
        """
        _v = self.felt.get("fulfils")
        if _v is None:
            return None
        _v = float(_v)
        if not isfinite(_v):
            return None          # not a number is not a reading
        return max(0.0, min(1.0, _v))

    def to_dict(self) -> dict[str, Any]:
        _d = {"level_at_time": int(self.level_at_time), "kind": self.kind,
              "ts": self.ts,
              "evidence": self.evidence[:240], "felt": dict(self.felt),
              "judged_by": self.judged_by}
        if self.event_id:
            _d["event_id"] = self.event_id
        if self.context:
            _d["context"] = list(self.context)[:8]
        return _d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Ring":
        return cls(level_at_time=int(d.get("level_at_time",
                                            d.get("level", 0))),
                   kind=str(d.get("kind", KIND_STUDY)),
                   ts=float(d.get("ts", 0.0)),
                   evidence=str(d.get("evidence", "")),
                   felt=dict(d.get("felt", {})),
                   context=list(d.get("context", []) or []),
                   judged_by=str(d.get("judged_by", "self")),
                   event_id=str(d.get("event_id", "")))


@dataclass
class MasteryTree:
    """One subject. Depth and generativity are continuous; level is their reading."""
    topic: str
    aliases: list[str] = field(default_factory=list)
    depth: float = 0.0            # integrates felt evidence over time
    generativity: float = 0.0     # how much has been MADE here
    level: int = int(MasteryLevel.SPROUT)   # cached reading of the two above
    rings: list[Ring] = field(default_factory=list)
    planted_from: str = "curiosity"
    created_ts: float = field(default_factory=time.time)
    last_touched: float = field(default_factory=time.time)

    @property
    def level_name(self) -> str:
        return LEVEL_NAMES.get(int(self.level), str(self.level))

    def is_dormant(self, now: Optional[float] = None) -> bool:
        _n = now if now is not None else time.time()
        return (_n - self.last_touched) > DORMANCY_DAYS * 86400.0

    def apply_forgetting(self, now: Optional[float] = None) -> float:
        """Lose fluency on what is not touched. Returns how much depth went.

        The rings are NOT touched: they happened, and they stay. What erodes
        is fluency — like a language you stop speaking. The memories remain;
        the ease does not.
        """
        _n = now if now is not None else time.time()
        if not self.is_dormant(_n) or self.depth <= 0.0:
            return 0.0
        _months = ((_n - self.last_touched) / 86400.0 - DORMANCY_DAYS) / 30.0
        if _months <= 0.0:
            return 0.0
        _left = self.depth * (FORGET_PER_MONTH ** _months)
        _lost = self.depth - _left
        self.depth = _left
        self.level = read_level(self.depth, self.generativity)
        return _lost

    def to_dict(self) -> dict[str, Any]:
        return {"topic": self.topic, "aliases": list(self.aliases),
                "depth": round(self.depth, 4),
                "generativity": round(self.generativity, 4),
                "level": int(self.level),
                "rings": [_r.to_dict() for _r in self.rings],
                "planted_from": self.planted_from,
                "created_ts": self.created_ts,
                "last_touched": self.last_touched}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MasteryTree":
        _t = cls(topic=str(d.get("topic", "")),
                 aliases=list(d.get("aliases", []) or []),
                 depth=float(d.get("depth", 0.0)),
                 generativity=float(d.get("generativity", 0.0)),
                 level=int(d.get("level", 0)),
                 planted_from=str(d.get("planted_from", "curiosity")),
                 created_ts=float(d.get("created_ts", 0.0) or time.time()),
                 last_touched=float(d.get("last_touched", 0.0) or time.time()))
        _t.rings = [Ring.from_dict(_r) for _r in (d.get("rings") or [])
                    if isinstance(_r, dict)]
        return _t


def _normalise(topic: str) -> str:
    """The key a topic is filed under.

    Separators are folded, so ``refund_handling``, ``refund-handling`` and
    ``Refund Handling`` are one subject rather than three unrelated trees.
    Fragmentation fails silently: each fragment looks like an agent that has
    barely learned anything, and nothing reports a problem.
    """
    _s = str(topic or "").replace("_", " ").replace("-", " ")
    return " ".join(_s.split()).strip().lower()


class Circulo:
    """The clearing: the registry of trees.

    Holds no I/O of its own. Serialise with :meth:`to_dict` and restore with
    :meth:`from_dict` wherever your architecture already persists things.
    """

    def __init__(self, felt_floor: float = RING_FELT_FLOOR):
        self._trees: dict[str, MasteryTree] = {}
        self._alias: dict[str, str] = {}
        self.felt_floor = float(felt_floor)
        # Called with the tree whenever it reaches a level it had not held.
        # Use it to hand the event to whatever else in your system should know.
        self.on_level_up: Optional[Callable[[MasteryTree], None]] = None

    # ── registry ────────────────────────────────────────────────────────────
    def plant(self, topic: str, planted_from: str = "curiosity",
              aliases: Optional[list[str]] = None) -> MasteryTree:
        _key = _normalise(topic)
        _existing = self.resolve(topic)
        if _existing is not None:
            return _existing
        _t = MasteryTree(topic=" ".join(str(topic).split()),
                         planted_from=planted_from)
        self._trees[_key] = _t
        self._add_aliases(_t, aliases or [])
        return _t

    def resolve(self, topic: str) -> Optional[MasteryTree]:
        _key = _normalise(topic)
        if _key in self._trees:
            return self._trees[_key]
        _target = self._alias.get(_key)
        return self._trees.get(_target) if _target else None

    def _add_aliases(self, tree: MasteryTree, aliases: list[str]) -> None:
        _key = _normalise(tree.topic)
        for _a in aliases:
            _na = _normalise(_a)
            if _na and _na != _key and _na not in self._alias:
                self._alias[_na] = _key
                if _a not in tree.aliases:
                    tree.aliases.append(_a)

    def trees(self) -> list[MasteryTree]:
        return list(self._trees.values())

    # ── the one operation that matters ──────────────────────────────────────
    def add_ring(self, topic: str, kind: str, evidence: str,
                 felt: dict[str, float], *,
                 planted_from: str = "responsibility",
                 aliases: Optional[list[str]] = None,
                 plant_if_absent: bool = True,
                 context: Optional[list] = None,
                 judged_by: str = "self",
                 event_id: str = "",
                 now: Optional[float] = None) -> dict[str, Any]:
        """Record evidence. A ring forms only if its felt verdict passes.

        The level is not unlocked: it is READ from (depth, generativity)
        after growth. Returns a report of what happened, including the
        reason when nothing did.
        """
        # AN UNKNOWN KIND IS REFUSED, not quietly given the study weight.
        # Evidence kinds are not equal, so guessing one is inventing meaning
        # where information is missing — and the guess would also make the
        # tree permanently unable to bear fruit through that path. Rejection
        # is visible in `reason`; a mis-weighted ring would not be.
        if kind not in _KIND_DEPTH_GAIN:
            log.warning("unknown evidence kind %r; nothing recorded. Known "
                        "kinds: %s", kind, ", ".join(sorted(_KIND_DEPTH_GAIN)))
            return {"ring_formed": False, "leveled_up": False, "level": -1,
                    "level_name": "", "composite": 0.0,
                    "reason": f"unknown evidence kind: {kind!r}"}

        _now = now if now is not None else time.time()
        tree = self.resolve(topic)
        if tree is None:
            if not plant_if_absent:
                return {"ring_formed": False, "leveled_up": False, "level": -1,
                        "level_name": "", "composite": 0.0,
                        "reason": "no such tree"}
            tree = self.plant(topic, planted_from=planted_from,
                              aliases=aliases)
        elif aliases:
            self._add_aliases(tree, aliases)

        ring = Ring(level_at_time=int(tree.level), kind=kind, ts=_now,
                    evidence=evidence or "", felt=dict(felt or {}),
                    context=list(context or []),
                    judged_by=str(judged_by or "self"),
                    event_id=str(event_id or ""))

        if not ring.passes_gate(self.felt_floor):
            # Nothing is recorded, not even the touch: hollow work must not
            # look like work, or dormancy would never arrive for a tree being
            # fed noise.
            return {"ring_formed": False, "leveled_up": False,
                    "level": int(tree.level), "level_name": tree.level_name,
                    "composite": round(ring.composite(), 3),
                    "reason": "hollow: did not pass the felt verdict"}

        tree.last_touched = _now      # only real rings water the tree
        tree.rings.append(ring)       # append-only, never trimmed

        _gain = _KIND_DEPTH_GAIN[kind]
        # Identity first when the caller has it, wording only as a fallback.
        # Compare against every EARLIER ring, not including this one.
        _eid = str(event_id or "").strip()
        _ev = str(evidence or "").strip()
        if _eid:
            _same = sum(1 for _r in tree.rings[:-1]
                        if str(getattr(_r, "event_id", "") or "").strip() == _eid)
            _how = "the same event"
        elif _ev:
            _same = sum(1 for _r in tree.rings[:-1]
                        if not getattr(_r, "event_id", "")
                        and str(getattr(_r, "evidence", "") or "").strip() == _ev)
            _how = "these exact words"
        else:
            _same, _how = 0, ""
        if _same:
            _gain *= REPEAT_DISCOUNT
            log.info("%r: already known via %s (%d times) - consolidates, "
                     "does not teach", tree.topic, _how, _same)

        # Diminishing returns: each ring moves what is LEFT to learn, so depth
        # approaches 1.0 without ever being handed it.
        tree.depth = min(1.0, tree.depth
                         + ring.composite() * _gain * (1.0 - tree.depth))

        _fulfils = ring.fulfilment()
        if _fulfils is not None:
            tree.generativity = min(1.0, tree.generativity
                                    + _fulfils * _GEN_FROM_MAKING
                                    * _GEN_KIND_MULT[kind]
                                    * (1.0 - tree.generativity))

        _prev = int(tree.level)
        tree.level = read_level(tree.depth, tree.generativity)
        _up = tree.level > _prev
        if _up and self.on_level_up is not None:
            try:
                self.on_level_up(tree)
            except Exception as _e:              # pragma: no cover - defensive
                log.warning("on_level_up hook failed: %s", _e)

        return {"ring_formed": True, "leveled_up": _up, "level": int(tree.level),
                "level_name": tree.level_name,
                "composite": round(ring.composite(), 3),
                "depth": round(tree.depth, 3),
                "generativity": round(tree.generativity, 3),
                "reason": ""}

    # ── forgetting ──────────────────────────────────────────────────────────
    def apply_forgetting(self, now: Optional[float] = None) -> dict[str, float]:
        """Let every dormant tree lose fluency. Returns what each one lost."""
        _lost = {}
        for _t in self._trees.values():
            _d = _t.apply_forgetting(now)
            if _d > 0:
                _lost[_t.topic] = round(_d, 4)
        return _lost

    # ── reading ─────────────────────────────────────────────────────────────
    def mastery_of(self, topic: str) -> Optional[dict[str, Any]]:
        """What this agent has actually earned here. ``None`` if never planted.

        ``None`` is not level zero. A subject never encountered and a subject
        encountered and not yet learned are different states, and collapsing
        them is how a system starts claiming competence it never had.
        """
        _t = self.resolve(topic)
        if _t is None:
            return None
        # `self_judged` belongs in the headline reading: a tree at CROWN whose
        # evidence is entirely self-judged and one judged by a test suite are
        # not the same claim.
        _n = len(_t.rings)
        _own = sum(1 for _r in _t.rings if _r.judged_by == "self")
        return {"topic": _t.topic, "level": int(_t.level),
                "level_name": _t.level_name, "depth": round(_t.depth, 3),
                "generativity": round(_t.generativity, 3),
                "rings": _n, "dormant": _t.is_dormant(),
                "kinds": sorted({_r.kind for _r in _t.rings}),
                "self_judged": round(_own / _n, 2) if _n else None,
                "judges": sorted({_r.judged_by for _r in _t.rings})}

    def can(self, topic: str, level: int = MasteryLevel.TRUNK) -> bool:
        """Has it earned at least this level here? False if never planted."""
        _t = self.resolve(topic)
        return _t is not None and int(_t.level) >= int(level)

    # ── persistence ─────────────────────────────────────────────────────────
    def to_dict(self) -> dict[str, Any]:
        return {"trees": [_t.to_dict() for _t in self._trees.values()],
                "aliases": dict(self._alias),
                "felt_floor": self.felt_floor}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Circulo":
        _c = cls(felt_floor=float(d.get("felt_floor", RING_FELT_FLOOR)))
        for _td in (d.get("trees") or []):
            if not isinstance(_td, dict):
                continue
            _t = MasteryTree.from_dict(_td)
            _c._trees[_normalise(_t.topic)] = _t
        _c._alias = {str(_k): str(_v)
                     for _k, _v in (d.get("aliases") or {}).items()}
        return _c
