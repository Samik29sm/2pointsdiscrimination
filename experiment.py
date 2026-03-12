"""Two-point discrimination experiment logic.

Algorithm (staircase / method of limits):
  • Start at the highest distance in the predefined list.
  • "2 points perceived" → move one step down (lower distance).
  • "1 point perceived"  → move one step up (higher distance) and record a
    reversal at the current distance.
  • When the same distance accumulates REVERSAL_THRESHOLD (3) reversals the
    experiment ends.  The two-point threshold is the next-higher distance in
    the list (the last distance at which the participant reliably saw 2 pts).
  • Two control trials (CT) per body location are inserted at random positions;
    in these trials only a single calipers point is applied.
"""

import random
from datetime import datetime
from typing import Any, Dict, List, Optional


class Trial:
    """Represents a single trial in the experiment."""

    def __init__(
        self,
        trial_number: int,
        trial_type: str,
        distance: Optional[float],
        stimulus_count: int = 2,
    ) -> None:
        self.trial_number = trial_number
        self.trial_type = trial_type        # 'experimental' | 'control'
        self.distance = distance            # mm; None for control trials
        self.stimulus_count = stimulus_count  # points physically applied
        self.response: Optional[str] = None  # '1' or '2'
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trial_number": self.trial_number,
            "trial_type": self.trial_type,
            "distance_mm": "CT" if self.trial_type == "control" else self.distance,
            "stimulus_applied": self.stimulus_count,
            "response": self.response,
            "correct": self._is_correct(),
            "timestamp": self.timestamp,
        }

    def _is_correct(self) -> Optional[bool]:
        """Control trials are 'correct' when the participant reports 1 point."""
        if self.trial_type == "control":
            return self.response == "1"
        return None  # no ground-truth for experimental trials


