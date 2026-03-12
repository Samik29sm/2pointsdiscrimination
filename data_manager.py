"""Data storage and export for experiment sessions."""

import csv
import json
import os
from datetime import datetime
from typing import Optional

from experiment import ExperimentSession


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

        fieldnames = [
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

        with open(filepath, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
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
