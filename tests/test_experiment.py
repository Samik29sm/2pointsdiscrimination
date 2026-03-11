"""Unit tests for experiment.py logic."""

import pytest
from experiment import ExperimentSession, Trial


# ---------------------------------------------------------------------------
# Trial
# ---------------------------------------------------------------------------

class TestTrial:
    def test_to_dict_experimental(self):
        t = Trial(1, "experimental", 5.0, stimulus_count=2)
        t.response = "2"
        d = t.to_dict()
        assert d["trial_number"] == 1
        assert d["trial_type"] == "experimental"
        assert d["distance_mm"] == 5.0
        assert d["stimulus_applied"] == 2
        assert d["response"] == "2"
        assert d["correct"] is None

    def test_to_dict_control_correct(self):
        t = Trial(3, "control", None, stimulus_count=1)
        t.response = "1"
        d = t.to_dict()
        assert d["distance_mm"] == "CT"
        assert d["correct"] is True

    def test_to_dict_control_incorrect(self):
        t = Trial(3, "control", None, stimulus_count=1)
        t.response = "2"
        d = t.to_dict()
        assert d["correct"] is False


# ---------------------------------------------------------------------------
# ExperimentSession – basic setup
# ---------------------------------------------------------------------------

class TestSessionSetup:
    def _session(self, distances=None):
        if distances is None:
            distances = [2, 4, 6, 8, 10]
        return ExperimentSession("P01", "Fingertip", distances)

    def test_distances_sorted_ascending(self):
        s = self._session([10, 4, 2, 8, 6])
        assert s.distances == [2.0, 4.0, 6.0, 8.0, 10.0]

    def test_distances_deduplicated(self):
        s = self._session([5, 5, 10, 10])
        assert s.distances == [5.0, 10.0]

    def test_starts_at_max_distance(self):
        s = self._session([2, 4, 6, 8, 10])
        assert s.current_distance == 10.0

    def test_requires_at_least_one_distance(self):
        with pytest.raises(ValueError):
            ExperimentSession("P01", "Fingertip", [])

    def test_initial_state(self):
        s = self._session()
        assert not s.done
        assert s.threshold is None
        assert s.trials == []


# ---------------------------------------------------------------------------
# ExperimentSession – staircase
# ---------------------------------------------------------------------------

class TestStaircase:
    def _session(self):
        # distances [2,4,6,8,10] → index 4 = 10mm at start
        return ExperimentSession("P01", "Fingertip", [2, 4, 6, 8, 10])

    def test_two_points_moves_down(self):
        s = self._session()
        s._ct_trial_numbers = set()
        s._pending_ct = 0
        # start at 10mm
        s.record_response("2")
        assert s.current_distance == 8.0

    def test_one_point_moves_up(self):
        s = self._session()
        s._ct_trial_numbers = set()
        s._pending_ct = 0
        s.record_response("2")  # 10→8
        s.record_response("2")  # 8→6
        s.record_response("1")  # 6→8
        assert s.current_distance == 8.0

    def test_three_reversals_terminates(self):
        s = self._session()
        s._ct_trial_numbers = set()
        s._pending_ct = 0

        s.record_response("2")  # 10→8
        s.record_response("2")  # 8→6
        s.record_response("2")  # 6→4
        assert s.current_distance == 4.0

        # first reversal at 4mm
        s.record_response("1")  # 4mm rev 1 → move to 6
        assert s.single_point_counts.get(4.0) == 1
        s.record_response("2")  # 6→4

        # second reversal at 4mm
        s.record_response("1")  # 4mm rev 2 → move to 6
        assert s.single_point_counts.get(4.0) == 2
        s.record_response("2")  # 6→4

        # third reversal at 4mm → done
        s.record_response("1")  # 4mm rev 3
        assert s.done
        assert s.threshold == 6.0  # next-higher distance above 4mm

    def test_threshold_at_max_distance(self):
        s = ExperimentSession("P01", "Loc", [5.0])
        s._ct_trial_numbers = set()
        s._pending_ct = 0
        # Only one distance – 3 reversals at 5mm
        for _ in range(3):
            s.record_response("1")
        assert s.done
        assert s.threshold == 5.0  # no higher distance available

    def test_responses_after_done_ignored(self):
        s = self._session()
        s._ct_trial_numbers = set()
        s._pending_ct = 0
        s.done = True
        count_before = len(s.trials)
        s.record_response("2")
        assert len(s.trials) == count_before

    def test_add_distance(self):
        s = self._session()
        s.add_distance(3.0)
        assert 3.0 in s.distances
        assert s.distances == sorted(s.distances)

    def test_add_duplicate_distance_noop(self):
        s = self._session()
        original = list(s.distances)
        s.add_distance(4.0)
        assert s.distances == original

    def test_custom_distance_used(self):
        s = self._session()
        s._ct_trial_numbers = set()
        s._pending_ct = 0
        s.record_response("2", custom_distance=9.0)
        # 9mm added to list and recorded
        assert 9.0 in s.distances
        assert s.trials[-1].distance == 9.0

    def test_floor_clamping(self):
        s = self._session()
        s._ct_trial_numbers = set()
        s._pending_ct = 0
        # Move down to minimum
        for _ in range(10):
            s.record_response("2")
        assert s.current_distance == s.distances[0]


# ---------------------------------------------------------------------------
# ExperimentSession – control trials
# ---------------------------------------------------------------------------

class TestControlTrials:
    def test_control_trial_recorded(self):
        s = ExperimentSession("P01", "Fingertip", [2, 4, 6, 8, 10])
        # Force a CT at trial 1 for predictability
        s._ct_trial_numbers = {1}
        s._pending_ct = 1
        s.record_response("1")
        assert s.trials[0].trial_type == "control"
        assert s.trials[0].distance is None
        assert s.trials[0].stimulus_count == 1

    def test_two_control_trials_per_session(self):
        s = ExperimentSession("P01", "Fingertip", [2, 4, 6, 8, 10])
        assert s._pending_ct == 2

    def test_ct_count_decrements(self):
        s = ExperimentSession("P01", "Fingertip", [2, 4, 6, 8, 10])
        s._ct_trial_numbers = {1, 2}
        s._pending_ct = 2
        s.record_response("1")
        assert s._pending_ct == 1
        s.record_response("2")
        assert s._pending_ct == 0


# ---------------------------------------------------------------------------
# ExperimentSession – summary
# ---------------------------------------------------------------------------

class TestSummary:
    def test_summary_contains_expected_keys(self):
        s = ExperimentSession("P01", "Fingertip", [2, 4, 6, 8, 10])
        summary = s.get_summary()
        for key in ("participant_id", "location", "threshold_mm",
                    "total_trials", "experimental_trials",
                    "control_trials", "control_trials_correct",
                    "responses_by_distance"):
            assert key in summary

    def test_summary_counts_correctly(self):
        s = ExperimentSession("P01", "Fingertip", [4, 6, 8])
        s._ct_trial_numbers = {2}
        s._pending_ct = 1

        s.record_response("2")   # exp trial 1
        s.record_response("1")   # CT trial 2
        s.record_response("2")   # exp trial 3

        summary = s.get_summary()
        assert summary["experimental_trials"] == 2
        assert summary["control_trials"] == 1
