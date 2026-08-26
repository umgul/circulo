# -*- coding: utf-8 -*-
"""The laws this package exists to enforce.

Each of these caught a real defect in the system circulo was extracted from.
They are kept as executable doctrine, not as coverage.
"""
import time
import unittest

from circulo import (DORMANCY_DAYS, KIND_CREATION, KIND_DISTILL,
                     KIND_PRACTICE, KIND_STUDY, Circulo, MasteryLevel, Ring,
                     read_level)

_GOOD = {"projects": 0.8, "contributes": 0.8, "satisfies": 0.8, "fulfils": 0.8}
_HOLLOW = {"projects": 0.1, "contributes": 0.1, "satisfies": 0.1,
           "fulfils": 0.1}


def _feed(c, topic, kind, n, felt=None, distinct=True):
    for _i in range(n):
        c.add_ring(topic, kind,
                   f"evidence {_i}" if distinct else "the same thing",
                   dict(felt or _GOOD))
    return c


class TestLevelIsReadNeverGranted(unittest.TestCase):

    def test_read_level_is_a_pure_function(self):
        self.assertEqual(read_level(0.0, 0.0), int(MasteryLevel.SPROUT))
        self.assertEqual(read_level(0.5, 0.0), int(MasteryLevel.TRUNK))
        self.assertEqual(read_level(0.9, 0.9), int(MasteryLevel.FRUIT))

    def test_depth_alone_never_reaches_fruit(self):
        """Reading forever must not make you an inventor."""
        self.assertEqual(read_level(1.0, 0.0), int(MasteryLevel.CROWN),
                         "reached FRUIT without ever having made anything")

    def test_studying_forever_stays_below_fruit(self):
        _c = _feed(Circulo(), "optics", KIND_STUDY, 200)
        _m = _c.mastery_of("optics")
        self.assertEqual(_m["generativity"], 0.0,
                         "study generated: then reading is indistinguishable "
                         "from making")
        self.assertLess(_m["level"], int(MasteryLevel.FRUIT))

    def test_creating_is_what_bears_fruit(self):
        _c = _feed(Circulo(), "optics", KIND_STUDY, 40)
        _feed(_c, "optics", KIND_CREATION, 40)
        self.assertEqual(_c.mastery_of("optics")["level"],
                         int(MasteryLevel.FRUIT))


class TestHollowWorkRecordsNothing(unittest.TestCase):

    def test_below_the_gate_no_ring_forms(self):
        _c = Circulo()
        _r = _c.add_ring("x", KIND_STUDY, "e", dict(_HOLLOW))
        self.assertFalse(_r["ring_formed"])
        self.assertEqual(_c.mastery_of("x")["rings"], 0)
        self.assertEqual(_c.mastery_of("x")["depth"], 0.0)

    def test_and_it_does_not_even_water_the_tree(self):
        """If hollow work refreshed last_touched, a tree fed noise would
        never go dormant and never forget."""
        _c = Circulo()
        _c.plant("x")
        _t = _c.resolve("x")
        _t.last_touched = 1000.0
        _c.add_ring("x", KIND_STUDY, "e", dict(_HOLLOW))
        self.assertEqual(_t.last_touched, 1000.0,
                         "hollow work watered the tree: noise now prevents "
                         "forgetting")

    def test_missing_components_are_not_zeros(self):
        """A caller reporting only what it can honestly read must not be
        penalised for the silence."""
        _full = Ring(0, KIND_STUDY, 0.0, "e", {"projects": 0.9})
        self.assertAlmostEqual(_full.composite(), 0.9, places=3)


class TestRepetitionConsolidatesButDoesNotTeach(unittest.TestCase):

    def test_the_same_evidence_is_discounted(self):
        _same = _feed(Circulo(), "a", KIND_STUDY, 12, distinct=False)
        _new = _feed(Circulo(), "a", KIND_STUDY, 12, distinct=True)
        self.assertLess(_same.mastery_of("a")["depth"],
                        _new.mastery_of("a")["depth"] * 0.6,
                        "resubmitting one fact reaches the same mastery as "
                        "twelve different ones")

    def test_the_first_time_is_not_discounted(self):
        _c = Circulo()
        _r = _c.add_ring("a", KIND_STUDY, "same", dict(_GOOD))
        self.assertGreater(_r["depth"], 0.0)