class ExperimentSession:
    """Manages the complete state of one two-point discrimination session."""

    NUM_CONTROL_TRIALS = 2
    REVERSAL_THRESHOLD = 3  # 1-point responses at same distance to stop

    def __init__(
        self,
        participant_id: str,
        location: str,
        distances: List[float],
        testing_day_nr: int = 1,
        test_date: Optional[str] = None,
        experiment_session: int = 1,
    ) -> None:
        self.participant_id = participant_id
        self.location = location
        self.testing_day_nr = testing_day_nr
        self.experiment_session = experiment_session
        self.test_date = test_date if test_date is not None else datetime.now().strftime("%Y-%m-%d")
        self.start_time = datetime.now().isoformat()

        # Ascending, unique distance list
        self.distances: List[float] = sorted(set(float(d) for d in distances))
        if not self.distances:
            raise ValueError("At least one distance must be provided.")

        self.trials: List[Trial] = []
        self.threshold: Optional[float] = None
        self.done = False

        # Staircase pointer: index into self.distances (ascending); start high
        self.current_distance_index: int = len(self.distances) - 1

        # Reversal counter per distance
        self.single_point_counts: Dict[float, int] = {}

        # Control trial scheduling
        self._pending_ct = self.NUM_CONTROL_TRIALS
        self._ct_trial_numbers: set = self._generate_ct_positions()
        # Set when the staircase threshold is found but CTs have not yet finished
        self._threshold_determined: bool = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_ct_positions(self) -> set:
        """Choose random trial numbers for control trials.

        CT trials are placed after the first 2 experimental trials so the
        participant never starts with a control trial.
        """
        max_pool = max(len(self.distances) * 3 + 5, 10)
        pool = list(range(3, max_pool))
        positions = random.sample(pool, min(self.NUM_CONTROL_TRIALS, len(pool)))
        return set(positions)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_trial_number(self) -> int:
        return len(self.trials) + 1

    @property
    def is_next_trial_control(self) -> bool:
        # After the staircase threshold is found, force-run remaining CTs
        if self._threshold_determined and self._pending_ct > 0:
            return True
        return (
            self.current_trial_number in self._ct_trial_numbers
            and self._pending_ct > 0
        )

    @property
    def current_distance(self) -> Optional[float]:
        """The distance the staircase is pointing at (or None for CT)."""
        if self.is_next_trial_control:
            return None
        if 0 <= self.current_distance_index < len(self.distances):
            return self.distances[self.current_distance_index]
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_distance(self, distance: float) -> None:
        """Insert a new distance into the list (no-op if already present)."""
        distance = float(distance)
        if distance in self.distances:
            return
        # Preserve current staircase pointer after list change
        current = self.distances[self.current_distance_index]
        self.distances.append(distance)
        self.distances.sort()
        self.current_distance_index = self.distances.index(current)

    def record_response(
        self, response: str, custom_distance: Optional[float] = None
    ) -> None:
        """Record the participant's response for the current trial.

        Args:
            response: ``'1'`` for one point perceived, ``'2'`` for two points.
            custom_distance: experimenter-supplied override distance (mm).
        """
        if self.done:
            return

        trial_num = self.current_trial_number

        if self.is_next_trial_control:
            # Control trial: only one physical point is applied
            trial = Trial(trial_num, "control", None, stimulus_count=1)
            trial.response = response
            self.trials.append(trial)
            self._pending_ct -= 1
            # If the staircase already determined the threshold, finish now
            if self._threshold_determined and self._pending_ct == 0:
                self.done = True

        else:
            # If a custom distance is provided, add it to the list and point there
            if custom_distance is not None:
                self.add_distance(custom_distance)
                self.current_distance_index = self.distances.index(
                    float(custom_distance)
                )

            distance = self.distances[self.current_distance_index]
            trial = Trial(trial_num, "experimental", distance, stimulus_count=2)
            trial.response = response
            self.trials.append(trial)
            self._update_staircase(distance, response)

    def get_summary(self) -> Dict[str, Any]:
        """Return a dict summarising the session results."""
        experimental = [t for t in self.trials if t.trial_type == "experimental"]
        control = [t for t in self.trials if t.trial_type == "control"]

        responses_by_distance: Dict[float, List[str]] = {}
        for t in experimental:
            if t.distance is not None:
                responses_by_distance.setdefault(t.distance, []).append(
                    t.response or ""
                )

        ct_correct = sum(1 for t in control if t.response == "1")

        return {
            "participant_id": self.participant_id,
            "location": self.location,
            "test_date": self.test_date,
            "testing_day_nr": self.testing_day_nr,
            "threshold_mm": self.threshold,
            "total_trials": len(self.trials),
            "experimental_trials": len(experimental),
            "control_trials": len(control),
            "control_trials_correct": ct_correct,
            "responses_by_distance": {
                str(d): {
                    "responses": v,
                    "count_1": v.count("1"),
                    "count_2": v.count("2"),
                }
                for d, v in sorted(responses_by_distance.items())
            },
            "start_time": self.start_time,
            "end_time": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Private staircase logic
    # ------------------------------------------------------------------

    def _update_staircase(self, distance: float, response: str) -> None:
        idx = self.current_distance_index

        if response == "1":
            # Record reversal at this distance
            count = self.single_point_counts.get(distance, 0) + 1
            self.single_point_counts[distance] = count

            if count >= self.REVERSAL_THRESHOLD:
                # Threshold = the next-higher distance
                if idx + 1 < len(self.distances):
                    self.threshold = self.distances[idx + 1]
                else:
                    self.threshold = self.distances[idx]
                # Only mark done if all control trials are already completed
                if self._pending_ct == 0:
                    self.done = True
                else:
                    self._threshold_determined = True
                return

            # Move up one step (back towards higher distances)
            self.current_distance_index = min(idx + 1, len(self.distances) - 1)

        elif response == "2":
            # Move down one step (towards lower distances)
            self.current_distance_index = max(idx - 1, 0)
