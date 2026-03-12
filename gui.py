"""Tkinter GUI for the Two-Point Discrimination Experiment tool."""

import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

from data_manager import DataManager
from experiment import ExperimentSession
from locations import BODY_LOCATIONS, DEFAULT_LOCATION

# ---------------------------------------------------------------------------
# Theme constants
# ---------------------------------------------------------------------------
FONT_TITLE   = ("Helvetica", 20, "bold")
FONT_HEADING = ("Helvetica", 15, "bold")
FONT_SUBHEAD = ("Helvetica", 13, "bold")
FONT_BODY    = ("Helvetica", 12)
FONT_SMALL   = ("Helvetica", 10)
FONT_BIG_NUM = ("Helvetica", 36, "bold")

BG          = "#f4f6f8"
PANEL_BG    = "#ffffff"
PRIMARY     = "#2c3e50"
ACCENT      = "#2980b9"
SUCCESS     = "#27ae60"
DANGER      = "#e74c3c"
WARN        = "#e67e22"
LIGHT       = "#ecf0f1"
BORDER      = "#bdc3c7"
CT_COLOR    = "#8e44ad"     # purple for control trials

PAD = 12


def _make_button(parent, text, command, bg=ACCENT, fg="white", font=FONT_BODY, **kw):
    kw.setdefault("padx", 16)
    kw.setdefault("pady", 8)
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        font=font,
        relief=tk.FLAT,
        activebackground=bg,
        activeforeground=fg,
        cursor="hand2",
        **kw,
    )


def _make_label(parent, text, font=FONT_BODY, fg=PRIMARY, bg=PANEL_BG, **kw):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, **kw)


def _panel(parent, **kw):
    """A white, slightly raised panel frame."""
    return tk.Frame(parent, bg=PANEL_BG, relief=tk.FLAT, bd=0, **kw)


# ===========================================================================
# Main application window
# ===========================================================================

class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Two-Point Discrimination Experiment")
        self.geometry("860x700")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(720, 580)

        self.data_manager = DataManager()
        self.session: Optional[ExperimentSession] = None
        self.csv_save_path: Optional[str] = None

        # Multi-location experiment tracking
        self.sessions: List[ExperimentSession] = []
        self._location_queue: List[str] = []
        self._current_location_idx: int = 0
        self._setup_pid: str = ""
        self._setup_day_nr: int = 1
        self._setup_test_date: str = ""

        self._container = tk.Frame(self, bg=BG)
        self._container.pack(fill=tk.BOTH, expand=True)

        self._current_frame: Optional[tk.Frame] = None
        self.show_setup()

    # ------------------------------------------------------------------
    # Frame navigation
    # ------------------------------------------------------------------

    def _replace(self, frame: tk.Frame) -> None:
        if self._current_frame is not None:
            self._current_frame.destroy()
        self._current_frame = frame
        frame.pack(fill=tk.BOTH, expand=True)

    def show_setup(self) -> None:
        self._replace(SetupFrame(self._container, self))

    def show_trial(self, session: ExperimentSession, csv_save_path: str) -> None:
        self.session = session
        self.csv_save_path = csv_save_path
        self._replace(TrialFrame(self._container, self, session, csv_save_path))

    def show_results(self, session: ExperimentSession, csv_save_path: str) -> None:
        self._replace(ResultsFrame(self._container, self, session, csv_save_path))

    def start_experiment(
        self,
        pid: str,
        day_nr: int,
        test_date: str,
        locations: List[str],
        csv_path: str,
    ) -> None:
        """Begin a multi-location experiment session."""
        self.sessions = []
        self._location_queue = list(locations)
        self._current_location_idx = 0
        self._setup_pid = pid
        self._setup_day_nr = day_nr
        self._setup_test_date = test_date
        self.csv_save_path = csv_path
        # Create the CSV file immediately so partial data is preserved
        self.data_manager.init_csv(csv_path)
        self._start_next_location()

    def _start_next_location(self) -> None:
        """Start the next queued location, or show final results when done."""
        if self._current_location_idx >= len(self._location_queue):
            # All locations finished – write final structured CSV then show results
            try:
                self.data_manager.write_final_csv(self.sessions, self.csv_save_path)
            except OSError:
                pass  # best-effort; results are still displayed
            self.show_all_results()
            return
        loc = self._location_queue[self._current_location_idx]
        self._current_location_idx += 1
        distances = list(BODY_LOCATIONS.get(loc, {}).get("distances", []))
        if not distances:
            distances = [5, 10, 15, 20]  # fallback for custom locations
        session = ExperimentSession(
            self._setup_pid,
            loc,
            distances,
            testing_day_nr=self._setup_day_nr,
            test_date=self._setup_test_date,
        )
        self.show_trial(session, self.csv_save_path)

    def on_location_complete(self, session: ExperimentSession) -> None:
        """Called by TrialFrame when one location's experiment finishes."""
        self.sessions.append(session)
        self._start_next_location()

    def show_all_results(self) -> None:
        """Show combined results across all completed locations."""
        self._replace(
            AllResultsFrame(self._container, self, self.sessions, self.csv_save_path)
        )


# ===========================================================================
# Setup frame
# ===========================================================================