class TestTheSameEventIsTheSameEvent(unittest.TestCase):
    """The repeat check catches identical wording, which paraphrase defeats.
    When the caller knows the identity of the event, that is used instead."""

    def test_the_same_event_worded_differently_still_consolidates(self):
        _c = Circulo()
        for _i, _text in enumerate(("solved it with approach A",
                                    "successfully solved the problem via A",
                                    "resolved the problem, same strategy")):
            _c.add_ring("a", KIND_PRACTICE, _text, dict(_GOOD),
                        event_id="ticket-4471")
        _worded = Circulo()
        for _i, _text in enumerate(("solved it with approach A",
                                    "successfully solved the problem via A",
                                    "resolved the problem, same strategy")):
            _worded.add_ring("a", KIND_PRACTICE, _text, dict(_GOOD))
        self.assertLess(_c.mastery_of("a")["depth"],
                        _worded.mastery_of("a")["depth"] * 0.6,
                        "one event told three ways taught as much as three "
                        "different events")

    def test_different_events_still_teach(self):
        _c = Circulo()
        for _i in range(3):
            _c.add_ring("a", KIND_PRACTICE, "same words every time",
                        dict(_GOOD), event_id=f"ticket-{_i}")
        self.assertGreater(_c.mastery_of("a")["depth"], 0.3,
                           "three distinct events were discounted for sharing "
                           "a boilerplate description")

    def test_it_survives_persistence(self):
        import json
        _c = Circulo()
        _c.add_ring("a", KIND_PRACTICE, "e", dict(_GOOD), event_id="x-1")
        _back = Circulo.from_dict(json.loads(json.dumps(_c.to_dict())))
        self.assertEqual(_back.resolve("a").rings[0].event_id, "x-1",
                         "the event identity was lost on reload, so the same "
                         "event could teach twice after a restart")


class TestARingRecordsWhenItHappened(unittest.TestCase):
    """`level_at_time` is the level the TREE was at, not a grade for the ring."""

    def test_it_records_the_trees_level_not_its_own(self):
        _c = _feed(Circulo(), "a", KIND_CREATION, 30)
        _levels = [_r.level_at_time for _r in _c.resolve("a").rings]
        self.assertEqual(_levels, sorted(_levels),
                         "the recorded levels are not the tree's history")
        self.assertEqual(_levels[0], int(MasteryLevel.SPROUT))

    def test_an_old_file_still_loads(self):
        _r = Ring.from_dict({"level": 3, "kind": KIND_STUDY, "ts": 0.0,
                             "evidence": "e", "felt": {"fulfils": 0.9}})
        self.assertEqual(_r.level_at_time, 3,
                         "a file written before the rename lost its history")


