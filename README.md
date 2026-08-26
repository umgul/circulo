# circulo

**Skill trees an agent has to earn — and can lose.**

Most agent memories record what happened. This records what an agent has
become *good at*, as something it has to earn and can lose.

It does **not** verify anything itself — see [What this cannot do](#what-this-cannot-do),
which is the first thing worth reading.

No dependencies. No I/O. Serialise it into whatever you already persist.

```bash
pip install git+https://github.com/umgul/circulo.git
```

```python
from circulo import Circulo, KIND_STUDY, KIND_PRACTICE, KIND_CREATION

c = Circulo()

c.add_ring("rust", KIND_STUDY, "read the ownership chapter",
           {"projects": 0.7, "contributes": 0.6, "fulfils": 0.4})

c.mastery_of("rust")
# {'topic': 'rust', 'level': 0, 'level_name': 'SPROUT', 'depth': 0.089,
#  'generativity': 0.0, 'rings': 1, 'dormant': False, 'kinds': ['study'],
#  'self_judged': 1.0, 'judges': ['self']}

c.can("rust")          # False — one chapter is not competence

# ...eight sessions of actually building with it later:
c.mastery_of("rust")
# {'topic': 'rust', 'level': 3, 'level_name': 'CROWN', 'depth': 0.759,
#  'generativity': 0.387, 'rings': 9, 'dormant': False,
#  'kinds': ['practice', 'study'], 'self_judged': 1.0, 'judges': ['self']}
```

Every output in this README is copied from a real run, not typed by hand.

---

## The problem

Agent "skill libraries" usually work like this: the agent does something, it
works, the skill is stored, and from then on the agent *has* that skill.
Forever. At full strength. Regardless of whether it ever does it again.

Three things are wrong with that.

**Competence is claimed, not demonstrated.** If the code that stores the skill
also decides what level it is, then the level means whatever that code says.
There is no fact of the matter to be wrong about.

**All evidence counts the same.** Reading about distributed systems, running
one, and designing a new one are recorded identically. So an agent that has
only ever read reports the same competence as one that has built.

**Nothing is ever lost.** A learning curve that only rises is not learning. It
is a counter with an aspirational name.

## The idea

A tree per subject. Two continuous quantities — **depth** and
**generativity** — that evidence moves. `level` is a *reading* of those two,
recomputed after every change.

Nothing unlocks. You cannot promote a tree. You can only give it evidence and
see where it lands.

```
SPROUT → ROOTS → TRUNK → CROWN → FRUIT
```

`FRUIT` is the only level with a generativity requirement, and generativity
only comes from making things. **You cannot read your way to it**, however
much you read — which is the behaviour you want and almost never get.

---

## Five rules, and why each exists

### 1. Level is read, never granted

```python
from circulo import read_level

read_level(depth=1.0, generativity=0.0)   # -> CROWN, not FRUIT
```

A pure function of two numbers. No state, no gate, no unlock. If you want to
know why an agent is at a level, you can compute it yourself.

### 2. Evidence has kinds, and they are not equal

| Kind | Depth gain | Generativity |
|---|---|---|
| `KIND_STUDY` | 0.16 | ×0.0 — understanding does not generate |
| `KIND_PRACTICE` | 0.20 | ×0.30 |
| `KIND_CREATION` | 0.26 | ×1.0 |
| `KIND_DISTILL` | 0.16 | ×0.30 — compressing many encounters into one insight |

An unregistered kind is **refused**: nothing is recorded and the returned
`reason` says why. Guessing a weight for an unknown kind would invent
meaning where information is missing, and the guess would also leave the
tree permanently unable to bear fruit through that path.

### 3. A ring must be *felt* to count

Every piece of evidence carries a subjective reading:

```python
{"projects": 0.8,     # did it project forward — does it open onto more?
 "contributes": 0.7,  # did it contribute to something beyond itself?
 "satisfies": 0.6,    # was it satisfying?
 "fulfils": 0.9}      # was it self-realising? (the only one feeding generativity)
```

Every component is on `[0, 1]`. Out-of-range values are clamped **with a
warning** rather than silently — a 0–100 score passed in by mistake would
otherwise produce a plausible-looking wrong number.

Below the gate (`0.50` composite), **nothing is recorded**: no ring, no depth,
not even a refresh of the timestamp. That last part matters more than it
looks — if hollow work watered the tree, an agent being fed noise would never
go dormant and never forget.

Components you omit are **not zeros**. The weights renormalise over what is
actually present, so a caller reporting only what it can honestly read is not
punished for the silence. That applies to `fulfils` too: omitting it means
*no generative evidence*, which is not the same as a measured zero.

Where do these numbers come from? Whatever you can honestly measure: a
verifier's result, test coverage, a user's reaction, a self-assessment. The
package does not care — it cares that you do not fabricate them.

### 4. Repetition consolidates; it does not teach

Identical evidence is discounted to a quarter.

```python
for _ in range(12):
    c.add_ring("a", KIND_STUDY, "the same thing", felt)   # depth: 0.13
# versus twelve distinct pieces of evidence                # depth: 0.53
```

Without this, a loop that re-submits one success reaches mastery on one fact.

### 5. Unused mastery decays

```python
c.apply_forgetting()      # call it on a schedule, or at startup
# {'welsh': 0.0812}       # what each dormant tree lost
```

After a 30-day grace period, dormant trees lose 10% of their depth per month.
What erodes is **fluency, not memory**: the rings are never touched — they
happened, they stay — exactly like a language you stop speaking. The
vocabulary is still in there. The ease is not.

---

## `None` is not level zero

```python
Circulo().mastery_of("quantum chromodynamics")   # -> None
```

A subject never encountered and a subject encountered but not yet learned are
different states. Collapsing them is how a system starts claiming a competence
baseline it never had.

---

## API

| Method | Purpose |
|---|---|
| `add_ring(topic, kind, evidence, felt, judged_by="self", **kw)` | The one operation that matters. Returns a report including `reason` when nothing happened |
| `mastery_of(topic)` | What was actually earned, incl. `self_judged` and `judges`. `None` if never planted |
| `can(topic, level=TRUNK)` | Has it earned at least this? `False` if never planted |
| `plant(topic, planted_from, aliases)` | Register a subject without evidence |
| `resolve(topic)` | The tree, following aliases |
| `apply_forgetting(now=None)` | Let dormant trees lose fluency |
| `trees()` | All of them |
| `to_dict()` / `from_dict(d)` | Persistence, JSON-safe |

`FELT_WEIGHTS`, `RING_FELT_FLOOR` and `DORMANCY_DAYS` are public and importable if you want to read the weights rather than guess them.

**`on_level_up`** is a hook called with the tree whenever it reaches a level it
had not held — use it to tell the rest of your system. A hook that raises is
logged and swallowed: a broken downstream must never destroy the learning it
was only supposed to be told about.

---

## Use as a Claude skill

`skills/circulo/SKILL.md` is ready to use. Copy it into `.claude/skills/circulo/`
in your project (or `~/.claude/skills/circulo/` for every project) and Claude
will reach for it when a task involves tracking what an agent has learned or
deciding whether it is qualified for something.

## Use as a module

No dependencies, no I/O, no threads. Everything serialises to plain JSON:

```python
c = Circulo.from_dict(json.load(open("mastery.json")))
c.add_ring(...)
json.dump(c.to_dict(), open("mastery.json", "w"))
```

Pairs naturally with any agent loop that already has a verifier: whatever tells
you an attempt succeeded is what should be filling in `felt`.

### Running from a clone

There is no build step, but Python has to be told where the package is:

```bash
git clone https://github.com/umgul/circulo.git
cd circulo
PYTHONPATH=src python examples/quickstart.py
PYTHONPATH=src python -m pytest

# PowerShell:
#   $env:PYTHONPATH = "src"; python examples/quickstart.py
# cmd.exe:
#   set PYTHONPATH=src && python examples/quickstart.py
```

(`pytest` alone also works — `pyproject.toml` sets its path — but the example
script does not get that.)

See `examples/quickstart.py` for a runnable end-to-end example.

---

## Feeding it reliable data

circulo does not verify anything, so the quality of a tree is the quality of
what you put in. Three jobs are yours, and `examples/with_a_judge.py` is a
runnable recipe for the first two.

**Judge in a second call, not the one that did the work.** A model rating its
own output in the same breath inflates. Use a separate low-temperature call
given only the goal and the artefact — not the reasoning that produced it —
against a fixed rubric, and tell it that omitting a component it cannot assess
is correct and costs nothing. Better still, judge from something observable:
tests that passed, an error rate, whether the artefact was reused, whether it
still works next week. Then `judged_by` stops being `"self"` and
`self_judged` becomes a number worth reading.

**Derive `event_id` from the root goal, not from the prose.**

```python
def event_id_for(goal: str) -> str:
    return hashlib.sha256(goal.strip().lower().encode()).hexdigest()[:16]
```

Three retries at one goal are one event, however differently each is worded;
the same words about two different goals are two events. If you want semantic
matching between *different* goals, that is a vector search on your side — do
it before calling, and pass the id of whatever you matched.

**Sweep for forgetting when the agent wakes.** `apply_forgetting()` is not
automatic and nothing calls it for you. A reactive agent that only runs on a
prompt will never decay anything unless you call it at startup, or on a
schedule.

## What this cannot do

**It cannot stop an agent grading its own homework.** The `felt` verdict comes
from whoever calls `add_ring`. If that is the same model that did the work,
you have a closed loop:

```
agent does X  ->  agent judges X  ->  mastery rises  ->  agent trusts its mastery
```

This package will not pretend to solve that — verification belongs to the
caller, and a verifier bolted inside would just be one more thing grading
itself. What it refuses to do is let the loop be **invisible**:

```python
c.add_ring("parsing", KIND_PRACTICE, "shipped it",
           felt, judged_by="pytest")          # or "human-review", "benchmark"

c.mastery_of("parsing")["self_judged"]        # 0.5
c.mastery_of("parsing")["judges"]             # ['pytest', 'self']
```

`judged_by` defaults to `"self"`, which is honest and is also the weakest
evidence there is. A tree at CROWN with `self_judged: 1.0` and one judged by a
test suite are not the same claim, so `self_judged` is part of the headline
reading rather than a detail you have to go looking for.

**Feed it observable outcomes wherever you can.** Test results, latency,
error rates, whether an artifact still works a week later, what a human said.
The `felt` dict is where external signal enters — that is its purpose, not
self-report.

**A `NaN` felt value used to score as PERFECT.** `min(1.0, nan)` is `1.0` in
CPython, so four NaNs — an ordinary result of a `0/0` upstream — built a
flawless ring, levelled the tree up and handed it maximal generativity. Now a
value that is not a number is dropped like an absent one, with a warning. An
`inf` goes the same way: an infinity out of a division by zero is not «the
maximum», it is the absence of a reading. A finite 250.0 is a scale mistake
and is still clamped.

**The repeat discount catches identical strings, and paraphrase defeats it:**

```python
"solved it with approach A"
"successfully solved the problem using method A"     # counts as new evidence
```

Semantic deduplication needs embeddings, and this package has no dependencies
on purpose. So when you know the identity of the event, say so:

```python
c.add_ring("a", KIND_PRACTICE, "solved it with approach A", felt,
           event_id="ticket-4471")
```

Same `event_id` means the same thing happened twice, however differently it
was worded. Deciding whether two *different* events mean the same is
semantics, and semantics stays the caller's business.

**`generativity` does not decay, and that is a decision.** Depth erodes with
disuse; what has been *made* does not. So `FRUIT` means «this has created
something», not «this is still able to create» — a creation that happened
does not stop having happened after a year. If you need the second meaning,
generativity needs a currency dimension of its own; the piece to add is a
fluency term beside it, not a decay on the record.

**`depth` is not a memory count.** It is integrated, currently-available
mastery: it grows with evidence and *decays with disuse*. The rings are the
memory and they never decay. A cleaner model would separate the two — a
`depth` that only ever accumulates and a `fluency` that erodes — so a tree
could say *"I learned this deeply eight months ago and cannot use it smoothly
now."* That split is the main thing 0.2.0 should do; today one number carries
both jobs, and this paragraph exists so the naming does not mislead you.

## Prior art, honestly

The closest relative is **Voyager** (Wang et al., 2023), which built a skill
library in Minecraft from verified successes. `circulo` shares the core
instinct — skills are earned by demonstrated success, not declared — and
differs in four ways:

- mastery is **read** from the accumulated evidence rather than being a
  membership test;
- evidence **kinds** carry different weight, so studying and building are not
  the same act;
- unused mastery **decays**, which is rare in agent systems and is the part
  most likely to change your behaviour;
- repeated identical evidence is **discounted**, so loops cannot farm it.

If you know of work that already does the decay part well, open an issue — it
is the piece we would most like to compare against.

## Origin

Extracted from **SGICP**, a computational-phenomenology architecture built
between 2025 and 2026, where it is the organ that answers "what has this
system actually learned, as opposed to what has it been told?"

In that system the gate floor is not a constant but is itself calibrated
against the agent's own history of felt verdicts. Here it is a constructor
argument (`felt_floor`), so you can supply your own — including from `varas`,
its companion package.

### Using them together

They share no code and no vocabulary on purpose, so the glue is yours. Two
things worth knowing before you write it.

**A varas channel and a circulo topic are different things.** A channel is a
quantity you observe repeatedly (`latency`, `retries`, `tokens`). A topic is a
subject you get better at (`sql-optimisation`, `rust`). Naming them alike will
tempt you to pipe one into the other, and that is the mistake below.

**Do not feed a varas signal into `felt`.** It is tempting: `is_unusual()`
returns something in the right shape. But `felt` asks how good the work was,
and `is_unusual()` answers whether a number was rare for this agent. A latency
of 0.43s on a very tight channel reads as unusual and says nothing about the
quality of what was done — wire it in and your mastery tree starts tracking
your own variance.

The honest use of the pair is sequential, not nested:

```python
# varas decides whether this is worth a second look
if is_unusual(state, "task_latency", elapsed) is True:
    log_for_review(task)

# circulo records what was learned, judged on its own terms
if tests_passed:
    circulo.add_ring("sql-optimisation", KIND_PRACTICE, summary,
                     felt_from_outcome(test_report),
                     event_id=event_id_for(goal), judged_by="pytest")
```

One says *this moment was unusual for me*. The other says *this made me
better at something*. They are both about the agent, and they are not the
same sentence.

## Contributing

The tests are the doctrine. `tests/test_circulo.py` is not coverage — each
test is a defect that actually happened, kept executable. If you change
behaviour, change the law that describes it and say what you measured.

```bash
python -m pytest
```

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
