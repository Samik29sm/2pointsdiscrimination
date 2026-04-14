# Two-Point Discrimination Experiment Tool

A minimal desktop application for conducting and analysing **two-point discrimination (2PD)** experiments in sensory-perception research.

---

## Features

- **Six built-in body locations** (Fingertip of index finger, Palm, Ventral forearm, Lower back, Lower leg, Foot sole) each with typical 2PD distances pre-loaded.
- **Custom locations and distances** – add a new body site or extra distance on the fly.
- **Staircase algorithm (Method of Limits)**  
  - Starts at the highest distance and steps down until the participant reports 1.  
  - Reverses direction at each boundary.  
  - Automatically stops when the same distance accumulates **3 reversals** (3 × "1 point").  
  - Reports the **threshold** as the next-higher distance (the last reliable 2-point distance).
- **2 Control Trials (CT) per session** – single-point stimuli inserted at random positions to check for response bias with possibility to add more control trials if needed.
- **Distance override** – the experimenter can type a custom distance for any individual trial.
- **Results screen** with session summary, per-distance response table, and an interactive staircase graph (orange = 1 pt, green = 2 pts, dashed red = threshold).
- **Export** to CSV.

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
4. **Results** – When 3 reversals accumulate at the same distance the experiment ends automatically and change location. When all locations are finished, results are saved in a CSV file.

