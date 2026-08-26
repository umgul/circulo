# -*- coding: utf-8 -*-
"""Feeding circulo reliable data: a separate judge, and stable event identity.

circulo deliberately does not verify anything — the `felt` verdict comes from
the caller. That leaves you two jobs, and this file is the recipe for both.

    1. WHO JUDGES. If the same model call that did the work also rates it, the
       ratings inflate. Judge in a SECOND call, at low temperature, against a
       fixed rubric, given only the artefact and the goal — not the reasoning
       that produced it. Better still, judge from something observable: tests
       that passed, an error rate, whether the artefact still works next week.

    2. WHAT COUNTS AS THE SAME EVENT. The repeat discount falls back to
       comparing evidence text, and an agent paraphrases its own successes.
       Derive `event_id` from the ROOT GOAL of the task, not from the prose.

Run:  python examples/with_a_judge.py
"""
import hashlib
import json

from circulo import KIND_CREATION, KIND_STUDY, Circulo

# ── 1. Identity of the event ────────────────────────────────────────────────


def event_id_for(goal: str, attempt_of: str = "") -> str:
    """A stable id for the thing that happened.

    Hash the ROOT GOAL, not the description of what was done. Three retries at
    one goal are one event; the same words about two different goals are two.
    Add `attempt_of` only when repeated attempts should each count separately.
    """
    _seed = f"{goal.strip().lower()}|{attempt_of}"
    return hashlib.sha256(_seed.encode("utf-8")).hexdigest()[:16]


# ── 2. The judge ────────────────────────────────────────────────────────────

RUBRIC = """You are scoring one completed piece of work. You did not do it.
Score ONLY on the artefact and the goal. Return JSON with any of these keys
you can honestly assess, on a 0.0-1.0 scale, and OMIT any you cannot:

  projects     does this open onto further work, or is it a dead end?
  contributes  did it contribute beyond itself (someone used it, it unblocked
               something, it changed a decision)?
  satisfies    was the result satisfying on its own terms?
  fulfils      did doing this realise a capability, as opposed to executing a
               known routine? (the only component that feeds generativity;
               it is NOT what decides the evidence kind — the caller passes
               that separately)

Omitting a key is correct and costs nothing. Never invent a number to fill
the object. Return only the JSON."""


def judge_with_a_model(goal, artefact, evidence_of_outcome, client):
    """The second, low-temperature call. Not run here — it needs an API key.

    Two rules, whichever client you use:
      * it must not be the same call that produced `artefact`;
      * anything measurable should come from `evidence_of_outcome` rather
        than from the model's opinion.
    """
    reply = client.messages.create(
        model="claude-sonnet-4-5", temperature=0.0, max_tokens=300,
        system=RUBRIC,
        messages=[{"role": "user", "content":
                   json.dumps({"goal": goal, "artefact": artefact,
                               "outcome": evidence_of_outcome})}])
    return json.loads(reply.content[0].text)


def judge(goal: str, artefact: str, evidence_of_outcome: dict) -> dict:
    """What this example actually runs: no model at all.

    Every component here comes from something observable. That is the
    stronger option whenever it is available — a model judging is a fallback
    for what you cannot measure, not the default.
    """
    _felt = {}
    if "tests_passed" in evidence_of_outcome:
        _p, _t = evidence_of_outcome["tests_passed"]
        _felt["contributes"] = _p / _t if _t else 0.0
    if "was_reused" in evidence_of_outcome:
        _felt["projects"] = 0.9 if evidence_of_outcome["was_reused"] else 0.3
    if "novel_capability" in evidence_of_outcome:
        _felt["fulfils"] = 0.85 if evidence_of_outcome["novel_capability"] else 0.2
    # `satisfies` is deliberately absent: nothing here measures it, and
    # circulo renormalises over what is present.
    return _felt


# ── 3. The loop ─────────────────────────────────────────────────────────────

def record(c: Circulo, topic: str, goal: str, kind: str, artefact: str,
           outcome: dict, judged_by: str) -> dict:
    _felt = judge(goal, artefact, outcome)
    return c.add_ring(topic, kind, artefact[:200], _felt,
                      event_id=event_id_for(goal),
                      judged_by=judged_by)


if __name__ == "__main__":
    c = Circulo()

    print("Three attempts at ONE goal, worded differently each time:")
    for _attempt in ("wrote the tokenizer",
                     "implemented tokenization for the parser",
                     "finished the tokenizer module"):
        _r = record(c, "parsing", goal="build a tokenizer for the DSL",
                    kind=KIND_CREATION, artefact=_attempt,
                    outcome={"tests_passed": (18, 20), "was_reused": True,
                             "novel_capability": True},
                    judged_by="pytest+reuse")
        print(f"   {_attempt[:40]:42s} ring={_r['ring_formed']} "
              f"depth={_r.get('depth', 0):.3f}")
    print("   -> one event, three wordings: consolidated, not learned thrice.")

    print("\nA genuinely different goal:")
    _r = record(c, "parsing", goal="add error recovery to the parser",
                kind=KIND_CREATION, artefact="parser now resyncs on bad input",
                outcome={"tests_passed": (20, 20), "was_reused": True,
                         "novel_capability": True},
                judged_by="pytest+reuse")
    print(f"   depth={_r['depth']:.3f}  (moved: it is a different event)")

    print("\nSomething it only read about:")
    _r = record(c, "parsing", goal="read the Earley parsing chapter",
                kind=KIND_STUDY, artefact="read about Earley parsing",
                outcome={"was_reused": False},
                judged_by="self")
    print(f"   ring={_r['ring_formed']}  reason={_r['reason'] or '-'}")

    print("\nWhat it has earned, and on whose word:")
    print("  ", json.dumps(c.mastery_of("parsing"), indent=None))
    print("\n  `self_judged` is the number to watch. Here it is 0.0: every\n   ring that formed was judged by test outcomes, not by the agent's\n   opinion of itself. The one it only read about never formed.")

    print("\n  Nothing above called a model: every component came from an\n   observable outcome. `RUBRIC` + `judge_with_a_model()` are there for\n   what you cannot measure — a fallback, not the default.")

    print("\nForgetting is not automatic — sweep on startup:")
    print("  ", c.apply_forgetting() or "(nothing dormant yet)")