class TestNonFiniteIsNotPerfect(unittest.TestCase):
    """`min(1.0, nan)` is 1.0 in CPython, so a NaN felt value scored as
    FLAWLESS evidence, levelled the tree up and handed it maximal
    generativity — the exact opposite of failing safe."""

    def test_a_nan_reading_is_ignored_not_scored_perfect(self):
        with self.assertLogs("circulo.core", level="WARNING"):
            _r = Ring(0, KIND_CREATION, 0.0, "e",
                      {"projects": float("nan"), "contributes": 0.6})
            _c = _r.composite()
        self.assertAlmostEqual(_c, 0.6, places=3,
                               msg=f"a NaN was scored, giving {_c}")

    def test_four_nans_build_no_ring_at_all(self):
        _nan = float("nan")
        _c = Circulo()
        with self.assertLogs("circulo.core", level="WARNING"):
            _r = _c.add_ring("hacking", KIND_CREATION, "e",
                             {"projects": _nan, "contributes": _nan,
                              "satisfies": _nan, "fulfils": _nan})
        self.assertFalse(_r["ring_formed"],
                         "four NaNs were recorded as flawless evidence")
        self.assertEqual(_r["composite"], 0.0)

    def test_and_generativity_is_untouched(self):
        _nan = float("nan")
        self.assertIsNone(
            Ring(0, KIND_CREATION, 0.0, "e", {"fulfils": _nan}).fulfilment(),
            "a NaN counted as maximal self-realisation")

    def test_infinity_is_ignored_too(self):
        """An infinity out of a division by zero is not «the maximum»; it is
        the absence of a reading. A finite 250.0 is a scale mistake and gets
        clamped; inf is not a number and gets dropped."""
        with self.assertLogs("circulo.core", level="WARNING"):
            _v = Ring(0, KIND_STUDY, 0.0, "e",
                      {"projects": float("inf"), "contributes": 0.4}).composite()
        self.assertAlmostEqual(_v, 0.4, places=3,
                               msg="an infinity was scored as maximal")

    def test_a_finite_out_of_range_value_is_still_clamped(self):
        with self.assertLogs("circulo.core", level="WARNING"):
            _v = Ring(0, KIND_STUDY, 0.0, "e", {"projects": 250.0}).composite()
        self.assertEqual(_v, 1.0, "the clamp for real scale mistakes was lost")


class TestUnusedMasteryDecays(unittest.TestCase):

    def test_a_dormant_tree_loses_fluency(self):
        _c = _feed(Circulo(), "welsh", KIND_PRACTICE, 20)
        _before = _c.mastery_of("welsh")["depth"]
        _future = time.time() + (DORMANCY_DAYS + 180) * 86400.0
        _c.apply_forgetting(now=_future)
        self.assertLess(_c.mastery_of("welsh")["depth"], _before,
                        "mastery only ever rises: that is a counter, not "
                        "learning")

    def test_but_the_rings_are_never_touched(self):
        """It happened. Fluency erodes; the record does not."""
        _c = _feed(Circulo(), "welsh", KIND_PRACTICE, 20)
        _n = _c.mastery_of("welsh")["rings"]
        _c.apply_forgetting(now=time.time() + 3650 * 86400.0)
        self.assertEqual(_c.mastery_of("welsh")["rings"], _n,
                         "forgetting deleted the evidence: that is not losing "
                         "fluency, it is losing the life")

    def test_nothing_is_lost_inside_the_grace_period(self):
        _c = _feed(Circulo(), "welsh", KIND_PRACTICE, 20)
        _before = _c.mastery_of("welsh")["depth"]
        _c.apply_forgetting(now=time.time() + (DORMANCY_DAYS - 1) * 86400.0)
        self.assertEqual(_c.mastery_of("welsh")["depth"], _before,
                         "penalised a pause shorter than the grace period")

    def test_the_level_follows_the_decay_down(self):
        _c = _feed(Circulo(), "welsh", KIND_PRACTICE, 30)
        _lvl = _c.mastery_of("welsh")["level"]
        _c.apply_forgetting(now=time.time() + 3650 * 86400.0)
        self.assertLess(_c.mastery_of("welsh")["level"], _lvl,
                        "depth fell and the label did not: the reading and "
                        "the continuum have drifted apart")


class TestSelfCertificationIsVisible(unittest.TestCase):
    """This package cannot stop an agent grading its own homework —
    verification belongs to the caller. What it refuses to do is let that be
    invisible."""

    def test_self_judged_is_reported(self):
        _c = _feed(Circulo(), "a", KIND_STUDY, 4)
        self.assertEqual(_c.mastery_of("a")["self_judged"], 1.0,
                         "a wholly self-graded tree does not say so: its "
                         "level reads like an external claim")

    def test_an_external_judge_is_recorded(self):
        _c = Circulo()
        _c.add_ring("a", KIND_PRACTICE, "e1", dict(_GOOD), judged_by="pytest")
        _c.add_ring("a", KIND_PRACTICE, "e2", dict(_GOOD))
        _m = _c.mastery_of("a")
        self.assertEqual(_m["self_judged"], 0.5)
        self.assertEqual(_m["judges"], ["pytest", "self"])

    def test_the_judge_survives_persistence(self):
        import json
        _c = Circulo()
        _c.add_ring("a", KIND_PRACTICE, "e", dict(_GOOD), judged_by="human")
        _back = Circulo.from_dict(json.loads(json.dumps(_c.to_dict())))
        self.assertEqual(_back.mastery_of("a")["judges"], ["human"],
                         "who judged was lost on reload: the audit trail only "
                         "lasts as long as the process")

    def test_no_rings_means_no_claim_either_way(self):
        _c = Circulo()
        _c.plant("a")
        self.assertIsNone(_c.mastery_of("a")["self_judged"],
                          "reported a self-judged ratio with no evidence at "
                          "all: 0/0 is not 0")


