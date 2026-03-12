"""Unit tests for experiment.py logic."""

import bisect
import os
import tempfile

import pytest
from data_manager import DataManager
from experiment import ExperimentSession, Trial
from locations import BODY_LOCATIONS


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

    def test_experiment_does_not_end_before_two_cts(self):
        """Staircase threshold does not mark done if CTs are still pending."""
        s = ExperimentSession("P01", "Loc", [5.0])
        # Leave the 2 CTs pending; the staircase will hit threshold first
        s._ct_trial_numbers = set()  # no scheduled CT positions yet
        s._pending_ct = 2
        # Trigger 3 reversals at 5 mm (the only distance)
        for _ in range(3):
            s.record_response("1")
        # Threshold determined but not done yet – 2 CTs remain
        assert not s.done
        assert s._threshold_determined
        assert s.threshold == 5.0
        # Complete the 2 remaining control trials
        s.record_response("1")  # CT #1
        assert not s.done
        s.record_response("1")  # CT #2
        assert s.done

    def test_experiment_ends_immediately_when_cts_already_done(self):
        """If all CTs are already done, threshold detection marks done immediately."""
        s = ExperimentSession("P01", "Loc", [5.0])
        s._ct_trial_numbers = set()
        s._pending_ct = 0
        for _ in range(3):
            s.record_response("1")
        assert s.done

    def test_ct_positions_never_in_first_two_trials(self):
        """CT positions must always be >= 3 (never trial 1 or 2)."""
        for _ in range(30):
            s = ExperimentSession("P01", "Fingertip", [2, 4, 6, 8, 10])
            assert all(p >= 3 for p in s._ct_trial_numbers)

    def test_ct_positions_are_distinct(self):
        """The two CT positions must be different trial numbers."""
        for _ in range(30):
            s = ExperimentSession("P01", "Fingertip", [2, 4, 6, 8, 10])
            positions = list(s._ct_trial_numbers)
            assert len(positions) == 2
            assert positions[0] != positions[1]

    def test_ct_positions_spread_across_halves(self):
        """CT positions should come from different halves of the estimated range.

        With distances [2,4,6,8,10] (n=5):
          avg_threshold_idx = 2, steps_down = 2
          estimated_total = 2 + 3*2 + 3 = 11, max_pool = 11
          pool = [3..11], mid index = 4, so first half = [3,4,5,6], second = [7,8,9,10,11]
        After sorting the two positions the smaller one must come from the first
        half and the larger from the second half (since first_half < second_half
        by construction).
        """
        n = 5
        avg_threshold_idx = n // 2          # 2
        steps_down = max((n - 1) - avg_threshold_idx, 1)  # 2
        estimated_total = steps_down + ExperimentSession.REVERSAL_THRESHOLD * 2 + 3  # 11
        max_pool = max(estimated_total, 10)  # 11
        pool = list(range(3, max_pool + 1))
        mid = len(pool) // 2
        first_half = set(pool[:mid])
        second_half = set(pool[mid:])

        for _ in range(30):
            s = ExperimentSession("P01", "Fingertip", [2, 4, 6, 8, 10])
            positions = s._ct_trial_numbers
            assert len(positions) == 2
            pos_list = sorted(positions)
            # After sorting, the smaller value must be from the first half and
            # the larger from the second half (the halves are disjoint ranges).
            assert pos_list[0] in first_half, f"{pos_list[0]} not in first half {first_half}"
            assert pos_list[1] in second_half, f"{pos_list[1]} not in second half {second_half}"

    def test_ct_positions_within_estimated_range(self):
        """Both CT positions should fall within [3 .. max_pool]."""
        for _ in range(30):
            distances = [1, 5, 10, 15, 20, 25, 30, 40]
            s = ExperimentSession("P01", "Palm", distances)
            n = len(s.distances)
            # Mirror the index-computation logic in _generate_ct_positions.
            loc_data = BODY_LOCATIONS.get("Palm", {})
            avg_threshold_mm = loc_data.get("average_threshold")
            if avg_threshold_mm is not None:
                idx = bisect.bisect_left(s.distances, float(avg_threshold_mm))
                avg_threshold_idx = min(idx, n - 1)
            else:
                avg_threshold_idx = n // 2
            steps_down = max((n - 1) - avg_threshold_idx, 1)
            estimated_total = steps_down + ExperimentSession.REVERSAL_THRESHOLD * 2 + 3
            max_pool = max(estimated_total, 10)
            assert all(3 <= p <= max_pool for p in s._ct_trial_numbers)


# ---------------------------------------------------------------------------
# ExperimentSession – summary
# ---------------------------------------------------------------------------

