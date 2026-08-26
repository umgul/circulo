---
name: circulo
description: Track what an agent has actually learned as skill trees it must earn and can lose, with mastery read from accumulated evidence rather than granted. Use when building agent skill libraries, memory of competence, self-improvement loops, curriculum or capability gating, when deciding whether an agent is qualified to attempt something, or when a system's claimed abilities need to reflect demonstrated work rather than stored labels.
---

# circulo — skill trees an agent earns, and can lose

Most agent memories record what happened. This records what an agent has
become good at, as something it has to earn and can lose.

It does **not** verify anything — see "What this does not do" at the end,
which matters more than the API.

## When to reach for this

- Building a skill library, capability registry, or "what has this agent
  learned" memory.
- A self-improvement loop needs to know whether it is getting better.
- Deciding whether an agent is qualified to attempt something.
- A system claims competence from a stored label rather than from work.
- Tracking progress across sessions where some skills go unused.

## Install

```bash
pip install git+https://github.com/umgul/circulo.git
```

## The whole API

```python
from circulo import Circulo, KIND_STUDY, KIND_PRACTICE, KIND_CREATION, KIND_DISTILL

c = Circulo()

c.add_ring("rust", KIND_PRACTICE, "shipped the parser",
           {"projects": 0.8, "contributes": 0.7,      # each on [0, 1]
            "satisfies": 0.6, "fulfils": 0.9},
           judged_by="pytest")                        # who judged. See rule 7.

c.plant("rust", aliases=["rustlang", "rust-lang"])    # same subject, one tree

c.mastery_of("rust")          # dict, or None if never encountered
c.can("rust")                 # bool: has it earned at least TRUNK here?
c.apply_forgetting()          # dormant trees lose fluency
c.to_dict() / Circulo.from_dict(d)      # plain JSON
```

Levels, low to high: `SPROUT → ROOTS → TRUNK → CROWN → FRUIT`.

## The model in one paragraph

Each subject is a tree with two continuous quantities: **depth** (how much it
has taken in) and **generativity** (how much it has made). The `level` is a
*reading* of those two, recomputed after every piece of evidence. Nothing
unlocks; you cannot promote a tree. `FRUIT` is the only level that requires
generativity, and generativity only comes from making things — so an agent
that only ever studies can approach maximum depth and still never bear fruit.

## How to record evidence

Pick the kind honestly:

| Kind | Means | Feeds generativity |
|---|---|---|
| `KIND_STUDY` | took something in | no |
| `KIND_PRACTICE` | applied it | partly |
| `KIND_CREATION` | made something that did not exist | fully |
| `KIND_DISTILL` | compressed many encounters into one insight | partly |

Fill `felt` from whatever you can honestly measure — a verifier result, test
outcome, user reaction, self-assessment:

```python
{"projects": 0.8,      # does it open onto more?
 "contributes": 0.7,   # did it contribute beyond itself?
 "satisfies": 0.6,     # was it satisfying?
 "fulfils": 0.9}       # was it self-realising? (the only one feeding generativity)
```

**Omit what you cannot measure.** Missing components are not zeros — the
weights renormalise over what is present, and an omitted `fulfils` means *no
generative evidence* rather than zero. Never fabricate a value to fill the
dict; that is exactly the failure this package exists to prevent.

## Rules to follow when writing code with this

**1. Never write to `depth`, `generativity`, or `level` directly.** They are
outputs. If you are tempted to set them, you want `add_ring` with real
evidence, or you have a design problem.

**2. `mastery_of` returning `None` is not level zero.** Never encountered and
encountered-but-not-learned are different states:

```python
_m = c.mastery_of(topic)
if _m is None:
    ...        # it has never met this. Not "it is bad at this."
```

**3. Check `ring_formed` in the result.** A hollow verdict records nothing and
tells you why in `reason`. Silently ignoring that means your caller thinks it
taught something it did not.

**4. Pass `event_id` when you know it; do not resubmit one event as several.**
Repeated evidence is discounted to a quarter, but the fallback check compares
the evidence TEXT, which paraphrase defeats — three re-wordings of one
success would teach as much as three real successes. If the caller has an
identity for the event (a ticket, a commit, a run id), pass it:

```python
c.add_ring("parsing", KIND_PRACTICE, "shipped it", felt,
           event_id="run-8812")
```

**5. Call `apply_forgetting()` somewhere real** — startup, a daily job, before
reporting. It is not automatic, so a system that never calls it never forgets,
which is the behaviour this package was built to fix.

**6. One subject, one tree — use `plant(topic, aliases=[...])`.** Topic keys
fold case and separators, so `refund_handling`, `refund-handling` and
`Refund Handling` are already one subject. Genuinely different NAMES for the
same thing (`rust` / `rustlang`) need aliases. Silent fragmentation is the
worst failure here: each fragment looks like an agent that has barely learned
anything, and nothing reports a problem.

**7. Pass `judged_by` whenever something other than the agent judged.** It
defaults to `"self"`, which is honest and is the weakest evidence there is. If
a test suite, a benchmark or a human produced the verdict, say so — then
`mastery_of()["self_judged"]` becomes a number someone can look at. An agent
that only ever grades its own homework should be visibly doing so.

**8. `felt` components are on `[0, 1]`, and must be real numbers.** A finite
out-of-range value (250.0) is clamped with a warning. A `NaN` or `inf` is
DROPPED like an absent component, not clamped — `min(1.0, nan)` is `1.0` in
CPython, so clamping would score an uninitialised float as flawless evidence.
Never fabricate a component to fill the dict — omit it instead; weights
renormalise over what is present.

**9. Only the four kinds exist.** Anything else is REFUSED: nothing is
recorded and `reason` says so. A typo (`"practise"`) loses that evidence
rather than mis-weighting it. If a project genuinely needs a fifth kind, add
it to both weight tables in `core.py`; do not pass a new string.

## Judge in a second call

If the same model call that did the work also fills in `felt`, the ratings
inflate. Use a separate low-temperature call given only the goal and the
artefact — not the reasoning that produced it — and tell it that omitting a
component it cannot assess is correct. Better: derive components from
observable outcomes (tests passed, error rate, whether it was reused) and
pass `judged_by` accordingly. `examples/with_a_judge.py` is a runnable
recipe.

## Deciding whether to attempt something

```python
from circulo import MasteryLevel

if c.can("cryptography", MasteryLevel.CROWN):
    do_it_directly()
elif c.mastery_of("cryptography") is None:
    study_first()
else:
    do_it_with_review()
```

## Telling the rest of the system

```python
c.on_level_up = lambda tree: notify(f"{tree.topic} reached {tree.level_name}")
```

A hook that raises is logged and swallowed: a broken downstream must never
destroy the learning it was only supposed to be told about.

## What this does not do

It does not verify anything itself. It has no idea whether an attempt actually
succeeded — that is the caller's job, and the `felt` dict is where that
judgement enters. Fabricate those numbers and the tree is decoration. Feed it
a real verifier's output and it becomes a record of demonstrated work.

It also cannot break the self-certification loop (agent does X, agent judges X,
mastery rises). It only makes that loop **visible**, through `judged_by` and
`self_judged`. Wherever an observable outcome exists — a test result, an error
rate, whether the artifact still works next week, what a human said — use it
instead of the agent's own opinion.

The repeat discount catches identical evidence strings only; paraphrase defeats
it. If evidence is machine-generated, pass a stable signature rather than prose.