class TestOneSubjectIsOneTree(unittest.TestCase):
    """Silent fragmentation is the worst failure this class can have: each
    fragment looks like an agent that has barely learned anything, and
    nothing anywhere reports a problem."""

    def test_separators_do_not_fragment_a_subject(self):
        _c = Circulo()
        for _t in ("refund_handling", "refund-handling", "Refund Handling"):
            _c.add_ring(_t, KIND_PRACTICE, f"case via {_t}", dict(_GOOD))
        self.assertEqual(len(_c.trees()), 1,
                         f"one subject became {len(_c.trees())} trees: "
                         f"{[_t.topic for _t in _c.trees()]}")
        self.assertEqual(_c.mastery_of("refund handling")["rings"], 3)

    def test_aliases_join_genuinely_different_names(self):
        _c = Circulo()
        _c.plant("refund handling", aliases=["refunds", "chargebacks"])
        _c.add_ring("refunds", KIND_PRACTICE, "one case", dict(_GOOD))
        self.assertEqual(_c.mastery_of("chargebacks")["rings"], 1,
                         "aliases did not resolve to the same tree")


class TestFeltValuesOutsideRangeAreCaught(unittest.TestCase):

    def test_out_of_range_warns_rather_than_passing_silently(self):
        with self.assertLogs("circulo.core", level="WARNING") as _log:
            Ring(0, KIND_STUDY, 0.0, "e", {"projects": 87.0}).composite()
        self.assertTrue(any("outside [0, 1]" in _l for _l in _log.output),
                        "a 0-100 score passed as [0,1] produced a plausible "
                        "wrong number with nothing said")

    def test_and_the_composite_stays_in_range(self):
        _r = Ring(0, KIND_STUDY, 0.0, "e",
                  {"projects": 87.0, "contributes": -4.0})
        self.assertTrue(0.0 <= _r.composite() <= 1.0)


class TestAbsentFulfilmentIsNotZero(unittest.TestCase):
    """`composite` renormalises over what is present; `fulfilment` has to
    follow the same rule or the module contradicts itself."""

    def test_unmeasured_fulfilment_is_none(self):
        self.assertIsNone(
            Ring(0, KIND_PRACTICE, 0.0, "e", {"projects": 0.9}).fulfilment(),
            "an unmeasured reading came back as a measured zero")

    def test_and_it_produces_no_generativity(self):
        _c = Circulo()
        for _i in range(20):
            _c.add_ring("a", KIND_CREATION, f"e{_i}",
                        {"projects": 0.9, "contributes": 0.9,
                         "satisfies": 0.9})          # no `fulfils`
        self.assertEqual(_c.mastery_of("a")["generativity"], 0.0)

    def test_a_measured_zero_is_still_a_measurement(self):
        self.assertEqual(
            Ring(0, KIND_PRACTICE, 0.0, "e", {"fulfils": 0.0}).fulfilment(),
            0.0, "a real zero came back as «not measured»")


class TestNeverEncounteredIsNotLevelZero(unittest.TestCase):

    def test_unknown_topic_returns_none(self):
        self.assertIsNone(Circulo().mastery_of("nothing"),
                          "a subject never encountered reported as level 0: "
                          "that is claiming a competence baseline it never had")

    def test_can_is_false_for_the_unknown(self):
        self.assertFalse(Circulo().can("nothing"))

    def test_can_is_false_until_earned(self):
        _c = _feed(Circulo(), "a", KIND_STUDY, 1)
        self.assertFalse(_c.can("a", MasteryLevel.CROWN))