class SetupFrame(tk.Frame):
    """Initial screen: participant ID, experiment type, locations, CSV path."""

    def __init__(self, parent: tk.Widget, app: App) -> None:
        super().__init__(parent, bg=BG)
        self.app = app
        self._csv_manually_set: bool = False
        self._location_vars: Dict[str, tk.BooleanVar] = {}
        self._build()

    def _build(self) -> None:
        # ---------- title ----------
        header = tk.Frame(self, bg=PRIMARY, padx=PAD, pady=PAD)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="Two-Point Discrimination Experiment",
            font=FONT_TITLE,
            fg="white",
            bg=PRIMARY,
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Setup",
            font=FONT_BODY,
            fg=LIGHT,
            bg=PRIMARY,
        ).pack(anchor="w")

        # ---------- scrollable body ----------
        canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        vscroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        body_outer = tk.Frame(canvas, bg=BG)
        _cw = canvas.create_window((0, 0), window=body_outer, anchor="nw")

        def _on_canvas_resize(ev):
            canvas.itemconfig(_cw, width=ev.width)
        canvas.bind("<Configure>", _on_canvas_resize)

        def _on_body_configure(_ev):
            canvas.configure(scrollregion=canvas.bbox("all"))
        body_outer.bind("<Configure>", _on_body_configure)

        body = tk.Frame(body_outer, bg=BG, padx=PAD * 2, pady=PAD)
        body.pack(fill=tk.BOTH, expand=True)

        # ---- Row 1: Participant ID + Test Date ----
        row1 = tk.Frame(body, bg=BG)
        row1.pack(fill=tk.X, pady=(PAD, 6))

        pid_panel = _panel(row1)
        pid_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, PAD // 2))
        _make_label(pid_panel, "Participant ID", font=FONT_SUBHEAD).pack(
            anchor="w", padx=PAD, pady=(PAD, 2)
        )
        self._pid_var = tk.StringVar()
        pid_entry = tk.Entry(
            pid_panel, textvariable=self._pid_var, font=FONT_BODY,
            relief=tk.SOLID, bd=1,
        )
        pid_entry.pack(fill=tk.X, padx=PAD, pady=(0, PAD))
        pid_entry.focus_set()
        self._pid_var.trace_add("write", self._on_pid_change)

        date_panel = _panel(row1)
        date_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(PAD // 2, 0))
        _make_label(date_panel, "Test Date", font=FONT_SUBHEAD).pack(
            anchor="w", padx=PAD, pady=(PAD, 2)
        )
        self._date_var = tk.StringVar(value=date.today().isoformat())
        tk.Entry(
            date_panel, textvariable=self._date_var, font=FONT_BODY,
            relief=tk.SOLID, bd=1, state="readonly", width=14,
        ).pack(padx=PAD, pady=(0, PAD))

        # ---- Row 2: Experiment Type + Testing Day Nr. ----
        row2 = tk.Frame(body, bg=BG)
        row2.pack(fill=tk.X, pady=6)

        exp_panel = _panel(row2)
        exp_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, PAD // 2))
        _make_label(exp_panel, "Experiment Type", font=FONT_SUBHEAD).pack(
            anchor="w", padx=PAD, pady=(PAD, 4)
        )
        self._exp_type_var = tk.StringVar(value="first")
        exp_radio_frame = tk.Frame(exp_panel, bg=PANEL_BG)
        exp_radio_frame.pack(fill=tk.X, padx=PAD, pady=(0, PAD))
        tk.Radiobutton(
            exp_radio_frame,
            text="1st 2PD experiment (default: Day 1)",
            variable=self._exp_type_var,
            value="first",
            bg=PANEL_BG,
            font=FONT_BODY,
            command=self._on_exp_type_change,
        ).pack(anchor="w")
        tk.Radiobutton(
            exp_radio_frame,
            text="2nd 2PD experiment (default: Day 8)",
            variable=self._exp_type_var,
            value="second",
            bg=PANEL_BG,
            font=FONT_BODY,
            command=self._on_exp_type_change,
        ).pack(anchor="w")

        day_panel = _panel(row2)
        day_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(PAD // 2, 0))
        day_inner = tk.Frame(day_panel, bg=PANEL_BG)
        day_inner.pack(fill=tk.X, padx=PAD, pady=PAD)
        _make_label(day_inner, "Testing Day Nr.", font=FONT_SUBHEAD).pack(side=tk.LEFT)
        self._day_nr_var = tk.IntVar(value=1)
        tk.Spinbox(
            day_inner, from_=1, to=999, textvariable=self._day_nr_var,
            font=FONT_BODY, width=5, relief=tk.SOLID, bd=1,
        ).pack(side=tk.LEFT, padx=(PAD, 0))
        self._day_hint = tk.Label(
            day_inner, text="", font=FONT_SMALL, fg="#7f8c8d", bg=PANEL_BG
        )
        self._day_hint.pack(side=tk.LEFT, padx=(PAD, 0))

        # ---- Row 3: Body Locations (checkboxes, all selected by default) ----
        loc_panel = _panel(body)
        loc_panel.pack(fill=tk.X, pady=6)

        loc_header = tk.Frame(loc_panel, bg=PANEL_BG)
        loc_header.pack(fill=tk.X, padx=PAD, pady=(PAD, 4))
        _make_label(loc_header, "Body Locations", font=FONT_SUBHEAD).pack(side=tk.LEFT)
        _make_button(
            loc_header, "+ Custom", self._add_custom_location,
            bg=WARN, font=FONT_SMALL, pady=2,
        ).pack(side=tk.RIGHT, padx=(4, 0))
        tk.Button(
            loc_header, text="Deselect All", font=FONT_SMALL, bg=LIGHT, fg=PRIMARY,
            relief=tk.FLAT, command=self._deselect_all_locations, cursor="hand2",
            padx=6, pady=2,
        ).pack(side=tk.RIGHT, padx=(4, 0))
        tk.Button(
            loc_header, text="Select All", font=FONT_SMALL, bg=LIGHT, fg=PRIMARY,
            relief=tk.FLAT, command=self._select_all_locations, cursor="hand2",
            padx=6, pady=2,
        ).pack(side=tk.RIGHT, padx=(4, 0))

        self._loc_checks_frame = tk.Frame(loc_panel, bg=PANEL_BG)
        self._loc_checks_frame.pack(fill=tk.X, padx=PAD, pady=(0, PAD))
        self._build_location_checkboxes()

        # ---- Row 4: CSV Save Path ----
        csv_panel = _panel(body)
        csv_panel.pack(fill=tk.X, pady=6)
        _make_label(csv_panel, "CSV Save Path", font=FONT_SUBHEAD).pack(
            anchor="w", padx=PAD, pady=(PAD, 2)
        )
        csv_row = tk.Frame(csv_panel, bg=PANEL_BG)
        csv_row.pack(fill=tk.X, padx=PAD, pady=(0, PAD))
        self._csv_path_var = tk.StringVar()
        tk.Label(
            csv_row, textvariable=self._csv_path_var,
            font=FONT_SMALL, fg="#555", bg=PANEL_BG, anchor="w", wraplength=480,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        _make_button(
            csv_row, "Browse…", self._browse_csv, bg=ACCENT, pady=4,
        ).pack(side=tk.RIGHT, padx=(PAD, 0))

        # ---- Start button ----
        _make_button(
            body, "▶  Start Experiment", self._start,
            bg=SUCCESS, font=FONT_HEADING, pady=12,
        ).pack(fill=tk.X, pady=(PAD * 2, PAD))

        # Set the initial auto-generated CSV path
        self._update_csv_path()

    # ------------------------------------------------------------------

    def _build_location_checkboxes(self) -> None:
        """(Re)build the checkbox grid for all body locations — all checked by default."""
        for w in self._loc_checks_frame.winfo_children():
            w.destroy()
        self._location_vars.clear()
        cols = 2
        for i, loc in enumerate(BODY_LOCATIONS.keys()):
            var = tk.BooleanVar(value=True)
            self._location_vars[loc] = var
            tk.Checkbutton(
                self._loc_checks_frame,
                text=loc,
                variable=var,
                bg=PANEL_BG,
                font=FONT_BODY,
                anchor="w",
            ).grid(row=i // cols, column=i % cols, sticky="w", padx=(0, PAD * 2), pady=2)

    def _select_all_locations(self) -> None:
        for var in self._location_vars.values():
            var.set(True)

    def _deselect_all_locations(self) -> None:
        for var in self._location_vars.values():
            var.set(False)

    def _on_exp_type_change(self) -> None:
        """Update Testing Day Nr. when the experiment type radio button changes."""
        if self._exp_type_var.get() == "first":
            self._day_nr_var.set(1)
            self._day_hint.config(text="(1st experiment default)")
        else:
            self._day_nr_var.set(8)
            self._day_hint.config(text="(2nd experiment default)")
        self._update_csv_path()

    def _on_pid_change(self, *_) -> None:
        """Auto-update Testing Day Nr. when participant ID changes."""
        pid = self._pid_var.get().strip()
        if pid:
            suggested = self.app.data_manager.get_next_testing_day_nr(pid)
            self._day_nr_var.set(suggested)
            self._day_hint.config(text=f"(auto-detected: {suggested})")
        else:
            self._day_nr_var.set(1)
            self._day_hint.config(text="")
        self._update_csv_path()

    def _update_csv_path(self) -> None:
        """Refresh the auto-generated CSV path (unless manually set by Browse)."""
        if not self._csv_manually_set:
            pid = self._pid_var.get().strip() or "participant"
            day_nr = self._day_nr_var.get()
            today = self._date_var.get()
            filepath = self.app.data_manager.make_experiment_filepath(
                pid, day_nr, today
            )
            self._csv_path_var.set(filepath)

    def _browse_csv(self) -> None:
        pid = self._pid_var.get().strip() or "participant"
        today = self._date_var.get()
        day_nr = self._day_nr_var.get()
        suggested = f"{pid}_day{day_nr}_{today}.csv"
        filepath = filedialog.asksaveasfilename(
            parent=self,
            title="Choose CSV save location",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=suggested,
            initialdir=self.app.data_manager.data_dir,
        )
        if filepath:
            self._csv_manually_set = True
            self._csv_path_var.set(filepath)

    def _add_custom_location(self) -> None:
        name_dlg = _InputDialog(self, "Custom Location", "Location name:")
        if name_dlg.result is None:
            return
        name = name_dlg.result.strip()
        if not name:
            return
        dist_dlg = _InputDialog(
            self,
            "Custom Distances",
            "Enter distances (mm), comma-separated (e.g. 5,10,15,20):",
        )
        if dist_dlg.result is None:
            return
        try:
            dists = [float(x.strip()) for x in dist_dlg.result.split(",") if x.strip()]
        except ValueError:
            messagebox.showerror("Invalid", "Could not parse distances.", parent=self)
            return
        if not dists:
            messagebox.showerror(
                "Invalid", "At least one distance is required.", parent=self
            )
            return
        BODY_LOCATIONS[name] = {
            "distances": sorted(dists),
            "typical_threshold": "N/A",
            "description": "Custom location",
        }
        # Rebuild checkboxes so the new location appears (checked by default)
        self._build_location_checkboxes()

    def _start(self) -> None:
        pid = self._pid_var.get().strip()
        if not pid:
            messagebox.showwarning(
                "Participant ID", "Please enter a participant ID.", parent=self
            )
            return
        locations = [loc for loc, var in self._location_vars.items() if var.get()]
        if not locations:
            messagebox.showwarning(
                "Locations", "Please select at least one body location.", parent=self
            )
            return
        csv_path = self._csv_path_var.get()
        self.app.start_experiment(
            pid=pid,
            day_nr=self._day_nr_var.get(),
            test_date=self._date_var.get(),
            locations=locations,
            csv_path=csv_path,
        )


# ===========================================================================
# Trial frame
# ===========================================================================

class TrialFrame(tk.Frame):
    """Main experiment screen shown during data collection."""

    def __init__(self, parent: tk.Widget, app: App, session: ExperimentSession, csv_save_path: str) -> None:
        super().__init__(parent, bg=BG)
        self.app = app
        self.session = session
        self._csv_save_path = csv_save_path
        self._build()
        self._refresh()

    def _build(self) -> None:
        # ---------- header bar ----------
        self._header = tk.Frame(self, bg=PRIMARY, padx=PAD, pady=8)
        self._header.pack(fill=tk.X)

        self._header_title = tk.Label(
            self._header, text="", font=FONT_HEADING, fg="white", bg=PRIMARY
        )
        self._header_title.pack(side=tk.LEFT)

        self._header_sub = tk.Label(
            self._header, text="", font=FONT_SMALL, fg=LIGHT, bg=PRIMARY
        )
        self._header_sub.pack(side=tk.RIGHT)

        # ---------- trial info panel ----------
        body = tk.Frame(self, bg=BG, padx=PAD * 2, pady=PAD)
        body.pack(fill=tk.BOTH, expand=True)

        trial_panel = _panel(body)
        trial_panel.pack(fill=tk.BOTH, expand=True, pady=(0, PAD))

        top_row = tk.Frame(trial_panel, bg=PANEL_BG)
        top_row.pack(fill=tk.X, padx=PAD, pady=(PAD, 4))

        self._trial_type_label = tk.Label(
            top_row, text="", font=FONT_SUBHEAD, bg=PANEL_BG
        )
        self._trial_type_label.pack(side=tk.LEFT)

        self._trial_num_label = tk.Label(
            top_row, text="", font=FONT_SMALL, fg="#7f8c8d", bg=PANEL_BG
        )
        self._trial_num_label.pack(side=tk.RIGHT)

        # Distance display
        dist_container = tk.Frame(trial_panel, bg=PANEL_BG)
        dist_container.pack(pady=(PAD, 0))

        _make_label(dist_container, "Apply stimulus at:", font=FONT_BODY, fg="#555").pack()

        self._dist_display = tk.Label(
            dist_container, text="", font=FONT_BIG_NUM, fg=ACCENT, bg=PANEL_BG
        )
        self._dist_display.pack(pady=4)

        self._ct_note = tk.Label(
            dist_container,
            text="⚠  CONTROL TRIAL — apply only ONE point",
            font=FONT_SUBHEAD,
            fg=CT_COLOR,
            bg=PANEL_BG,
        )

        # Custom distance row
        custom_row = tk.Frame(trial_panel, bg=PANEL_BG)
        custom_row.pack(pady=(4, PAD))

        self._use_custom = tk.BooleanVar(value=False)
        tk.Checkbutton(
            custom_row,
            text="Override distance:",
            variable=self._use_custom,
            bg=PANEL_BG,
            font=FONT_SMALL,
            command=self._toggle_custom,
        ).pack(side=tk.LEFT)

        self._custom_dist_var = tk.StringVar()
        self._custom_entry = tk.Entry(
            custom_row,
            textvariable=self._custom_dist_var,
            width=6,
            font=FONT_BODY,
            relief=tk.SOLID,
            bd=1,
            state=tk.DISABLED,
        )
        self._custom_entry.pack(side=tk.LEFT, padx=4)

        tk.Label(custom_row, text="mm", font=FONT_BODY, bg=PANEL_BG).pack(side=tk.LEFT)

        # Separator
        tk.Frame(trial_panel, bg=BORDER, height=1).pack(fill=tk.X, padx=PAD, pady=8)

        # Response buttons
        resp_label = _make_label(trial_panel, "Participant reports:", font=FONT_SUBHEAD)
        resp_label.pack(pady=(0, 8))

        btn_row = tk.Frame(trial_panel, bg=PANEL_BG)
        btn_row.pack(pady=(0, PAD))

        _make_button(
            btn_row,
            "  1 Point  ",
            lambda: self._respond("1"),
            bg=WARN,
            font=("Helvetica", 16, "bold"),
            pady=14, padx=30,
        ).pack(side=tk.LEFT, padx=12)

        _make_button(
            btn_row,
            "  2 Points  ",
            lambda: self._respond("2"),
            bg=SUCCESS,
            font=("Helvetica", 16, "bold"),
            pady=14, padx=30,
        ).pack(side=tk.LEFT, padx=12)

        # ---------- footer ----------
        footer = tk.Frame(self, bg=BG, padx=PAD * 2, pady=6)
        footer.pack(fill=tk.X)

        self._progress_label = tk.Label(
            footer, text="", font=FONT_SMALL, fg="#7f8c8d", bg=BG
        )
        self._progress_label.pack(side=tk.LEFT)

        tk.Label(
            footer,
            text="🔒 Experiment in progress — please complete all trials",
            font=FONT_SMALL,
            fg=WARN,
            bg=BG,
        ).pack(side=tk.RIGHT)

    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        s = self.session
        pid = s.participant_id
        loc = s.location
        trial_num = s.current_trial_number
        is_ct = s.is_next_trial_control
        dist = s.current_distance

        self._header_title.config(
            text=f"Two-Point Discrimination — {loc}"
        )
        total = len(self.app._location_queue)
        current = self.app._current_location_idx
        loc_progress = f"Location {current}/{total} | Participant: {pid}"
        self._header_sub.config(text=loc_progress)

        if is_ct:
            self._trial_type_label.config(
                text="Control Trial (CT)", fg=CT_COLOR
            )
            self._dist_display.pack_forget()
            self._ct_note.pack()
        else:
            self._trial_type_label.config(
                text="Experimental Trial", fg=ACCENT
            )
            self._ct_note.pack_forget()
            self._dist_display.pack(pady=4)
            self._dist_display.config(
                text=f"{dist} mm" if dist is not None else "—"
            )

        self._trial_num_label.config(text=f"Trial #{trial_num}")

        # Progress info
        reversals = s.single_point_counts
        rev_str = "  |  ".join(
            f"{d} mm × {c}" for d, c in sorted(reversals.items())
        ) if reversals else "No reversals yet"
        self._progress_label.config(
            text=f"Reversals: {rev_str}   (stop at 3 for same distance)"
        )

    def _toggle_custom(self) -> None:
        if self._use_custom.get():
            self._custom_entry.config(state=tk.NORMAL)
            self._custom_entry.focus_set()
        else:
            self._custom_entry.config(state=tk.DISABLED)
            self._custom_dist_var.set("")

    def _respond(self, response: str) -> None:
        custom: Optional[float] = None
        if self._use_custom.get():
            raw = self._custom_dist_var.get().strip()
            if not raw:
                messagebox.showwarning(
                    "Distance", "Please enter a custom distance or uncheck the override.",
                    parent=self
                )
                return
            try:
                custom = float(raw)
                if custom <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Invalid distance", "Custom distance must be a positive number.",
                    parent=self
                )
                return

        self.session.record_response(response, custom_distance=custom)

        # Persist the trial immediately so partial data survives an interruption
        if self.session.trials:
            try:
                self.app.data_manager.append_trial_row(
                    self.session, self.session.trials[-1], self._csv_save_path
                )
            except OSError:
                pass  # best-effort — do not block the experiment

        if self.session.done:
            self.app.on_location_complete(self.session)
        else:
            self._use_custom.set(False)
            self._custom_dist_var.set("")
            self._custom_entry.config(state=tk.DISABLED)
            self._refresh()

# ===========================================================================
# Results frame
# ===========================================================================

class ResultsFrame(tk.Frame):
    """Results screen shown when the experiment is complete."""

    def __init__(self, parent: tk.Widget, app: App, session: ExperimentSession, csv_save_path: str) -> None:
        super().__init__(parent, bg=BG)
        self.app = app
        self.session = session
        self.data_manager = DataManager()
        self._csv_save_path = csv_save_path
        self._auto_saved_csv: Optional[str] = None
        self._build()

    def _build(self) -> None:
        summary = self.session.get_summary()

        # ---------- header ----------
        header = tk.Frame(self, bg=SUCCESS, padx=PAD, pady=8)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="✓  Experiment Complete",
            font=FONT_TITLE,
            fg="white",
            bg=SUCCESS,
        ).pack(side=tk.LEFT)
        tk.Label(
            header,
            text=f"Participant: {self.session.participant_id}   |   "
                 f"Location: {self.session.location}",
            font=FONT_SMALL,
            fg=LIGHT,
            bg=SUCCESS,
        ).pack(side=tk.RIGHT)

        # ---------- scrollable body ----------
        canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        body = tk.Frame(canvas, bg=BG)
        canvas_window = canvas.create_window((0, 0), window=body, anchor="nw")

        def _on_resize(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_resize)

        def _on_frame_configure(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        body.bind("<Configure>", _on_frame_configure)

        inner = tk.Frame(body, bg=BG, padx=PAD * 2, pady=PAD)
        inner.pack(fill=tk.BOTH, expand=True)

        # ---------- threshold ----------
        thresh_panel = _panel(inner)
        thresh_panel.pack(fill=tk.X, pady=(0, PAD))

        _make_label(thresh_panel, "Two-Point Discrimination Threshold",
                    font=FONT_HEADING, fg=PRIMARY).pack(pady=(PAD, 0))

        thr = summary.get("threshold_mm")
        thr_text = f"{thr} mm" if thr is not None else "Not determined"
        thr_color = SUCCESS if thr is not None else DANGER

        tk.Label(
            thresh_panel, text=thr_text,
            font=("Helvetica", 48, "bold"), fg=thr_color, bg=PANEL_BG
        ).pack(pady=(4, PAD))

        # ---------- stats ----------
        stats_panel = _panel(inner)
        stats_panel.pack(fill=tk.X, pady=(0, PAD))
        _make_label(stats_panel, "Session Summary", font=FONT_SUBHEAD).pack(anchor="w", padx=PAD, pady=(PAD, 4))

        stats_grid = tk.Frame(stats_panel, bg=PANEL_BG)
        stats_grid.pack(fill=tk.X, padx=PAD, pady=(0, PAD))

        stats_items = [
            ("Test Date",            summary["test_date"]),
            ("Testing Day Nr.",      summary["testing_day_nr"]),
            ("Total trials",         summary["total_trials"]),
            ("Experimental trials",  summary["experimental_trials"]),
            ("Control trials",       summary["control_trials"]),
            ("Control trials correct",
             f"{summary['control_trials_correct']} / {summary['control_trials']}"),
        ]
        for i, (label, value) in enumerate(stats_items):
            tk.Label(
                stats_grid, text=label + ":", font=FONT_BODY,
                fg="#555", bg=PANEL_BG, anchor="e"
            ).grid(row=i, column=0, sticky="e", padx=(0, 8), pady=2)
            tk.Label(
                stats_grid, text=str(value), font=FONT_SUBHEAD,
                fg=PRIMARY, bg=PANEL_BG, anchor="w"
            ).grid(row=i, column=1, sticky="w", pady=2)

        # ---------- per-distance table ----------
        tbl_panel = _panel(inner)
        tbl_panel.pack(fill=tk.X, pady=(0, PAD))
        _make_label(tbl_panel, "Responses by Distance", font=FONT_SUBHEAD).pack(anchor="w", padx=PAD, pady=(PAD, 4))

        cols = ("Distance (mm)", "Times tested", "1 point", "2 points", "Reversals")
        tree = ttk.Treeview(tbl_panel, columns=cols, show="headings", height=min(10, len(summary["responses_by_distance"]) + 1))
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor="center", width=110)

        for d_str, info in sorted(
            summary["responses_by_distance"].items(), key=lambda x: float(x[0])
        ):
            d = float(d_str)
            reversals = self.session.single_point_counts.get(d, 0)
            row_tag = "threshold" if thr is not None and d == thr else ""
            tree.insert("", tk.END, values=(
                d_str,
                len(info["responses"]),
                info["count_1"],
                info["count_2"],
                reversals,
            ))

        # Highlight the threshold row
        tree.tag_configure("threshold", background="#d5f5e3")
        tree.pack(fill=tk.X, padx=PAD, pady=(0, PAD))

        # ---------- graph ----------
        graph_panel = _panel(inner)
        graph_panel.pack(fill=tk.BOTH, expand=True, pady=(0, PAD))
        _make_label(graph_panel, "Response Graph", font=FONT_SUBHEAD).pack(anchor="w", padx=PAD, pady=(PAD, 4))

        self._build_graph(graph_panel, summary)

        # ---------- auto-save CSV ----------
        try:
            self._auto_saved_csv = self.data_manager.export_csv(
                self.session, self._csv_save_path
            )
            csv_status_bg = "#d5f5e3"
            csv_status_text = f"✓  CSV saved to: {self._auto_saved_csv}"
            csv_status_fg = SUCCESS
        except OSError as exc:
            csv_status_bg = "#fdecea"
            csv_status_text = f"⚠  Could not save CSV: {exc}"
            csv_status_fg = DANGER

        csv_info = tk.Frame(inner, bg=csv_status_bg, relief=tk.FLAT, bd=0)
        csv_info.pack(fill=tk.X, pady=(0, PAD))
        tk.Label(
            csv_info,
            text=csv_status_text,
            font=FONT_SMALL,
            fg=csv_status_fg,
            bg=csv_status_bg,
            anchor="w",
            wraplength=700,
            padx=PAD,
            pady=8,
        ).pack(fill=tk.X)

        # ---------- action buttons ----------
        export_panel = tk.Frame(inner, bg=BG)
        export_panel.pack(fill=tk.X, pady=(0, PAD))

        _make_button(export_panel, "⬇  Export JSON", self._export_json, bg=PRIMARY).pack(side=tk.LEFT, padx=(0, PAD))
        _make_button(export_panel, "↩  New Experiment", self.app.show_setup, bg=WARN).pack(side=tk.RIGHT)

    # ------------------------------------------------------------------

    def _build_graph(self, parent: tk.Widget, summary: dict) -> None:
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except ImportError:
            tk.Label(
                parent,
                text="(matplotlib not installed — graph unavailable)",
                font=FONT_SMALL, fg="#999", bg=PANEL_BG
            ).pack(pady=PAD)
            return

        exp_trials = [t for t in self.session.trials if t.trial_type == "experimental"]
        if not exp_trials:
            tk.Label(parent, text="No experimental data to plot.", font=FONT_SMALL, fg="#999", bg=PANEL_BG).pack()
            return

        trial_nums = list(range(1, len(exp_trials) + 1))
        distances = [t.distance for t in exp_trials]
        responses = [1 if t.response == "1" else 2 for t in exp_trials]

        fig, ax = plt.subplots(figsize=(7, 3), dpi=90)
        fig.patch.set_facecolor(PANEL_BG)
        ax.set_facecolor("#f9fafb")

        # Plot distance over time (line)
        ax.plot(trial_nums, distances, color="#aaaaaa", linewidth=1, zorder=1)

        # Colour-code dots by response
        for i, (tn, d, r) in enumerate(zip(trial_nums, distances, responses)):
            color = WARN if r == 1 else SUCCESS
            ax.scatter(tn, d, color=color, s=70, zorder=2)

        # Threshold line
        thr = summary.get("threshold_mm")
        if thr is not None:
            ax.axhline(thr, color=DANGER, linestyle="--", linewidth=1.5, label=f"Threshold: {thr} mm")
            ax.legend(fontsize=9)

        ax.set_xlabel("Experimental trial #", fontsize=10)
        ax.set_ylabel("Distance (mm)", fontsize=10)
        ax.set_title("Staircase: distance vs trial (● orange=1pt, ● green=2pts)", fontsize=10)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=PAD, pady=(0, PAD))
        plt.close(fig)

    # ------------------------------------------------------------------

    def _export_json(self) -> None:
        filepath = filedialog.asksaveasfilename(
            parent=self,
            title="Save JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"{self.session.participant_id}_{self.session.location}.json",
        )
        if not filepath:
            return
        try:
            saved = self.data_manager.export_json(self.session, filepath)
            messagebox.showinfo("Saved", f"JSON saved to:\n{saved}", parent=self)
        except OSError as exc:
            messagebox.showerror("Error", str(exc), parent=self)


# ===========================================================================
# All-results frame (multi-location combined view)
# ===========================================================================

class AllResultsFrame(tk.Frame):
    """Combined results screen displayed after all locations are complete."""

    def __init__(
        self,
        parent: tk.Widget,
        app: "App",
        sessions: List[ExperimentSession],
        csv_save_path: Optional[str],
    ) -> None:
        super().__init__(parent, bg=BG)
        self.app = app
        self.sessions = sessions
        self._csv_save_path = csv_save_path
        self.data_manager = DataManager()
        self._build()

    def _build(self) -> None:
        n = len(self.sessions)
        pid = self.sessions[0].participant_id if self.sessions else ""

        # ---------- header ----------
        header = tk.Frame(self, bg=SUCCESS, padx=PAD, pady=8)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text=f"✓  Experiment Complete — {n} location{'s' if n != 1 else ''}",
            font=FONT_TITLE, fg="white", bg=SUCCESS,
        ).pack(side=tk.LEFT)
        if pid:
            tk.Label(
                header, text=f"Participant: {pid}",
                font=FONT_SMALL, fg=LIGHT, bg=SUCCESS,
            ).pack(side=tk.RIGHT)

        # ---------- scrollable body ----------
        canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        body = tk.Frame(canvas, bg=BG)
        canvas_window = canvas.create_window((0, 0), window=body, anchor="nw")

        def _on_resize(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_resize)

        def _on_frame_configure(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        body.bind("<Configure>", _on_frame_configure)

        inner = tk.Frame(body, bg=BG, padx=PAD * 2, pady=PAD)
        inner.pack(fill=tk.BOTH, expand=True)

        # ---------- summary table ----------
        sum_panel = _panel(inner)
        sum_panel.pack(fill=tk.X, pady=(0, PAD))
        _make_label(sum_panel, "Results Summary", font=FONT_HEADING, fg=PRIMARY).pack(
            anchor="w", padx=PAD, pady=(PAD, 4)
        )

        cols = ("Location", "Threshold (mm)", "Total Trials", "Exp. Trials", "CT Correct")
        tree = ttk.Treeview(
            sum_panel, columns=cols, show="headings",
            height=min(10, max(1, len(self.sessions))),
        )
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor="center", width=130)
        for s in self.sessions:
            summ = s.get_summary()
            thr = summ.get("threshold_mm")
            tree.insert("", tk.END, values=(
                s.location,
                f"{thr} mm" if thr is not None else "Not determined",
                summ["total_trials"],
                summ["experimental_trials"],
                f"{summ['control_trials_correct']} / {summ['control_trials']}",
            ))
        tree.pack(fill=tk.X, padx=PAD, pady=(0, PAD))

        # ---------- CSV status ----------
        if self._csv_save_path:
            csv_bg = "#d5f5e3"
            csv_info = tk.Frame(inner, bg=csv_bg)
            csv_info.pack(fill=tk.X, pady=(0, PAD))
            tk.Label(
                csv_info,
                text=f"✓  CSV saved to: {self._csv_save_path}",
                font=FONT_SMALL, fg=SUCCESS, bg=csv_bg,
                anchor="w", wraplength=700, padx=PAD, pady=8,
            ).pack(fill=tk.X)

        # ---------- per-location detail panels ----------
        for s in self.sessions:
            self._build_location_panel(inner, s)

        # ---------- action buttons ----------
        btn_panel = tk.Frame(inner, bg=BG)
        btn_panel.pack(fill=tk.X, pady=(0, PAD))
        _make_button(
            btn_panel, "↩  New Experiment", self.app.show_setup, bg=WARN,
        ).pack(side=tk.RIGHT)

    def _build_location_panel(
        self, parent: tk.Widget, s: ExperimentSession
    ) -> None:
        """Render a collapsible detail panel for one body location."""
        summ = s.get_summary()
        thr = summ.get("threshold_mm")

        loc_panel = _panel(parent)
        loc_panel.pack(fill=tk.X, pady=(0, PAD))

        hdr = tk.Frame(loc_panel, bg=PANEL_BG)
        hdr.pack(fill=tk.X, padx=PAD, pady=(PAD, 4))
        _make_label(hdr, s.location, font=FONT_SUBHEAD).pack(side=tk.LEFT)
        thr_text = f"Threshold: {thr} mm" if thr is not None else "Threshold: Not determined"
        tk.Label(
            hdr, text=thr_text, font=FONT_SUBHEAD,
            fg=SUCCESS if thr is not None else DANGER, bg=PANEL_BG,
        ).pack(side=tk.RIGHT)

        stats_row = tk.Frame(loc_panel, bg=PANEL_BG)
        stats_row.pack(fill=tk.X, padx=PAD, pady=(0, 4))
        for stat in [
            f"Total: {summ['total_trials']} trials",
            f"Experimental: {summ['experimental_trials']}",
            f"Control: {summ['control_trials']}  ({summ['control_trials_correct']} correct)",
        ]:
            tk.Label(
                stats_row, text=stat, font=FONT_SMALL, fg="#555",
                bg=PANEL_BG, padx=8,
            ).pack(side=tk.LEFT)

        # Per-distance response table
        rbd = summ.get("responses_by_distance", {})
        if rbd:
            cols = ("Distance (mm)", "Times tested", "1 point", "2 points", "Reversals")
            tbl = ttk.Treeview(
                loc_panel, columns=cols, show="headings",
                height=min(8, len(rbd) + 1),
            )
            for c in cols:
                tbl.heading(c, text=c)
                tbl.column(c, anchor="center", width=100)
            for d_str, info in sorted(rbd.items(), key=lambda x: float(x[0])):
                d = float(d_str)
                revs = s.single_point_counts.get(d, 0)
                tbl.insert("", tk.END, values=(
                    d_str,
                    len(info["responses"]),
                    info["count_1"],
                    info["count_2"],
                    revs,
                ))
            tbl.pack(fill=tk.X, padx=PAD, pady=(0, PAD))

        # Optional staircase graph
        self._build_graph(loc_panel, s, summ)

    def _build_graph(
        self, parent: tk.Widget, s: ExperimentSession, summary: dict
    ) -> None:
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except ImportError:
            return

        exp_trials = [t for t in s.trials if t.trial_type == "experimental"]
        if not exp_trials:
            return

        trial_nums = list(range(1, len(exp_trials) + 1))
        distances = [t.distance for t in exp_trials]

        fig, ax = plt.subplots(figsize=(6, 2.5), dpi=90)
        fig.patch.set_facecolor(PANEL_BG)
        ax.set_facecolor("#f9fafb")
        ax.plot(trial_nums, distances, color="#aaaaaa", linewidth=1, zorder=1)
        for tn, d, t in zip(trial_nums, distances, exp_trials):
            ax.scatter(tn, d, color=WARN if t.response == "1" else SUCCESS, s=60, zorder=2)

        thr = summary.get("threshold_mm")
        if thr is not None:
            ax.axhline(
                thr, color=DANGER, linestyle="--", linewidth=1.5,
                label=f"Threshold: {thr} mm",
            )
            ax.legend(fontsize=8)

        ax.set_xlabel("Experimental trial #", fontsize=9)
        ax.set_ylabel("Distance (mm)", fontsize=9)
        ax.set_title(
            f"{s.location}: staircase (● orange=1pt, ● green=2pts)", fontsize=9
        )
        fig.tight_layout()

        graph_canvas = FigureCanvasTkAgg(fig, master=parent)
        graph_canvas.draw()
        graph_canvas.get_tk_widget().pack(
            fill=tk.BOTH, expand=True, padx=PAD, pady=(0, PAD)
        )
        plt.close(fig)


# ===========================================================================
# Simple input dialog
# ===========================================================================

class _InputDialog(tk.Toplevel):
    """A minimal modal input dialog."""

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        prompt: str,
        validate: str = "str",
    ) -> None:
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.result: Optional[str] = None

        tk.Label(self, text=prompt, font=FONT_BODY, padx=PAD, pady=PAD).pack()
        self._var = tk.StringVar()
        entry = tk.Entry(self, textvariable=self._var, font=FONT_BODY, width=26)
        entry.pack(padx=PAD, pady=(0, PAD))
        entry.focus_set()
        entry.bind("<Return>", lambda _: self._ok())

        btn_row = tk.Frame(self)
        btn_row.pack(pady=(0, PAD))
        _make_button(btn_row, "OK", self._ok, bg=ACCENT, pady=4).pack(side=tk.LEFT, padx=6)
        _make_button(btn_row, "Cancel", self.destroy, bg=BORDER, fg=PRIMARY, pady=4).pack(side=tk.LEFT, padx=6)

        self.wait_window(self)

    def _ok(self) -> None:
        self.result = self._var.get().strip()
        self.destroy()