class TestSummary:
    def test_summary_contains_expected_keys(self):
        s = ExperimentSession("P01", "Fingertip", [2, 4, 6, 8, 10])
        summary = s.get_summary()
        for key in ("participant_id", "location", "test_date", "testing_day_nr",
                    "threshold_mm", "total_trials", "experimental_trials",
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


# ---------------------------------------------------------------------------
# ExperimentSession – test_date and testing_day_nr
# ---------------------------------------------------------------------------

class TestSessionMetadata:
    def test_default_testing_day_nr(self):
        s = ExperimentSession("P01", "Fingertip", [2, 4])
        assert s.testing_day_nr == 1

    def test_custom_testing_day_nr(self):
        s = ExperimentSession("P01", "Fingertip", [2, 4], testing_day_nr=3)
        assert s.testing_day_nr == 3

    def test_default_test_date_is_today(self):
        from datetime import date
        s = ExperimentSession("P01", "Fingertip", [2, 4])
        assert s.test_date == date.today().isoformat()

    def test_custom_test_date(self):
        s = ExperimentSession("P01", "Fingertip", [2, 4], test_date="2025-01-15")
        assert s.test_date == "2025-01-15"

    def test_summary_includes_date_and_day_nr(self):
        s = ExperimentSession("P01", "Fingertip", [2, 4], testing_day_nr=2, test_date="2025-06-01")
        summary = s.get_summary()
        assert summary["test_date"] == "2025-06-01"
        assert summary["testing_day_nr"] == 2

    def test_default_experiment_session(self):
        s = ExperimentSession("P01", "Fingertip", [2, 4])
        assert s.experiment_session == 1

    def test_custom_experiment_session(self):
        s = ExperimentSession("P01", "Fingertip", [2, 4], experiment_session=2)
        assert s.experiment_session == 2


# ---------------------------------------------------------------------------
# DataManager – get_next_testing_day_nr
# ---------------------------------------------------------------------------

class TestDataManagerDayNr:
    def test_returns_1_for_new_participant(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(data_dir=tmpdir)
            assert dm.get_next_testing_day_nr("NewParticipant") == 1

    def test_increments_with_existing_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(data_dir=tmpdir)
            # Create two fake CSV files for participant P99
            open(os.path.join(tmpdir, "P99_Fingertip_20250101.csv"), "w").close()
            open(os.path.join(tmpdir, "P99_Palm_20250102.csv"), "w").close()
            assert dm.get_next_testing_day_nr("P99") == 3

    def test_ignores_non_matching_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(data_dir=tmpdir)
            # File for a different participant should not count
            open(os.path.join(tmpdir, "OTHER_Fingertip_20250101.csv"), "w").close()
            assert dm.get_next_testing_day_nr("P99") == 1

    def test_export_csv_includes_metadata_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(data_dir=tmpdir)
            s = ExperimentSession("P01", "Fingertip", [4, 6, 8], testing_day_nr=2, test_date="2025-06-01")
            s._ct_trial_numbers = set()
            s._pending_ct = 0
            s.record_response("2")
            filepath = os.path.join(tmpdir, "test_out.csv")
            dm.export_csv(s, filepath)
            import csv
            with open(filepath, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["participant_id"] == "P01"
            assert rows[0]["test_date"] == "2025-06-01"
            assert rows[0]["testing_day_nr"] == "2"
            assert rows[0]["location"] == "Fingertip"


# ---------------------------------------------------------------------------
# DataManager – new multi-location CSV methods
# ---------------------------------------------------------------------------

class TestDataManagerMultiLocationCSV:
    def _make_session(self, pid="P01", loc="Fingertip", distances=None, day_nr=1):
        if distances is None:
            distances = [4, 6, 8]
        s = ExperimentSession(pid, loc, distances, testing_day_nr=day_nr, test_date="2025-06-01")
        s._ct_trial_numbers = set()
        s._pending_ct = 0
        return s

    # -- make_experiment_filepath --

    def test_make_experiment_filepath_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(data_dir=tmpdir)
            path = dm.make_experiment_filepath("P01", 1, 3, "2025-06-01")
            assert path.endswith("P01_session1_day3_2025-06-01.csv")
            assert path.startswith(tmpdir)

    def test_make_experiment_filepath_sanitises_pid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(data_dir=tmpdir)
            path = dm.make_experiment_filepath("P 01/x", 1, 1, "2025-01-01")
            basename = os.path.basename(path)
            assert "/" not in basename
            assert " " not in basename

    # -- init_csv --

    def test_init_csv_creates_file_with_headers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(data_dir=tmpdir)
            fp = os.path.join(tmpdir, "out.csv")
            dm.init_csv(fp)
            assert os.path.isfile(fp)
            import csv as csv_mod
            with open(fp, newline="", encoding="utf-8") as fh:
                reader = csv_mod.DictReader(fh)
                assert set(reader.fieldnames or []) == {
                    "participant_id", "test_date", "testing_day_nr", "location",
                    "trial_number", "trial_type", "distance_mm", "stimulus_applied",
                    "response", "correct", "timestamp",
                }
                rows = list(reader)
            assert rows == []

    def test_init_csv_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(data_dir=tmpdir)
            fp = os.path.join(tmpdir, "subdir", "out.csv")
            dm.init_csv(fp)
            assert os.path.isfile(fp)

    # -- append_trial_row --

    def test_append_trial_row_writes_one_row(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(data_dir=tmpdir)
            fp = os.path.join(tmpdir, "out.csv")
            dm.init_csv(fp)
            s = self._make_session()
            s.record_response("2")
            dm.append_trial_row(s, s.trials[-1], fp)
            import csv as csv_mod
            with open(fp, newline="", encoding="utf-8") as fh:
                rows = list(csv_mod.DictReader(fh))
            assert len(rows) == 1
            assert rows[0]["location"] == "Fingertip"
            assert rows[0]["participant_id"] == "P01"
            assert rows[0]["response"] == "2"

    def test_append_trial_row_accumulates_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(data_dir=tmpdir)
            fp = os.path.join(tmpdir, "out.csv")
            dm.init_csv(fp)
            s = self._make_session()
            for resp in ["2", "2", "1"]:
                s.record_response(resp)
                dm.append_trial_row(s, s.trials[-1], fp)
            import csv as csv_mod
            with open(fp, newline="", encoding="utf-8") as fh:
                rows = list(csv_mod.DictReader(fh))
            assert len(rows) == 3

    # -- write_final_csv --

    def test_write_final_csv_has_summary_section(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(data_dir=tmpdir)
            s1 = self._make_session(loc="Fingertip")
            s2 = self._make_session(loc="Palm", distances=[5, 10, 15, 20])
            s1.threshold = 6.0
            s2.threshold = 10.0
            fp = os.path.join(tmpdir, "final.csv")
            dm.write_final_csv([s1, s2], fp)
            with open(fp, newline="", encoding="utf-8") as fh:
                content = fh.read()
            assert "SUMMARY" in content
            assert "Fingertip" in content
            assert "Palm" in content
            assert "6.0" in content
            assert "10.0" in content

    def test_write_final_csv_has_per_location_sections(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(data_dir=tmpdir)
            s1 = self._make_session(loc="Fingertip")
            s1.record_response("2")
            s2 = self._make_session(loc="Palm", distances=[5, 10, 15, 20])
            s2.record_response("2")
            fp = os.path.join(tmpdir, "final.csv")
            dm.write_final_csv([s1, s2], fp)
            with open(fp, newline="", encoding="utf-8") as fh:
                content = fh.read()
            assert "LOCATION: Fingertip" in content
            assert "LOCATION: Palm" in content

    def test_write_final_csv_shows_na_for_missing_threshold(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(data_dir=tmpdir)
            s = self._make_session()
            fp = os.path.join(tmpdir, "final.csv")
            dm.write_final_csv([s], fp)
            with open(fp, newline="", encoding="utf-8") as fh:
                content = fh.read()
            assert "N/A" in content

    def test_write_final_csv_returns_filepath(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(data_dir=tmpdir)
            s = self._make_session()
            fp = os.path.join(tmpdir, "final.csv")
            result = dm.write_final_csv([s], fp)
            assert result == fp

    def test_write_final_csv_has_experiment_info_section(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(data_dir=tmpdir)
            s = self._make_session()
            s.experiment_session = 2
            fp = os.path.join(tmpdir, "final.csv")
            dm.write_final_csv([s], fp)
            with open(fp, newline="", encoding="utf-8") as fh:
                content = fh.read()
            assert "EXPERIMENT INFO" in content
            assert "participant_id" in content
            assert "test_date" in content
            assert "experiment_session" in content
            assert "testing_day_nr" in content
            assert "P01" in content
            assert "2025-06-01" in content

    def test_write_final_csv_location_columns_restricted(self):
        """Per-location sections should only contain the required columns."""
        import csv as csv_mod
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(data_dir=tmpdir)
            s = self._make_session()
            s.record_response("2")
            fp = os.path.join(tmpdir, "final.csv")
            dm.write_final_csv([s], fp)
            with open(fp, newline="", encoding="utf-8") as fh:
                content = fh.read()
            # Find the header row after the LOCATION marker
            lines = content.splitlines()
            header_fields = None
            for i, line in enumerate(lines):
                if line.startswith("LOCATION:") and i + 1 < len(lines):
                    header_fields = next(csv_mod.reader([lines[i + 1]]))
                    break
            assert header_fields is not None
            required = {"trial_number", "trial_type", "distance_mm",
                        "stimulus_applied", "response", "correct"}
            assert set(header_fields) == required
            assert "timestamp" not in header_fields
            assert "participant_id" not in header_fields