class TestDepthApproachesButIsNeverHanded(unittest.TestCase):

    def test_diminishing_returns(self):
        _c = Circulo()
        _first = _c.add_ring("a", KIND_STUDY, "e1", dict(_GOOD))["depth"]
        for _i in range(30):
            _c.add_ring("a", KIND_STUDY, f"x{_i}", dict(_GOOD))
        _last = _c.add_ring("a", KIND_STUDY, "final", dict(_GOOD))["depth"]
        _step = _last - _c.mastery_of("a")["depth"]
        self.assertLess(abs(_step), _first,
                        "later rings move depth as much as the first: there "
                        "are no diminishing returns")

    def test_depth_never_exceeds_one(self):
        _c = _feed(Circulo(), "a", KIND_CREATION, 300)
        self.assertLessEqual(_c.mastery_of("a")["depth"], 1.0)


class TestKindsAreNotEqual(unittest.TestCase):

    def test_creating_deepens_faster_than_studying(self):
        _s = _feed(Circulo(), "a", KIND_STUDY, 10)
        _m = _feed(Circulo(), "a", KIND_CREATION, 10)
        self.assertGreater(_m.mastery_of("a")["depth"],
                           _s.mastery_of("a")["depth"])

    def test_an_unregistered_kind_is_refused(self):
        """Guessing a weight for an unknown kind is inventing meaning where
        information is missing. Rejection is visible in `reason`; a
        mis-weighted ring would not be."""
        _c = Circulo()
        with self.assertLogs("circulo.core", level="WARNING"):
            _r = _c.add_ring("a", "improvised", "e", dict(_GOOD))
        self.assertFalse(_r["ring_formed"])
        self.assertIn("unknown evidence kind", _r["reason"])
        self.assertIsNone(_c.mastery_of("a"),
                          "refused the evidence but planted the tree anyway")

    def test_a_typo_does_not_quietly_become_a_new_kind(self):
        _c = _feed(Circulo(), "a", KIND_PRACTICE, 3)
        _before = _c.mastery_of("a")["depth"]
        _c.add_ring("a", "practise", "typo", dict(_GOOD))
        self.assertEqual(_c.mastery_of("a")["depth"], _before)
        self.assertEqual(_c.mastery_of("a")["kinds"], ["practice"])

    def test_distill_is_registered(self):
        with self.assertNoLogs("circulo.core", level="WARNING"):
            Circulo().add_ring("a", KIND_DISTILL, "e", dict(_GOOD))


class TestLevelUpHook(unittest.TestCase):

    def test_it_fires_once_per_new_level(self):
        _seen = []
        _c = Circulo()
        _c.on_level_up = lambda _t: _seen.append(int(_t.level))
        _feed(_c, "a", KIND_CREATION, 40)
        self.assertEqual(_seen, sorted(set(_seen)),
                         "a level fired twice or went backwards")
        self.assertTrue(_seen)

    def test_a_failing_hook_does_not_lose_the_ring(self):
        _c = Circulo()

        def _boom(_t):
            raise RuntimeError("downstream is down")

        _c.on_level_up = _boom
        _r = _feed(_c, "a", KIND_CREATION, 40).mastery_of("a")
        self.assertGreater(_r["rings"], 0,
                           "a broken downstream hook destroyed the learning "
                           "it was only supposed to be told about")


class TestItSurvivesPersistence(unittest.TestCase):

    def test_round_trip_keeps_everything(self):
        import json
        _c = _feed(Circulo(), "rust", KIND_PRACTICE, 12, )
        _c.plant("optics", aliases=["light"])
        _back = Circulo.from_dict(json.loads(json.dumps(_c.to_dict())))
        self.assertEqual(_back.mastery_of("rust"), _c.mastery_of("rust"))
        self.assertIsNotNone(_back.resolve("light"),
                            "aliases did not survive: the same subject would "
                            "grow two separate trees")


if __name__ == "__main__":
    unittest.main()
