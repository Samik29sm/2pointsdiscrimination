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

    def export_csv(
        self,
        session: ExperimentSession,
        filepath: Optional[str] = None,
    ) -> str:
        """Write trial data to a CSV file and return the path."""
        if filepath is None:
            filepath = self._make_filepath(session, "csv")

        fieldnames = [
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
                writer.writerow(trial.to_dict())

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
