"""Data storage and export for experiment sessions."""

import csv
import json
import os
from datetime import datetime
from typing import List, Optional

from experiment import ExperimentSession

# Column order used by all CSV exports
TRIAL_FIELDNAMES: List[str] = [
    "participant_id",
    "test_date",
    "testing_day_nr",
    "location",
    "trial_number",
    "trial_type",
    "distance_mm",
    "stimulus_applied",
    "response",
    "correct",
    "timestamp",
]


class DataManager:
    """Saves and exports experiment data to the local filesystem."""

    DEFAULT_DATA_DIR = "data"

    def __init__(self, data_dir: str = DEFAULT_DATA_DIR) -> None:
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_filepath(self, session: ExperimentSession, ext: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        pid = "".join(c if c.isalnum() or c in "-_" else "_" for c in session.participant_id)
        loc = session.location.replace(" ", "_")
        return os.path.join(self.data_dir, f"{pid}_{loc}_{ts}.{ext}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def make_experiment_filepath(
        self, participant_id: str, day_nr: int, test_date: str
    ) -> str:
        """Return an auto-generated CSV path for a multi-location experiment."""
        pid = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in participant_id
        )
        return os.path.join(self.data_dir, f"{pid}_day{day_nr}_{test_date}.csv")

    def init_csv(self, filepath: str) -> None:
        """Create the CSV file with trial headers at experiment start."""
        dirpath = os.path.dirname(os.path.abspath(filepath))
        os.makedirs(dirpath, exist_ok=True)
        with open(filepath, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=TRIAL_FIELDNAMES)
            writer.writeheader()

    def append_trial_row(
        self, session: ExperimentSession, trial, filepath: str
    ) -> None:
        """Append a single trial row to the CSV after each participant response."""
        with open(filepath, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=TRIAL_FIELDNAMES)
            row = trial.to_dict()
            row["participant_id"] = session.participant_id
            row["test_date"] = session.test_date
            row["testing_day_nr"] = session.testing_day_nr
            row["location"] = session.location
            writer.writerow(row)

    def write_final_csv(
        self, sessions: List[ExperimentSession], filepath: str
    ) -> str:
        """Rewrite CSV with a summary section followed by one section per location.

        Structure
        ---------
        SUMMARY
        participant_id, location, threshold_mm, test_date, testing_day_nr
        <one row per session>
        <blank line>
        LOCATION: <name>
        <trial field headers>
        <one row per trial>
        <blank line>
        ... (repeated for each location)
        """
        with open(filepath, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)

            # --- Summary section ---
            writer.writerow(["SUMMARY"])
            summary_fields = [
                "participant_id",
                "location",
                "threshold_mm",
                "test_date",
                "testing_day_nr",
            ]
            writer.writerow(summary_fields)
            for s in sessions:
                writer.writerow([
                    s.participant_id,
                    s.location,
                    s.threshold if s.threshold is not None else "N/A",
                    s.test_date,
                    s.testing_day_nr,
                ])
            writer.writerow([])  # blank separator

            # --- Per-location sections ---
            for s in sessions:
                writer.writerow([f"LOCATION: {s.location}"])
                writer.writerow(TRIAL_FIELDNAMES)
                for trial in s.trials:
                    row = trial.to_dict()
                    row["participant_id"] = s.participant_id
                    row["test_date"] = s.test_date
                    row["testing_day_nr"] = s.testing_day_nr
                    row["location"] = s.location
                    writer.writerow([row.get(f, "") for f in TRIAL_FIELDNAMES])
                writer.writerow([])  # blank separator

        return filepath

    def get_next_testing_day_nr(self, participant_id: str) -> int:
        """Return the next testing day number for a participant.

        Scans the data directory for existing CSV files whose names start
        with the sanitised participant ID and returns the count + 1.
        """
        pid = "".join(c if c.isalnum() or c in "-_" else "_" for c in participant_id)
        if not os.path.isdir(self.data_dir):
            return 1
        existing = [
            f for f in os.listdir(self.data_dir)
            if f.startswith(pid + "_") and f.endswith(".csv")
        ]
        return len(existing) + 1

    def export_csv(
        self,
        session: ExperimentSession,
        filepath: Optional[str] = None,
    ) -> str:
        """Write trial data to a CSV file and return the path."""
        if filepath is None:
            filepath = self._make_filepath(session, "csv")

        with open(filepath, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=TRIAL_FIELDNAMES)
            writer.writeheader()
            for trial in session.trials:
                row = trial.to_dict()
                row["participant_id"] = session.participant_id
                row["test_date"] = session.test_date
                row["testing_day_nr"] = session.testing_day_nr
                row["location"] = session.location
                writer.writerow(row)

        return filepath

    def export_json(
        self,
        session: ExperimentSession,
        filepath: Optional[str] = None,
    ) -> str:
        """Write session summary + trial data to a JSON file and return the path."""
        if filepath is None:
            filepath = self._make_filepath(session, "json")

        payload = {
            "summary": session.get_summary(),
            "trials": [t.to_dict() for t in session.trials],
        }

        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)

        return filepath
