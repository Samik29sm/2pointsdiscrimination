# Two-Point Discrimination Experiment Tool

A clean, minimal desktop application for conducting and analysing **two-point discrimination (2PD)** experiments in sensory-perception research.

---

## Screenshots

| Setup | Trial | Results |
|---|---|---|
| ![Setup screen](https://github.com/user-attachments/assets/d31b3dba-7cf4-4425-90c6-c20e98757619) | ![Trial screen](https://github.com/user-attachments/assets/1ee92d38-e9bf-424a-b4ec-c8b5250d4a69) | ![Results screen](https://github.com/user-attachments/assets/6cf1180f-1001-4c5c-ab77-0694e49b4eab) |

---

## Features

- **Eight built-in body locations** (Fingertip, Palm, Forearm, Upper Arm, Back, Lip, Forehead, Cheek) each with typical 2PD distances pre-loaded.
- **Custom locations and distances** – add a new body site or extra distance on the fly.
- **Staircase algorithm (Method of Limits)**  
  - Starts at the highest distance and steps down until the participant reports 1 point.  
  - Reverses direction at each boundary.  
  - Automatically stops when the same distance accumulates **3 reversals** (3 × "1 point").  
  - Reports the **threshold** as the next-higher distance (the last reliable 2-point distance).
- **2 Control Trials (CT) per session** – single-point stimuli inserted at random positions to check for response bias.
- **Distance override** – the experimenter can type a custom distance for any individual trial.
- **Results screen** with session summary, per-distance response table, and an interactive staircase graph (orange = 1 pt, green = 2 pts, dashed red = threshold).
- **Export** to CSV or JSON with one click.

---

## Project Structure

```
2pointsdiscrimination/
├── app.py            # Entry point
├── gui.py            # Tkinter UI (Setup → Trial → Results)
├── experiment.py     # Staircase algorithm & session state
├── locations.py      # Default body locations & distances
├── data_manager.py   # CSV / JSON export
├── requirements.txt
└── tests/
    └── test_experiment.py
```

---

## Running Locally

### Prerequisites

- Python 3.8 or newer
- `tkinter` (usually bundled with Python; see below if missing)
- `matplotlib` (for the response graph)

```bash
# Clone / enter the repo
git clone https://github.com/Samik29sm/2pointsdiscrimination.git
cd 2pointsdiscrimination

# Install Python dependencies
pip install -r requirements.txt

# (Linux only) install tkinter if not already present
# Ubuntu/Debian:  sudo apt-get install python3-tk
# Fedora:         sudo dnf install python3-tkinter
# macOS Homebrew: brew install python-tk

# Launch the app
python app.py
```

### Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## How to Use

1. **Setup** – Enter a Participant ID, choose a body location from the dropdown (or add a custom one), review/add test distances, then click **Start Experiment**.
2. **Trial** – The app shows the distance to apply. Present the calipers to the participant, then click **1 Point** or **2 Points** to record their response. Check *Override distance* to test a different distance than suggested.
3. **Control Trials** – Two trials appear at random positions with the instruction to apply only one point. These verify the participant is responding honestly.
4. **Results** – When 3 reversals accumulate at the same distance the experiment ends automatically. The threshold, a per-distance table, and a staircase graph are displayed. Use **Export CSV** or **Export JSON** to save the data. Click **New Experiment** to start again.

---

## Suggested Improvements

- **Randomised stimulus distances** – shuffle the distance sequence or use an adaptive Bayesian estimator (e.g. QUEST).
- **Repeat-trial button** – re-test the current distance if the experimenter suspects a false response.
- **Inter-trial interval timer** – enforce a minimum pause between trials to avoid habituation.
- **Multi-location session** – chain several body locations in one run, with a combined report at the end.
- **Normative data overlay** – display published reference thresholds on the results graph.
