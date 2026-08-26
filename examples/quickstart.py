# -*- coding: utf-8 -*-
"""Two agents, same number of sessions. One read; one built.

Run:  python examples/quickstart.py
"""
import json
import tempfile
import time
from pathlib import Path

from circulo import (DORMANCY_DAYS, KIND_CREATION, KIND_PRACTICE, KIND_STUDY,
                     Circulo)

_GOOD = {"projects": 0.8, "contributes": 0.75, "satisfies": 0.7,
         "fulfils": 0.8}


def _show(c, topic, label=""):
    _m = c.mastery_of(topic)
    if _m is None:
        print(f"  {label or topic:<22} -> None (never encountered)")
        return
    print(f"  {label or topic:<22} {_m['level_name']:<7} "
          f"depth {_m['depth']:.2f}  gen {_m['generativity']:.2f}  "
          f"rings {_m['rings']:>3}  kinds {','.join(_m['kinds'])}")


print("=" * 72)
print("Two agents. Thirty sessions each.")
print("=" * 72)

reader = Circulo()
builder = Circulo()
for _i in range(30):
    reader.add_ring("compilers", KIND_STUDY, f"read chapter {_i}", dict(_GOOD))
    builder.add_ring("compilers", KIND_CREATION, f"wrote pass {_i}",
                     dict(_GOOD))

_show(reader, "compilers", "only ever read")
_show(builder, "compilers", "actually built")
print("\n  Same effort, same felt quality. Only the builder can reach FRUIT:")
print("  generativity comes from making, and study multiplies it by zero.")

print()
print("=" * 72)
print("Hollow work records nothing at all")
print("=" * 72)
c = Circulo()
_r = c.add_ring("kubernetes", KIND_PRACTICE, "watched it fail, gave up",
                {"projects": 0.2, "contributes": 0.1, "satisfies": 0.1,
                 "fulfils": 0.1})
print(f"  ring_formed: {_r['ring_formed']}   composite: {_r['composite']}")
print(f"  reason     : {_r['reason']}")
_show(c, "kubernetes")
print("\n  Not even the timestamp moved. If hollow work watered the tree,")
print("  an agent fed noise would never go dormant and never forget.")

print()
print("=" * 72)
print("Repeating one fact is not learning it thirty times")
print("=" * 72)
_same, _diff = Circulo(), Circulo()
for _i in range(12):
    _same.add_ring("sql", KIND_STUDY, "joins exist", dict(_GOOD))
    _diff.add_ring("sql", KIND_STUDY, f"insight {_i}", dict(_GOOD))
_show(_same, "sql", "same evidence x12")
_show(_diff, "sql", "12 distinct pieces")

print()
print("=" * 72)
print("What is not practised is not lost, but it stops being fluent")
print("=" * 72)
_w = Circulo()
for _i in range(20):
    _w.add_ring("welsh", KIND_PRACTICE, f"conversation {_i}", dict(_GOOD))
_show(_w, "welsh", "after 20 sessions")

_a_year = time.time() + (DORMANCY_DAYS + 365) * 86400.0
_lost = _w.apply_forgetting(now=_a_year)
print(f"  a year of silence      lost {_lost['welsh']:.3f} depth")
_m = _w.mastery_of("welsh")
print(f"  {'now':<22} {_m['level_name']:<7} depth {_m['depth']:.2f}  "
      f"rings {_m['rings']:>3}   <- every ring still there")
print("\n  Fluency erodes; the record does not. Like a language you stop")
print("  speaking: the vocabulary is still in there, the ease is not.")

print()
print("=" * 72)
print("Never encountered is not level zero")
print("=" * 72)
print(f"  mastery_of('topology') -> {_w.mastery_of('topology')!r}")
print(f"  can('topology')        -> {_w.can('topology')}")
print("\n  A subject never met and a subject not yet learned are different.")

print()
print("=" * 72)
print("It is all plain JSON")
print("=" * 72)
_p = Path(tempfile.gettempdir()) / "circulo_quickstart.json"
_p.write_text(json.dumps(builder.to_dict()), encoding="utf-8")
_back = Circulo.from_dict(json.loads(_p.read_text(encoding="utf-8")))
_show(_back, "compilers", "restored from disk")
_p.unlink(missing_ok=True)
