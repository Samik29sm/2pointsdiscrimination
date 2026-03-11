"""Tkinter GUI for the Two-Point Discrimination Experiment tool."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

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
        self.geometry("860x640")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(720, 540)

        self.data_manager = DataManager()
        self.session: Optional[ExperimentSession] = None

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

    def show_trial(self, session: ExperimentSession) -> None:
        self.session = session
        self._replace(TrialFrame(self._container, self, session))

    def show_results(self, session: ExperimentSession) -> None:
        self._replace(ResultsFrame(self._container, self, session))


# ===========================================================================
# Setup frame
# ===========================================================================

class SetupFrame(tk.Frame):
    """Initial screen: participant ID, location, distances."""

    def __init__(self, parent: tk.Widget, app: App) -> None:
        super().__init__(parent, bg=BG)
        self.app = app
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

        # ---------- body ----------
        body = tk.Frame(self, bg=BG, padx=PAD * 2, pady=PAD)
        body.pack(fill=tk.BOTH, expand=True)

        # Participant ID
        pid_panel = _panel(body)
        pid_panel.pack(fill=tk.X, pady=(PAD, 6))
        _make_label(pid_panel, "Participant ID", font=FONT_SUBHEAD).pack(anchor="w", padx=PAD, pady=(PAD, 2))
        self._pid_var = tk.StringVar()
        pid_entry = tk.Entry(
            pid_panel, textvariable=self._pid_var, font=FONT_BODY,
            relief=tk.SOLID, bd=1
        )
        pid_entry.pack(fill=tk.X, padx=PAD, pady=(0, PAD))
        pid_entry.focus_set()

        # Location selection
        loc_panel = _panel(body)
        loc_panel.pack(fill=tk.X, pady=6)
        _make_label(loc_panel, "Body Location", font=FONT_SUBHEAD).pack(anchor="w", padx=PAD, pady=(PAD, 2))

        loc_row = tk.Frame(loc_panel, bg=PANEL_BG)
        loc_row.pack(fill=tk.X, padx=PAD, pady=(0, 4))

        self._loc_var = tk.StringVar(value=DEFAULT_LOCATION)
        loc_combo = ttk.Combobox(
            loc_row,
            textvariable=self._loc_var,
            values=list(BODY_LOCATIONS.keys()),
            state="readonly",
            font=FONT_BODY,
            width=20,
        )
        loc_combo.pack(side=tk.LEFT)
        loc_combo.bind("<<ComboboxSelected>>", self._on_location_change)

        _make_button(
            loc_row, "+ Custom Location", self._add_custom_location,
            bg=WARN, pady=4
        ).pack(side=tk.LEFT, padx=(PAD, 0))

        self._loc_desc_var = tk.StringVar()
        tk.Label(
            loc_panel, textvariable=self._loc_desc_var,
            font=FONT_SMALL, fg="#7f8c8d", bg=PANEL_BG, anchor="w"
        ).pack(fill=tk.X, padx=PAD, pady=(0, PAD))

        # Distances
        dist_panel = _panel(body)
        dist_panel.pack(fill=tk.X, pady=6)
        dist_header = tk.Frame(dist_panel, bg=PANEL_BG)
        dist_header.pack(fill=tk.X, padx=PAD, pady=(PAD, 4))
        _make_label(dist_header, "Test Distances (mm)", font=FONT_SUBHEAD).pack(side=tk.LEFT)
        _make_button(
            dist_header, "+ Add Distance", self._add_distance,
            bg=SUCCESS, pady=4
        ).pack(side=tk.RIGHT)

        self._dist_frame = tk.Frame(dist_panel, bg=PANEL_BG)
        self._dist_frame.pack(fill=tk.X, padx=PAD, pady=(0, PAD))

        self._typical_var = tk.StringVar()
        tk.Label(
            dist_panel, textvariable=self._typical_var,
            font=FONT_SMALL, fg="#7f8c8d", bg=PANEL_BG, anchor="w"
        ).pack(fill=tk.X, padx=PAD, pady=(0, PAD))

        # Start button
        _make_button(
            body, "▶  Start Experiment", self._start,
            bg=SUCCESS, font=FONT_HEADING, pady=12
        ).pack(fill=tk.X, pady=(PAD * 2, PAD))

        self._refresh_location()

    # ------------------------------------------------------------------

    def _on_location_change(self, _event=None) -> None:
        self._refresh_location()

    def _refresh_location(self) -> None:
        loc = self._loc_var.get()
        info = BODY_LOCATIONS.get(loc, {})
        self._loc_desc_var.set(info.get("description", ""))
        self._typical_var.set(
            f"Typical threshold: {info.get('typical_threshold', 'N/A')}"
        )
        self._distances = list(info.get("distances", []))
        self._render_distances()

    def _render_distances(self) -> None:
        for w in self._dist_frame.winfo_children():
            w.destroy()
        for d in sorted(self._distances):
            tk.Label(
                self._dist_frame,
                text=f"{d} mm",
                font=FONT_SMALL,
                bg=LIGHT,
                fg=PRIMARY,
                relief=tk.FLAT,
                padx=8, pady=4,
            ).pack(side=tk.LEFT, padx=3, pady=2)

    def _add_distance(self) -> None:
        dlg = _InputDialog(self, "Add Distance", "Enter distance in mm:", validate="float")
        if dlg.result is None:
            return
        val = float(dlg.result)
        if val <= 0:
            messagebox.showerror("Invalid", "Distance must be positive.", parent=self)
            return
        if val not in self._distances:
            self._distances.append(val)
        self._render_distances()

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
            messagebox.showerror("Invalid", "At least one distance is required.", parent=self)
            return
        BODY_LOCATIONS[name] = {
            "distances": sorted(dists),
            "typical_threshold": "N/A",
            "description": "Custom location",
        }
        # Refresh combobox in-place
        self._loc_var.set(name)
        self._refresh_location()

    def _start(self) -> None:
        pid = self._pid_var.get().strip()
        if not pid:
            messagebox.showwarning("Participant ID", "Please enter a participant ID.", parent=self)
            return
        if not self._distances:
            messagebox.showwarning("Distances", "No distances defined for this location.", parent=self)
            return
        session = ExperimentSession(pid, self._loc_var.get(), self._distances)
        self.app.show_trial(session)


# ===========================================================================
# Trial frame
# ===========================================================================

class TrialFrame(tk.Frame):
    """Main experiment screen shown during data collection."""

    def __init__(self, parent: tk.Widget, app: App, session: ExperimentSession) -> None:
        super().__init__(parent, bg=BG)
        self.app = app
        self.session = session
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

        _make_button(
            footer, "✕  Cancel", self._cancel,
            bg=DANGER, pady=4
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
        self._header_sub.config(text=f"Participant: {pid}")

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

        if self.session.done:
            self.app.show_results(self.session)
        else:
            self._use_custom.set(False)
            self._custom_dist_var.set("")
            self._custom_entry.config(state=tk.DISABLED)
            self._refresh()

    def _cancel(self) -> None:
        if messagebox.askyesno("Cancel", "Cancel the experiment and return to setup?", parent=self):
            self.app.show_setup()


# ===========================================================================
# Results frame
# ===========================================================================

class ResultsFrame(tk.Frame):
    """Results screen shown when the experiment is complete."""

    def __init__(self, parent: tk.Widget, app: App, session: ExperimentSession) -> None:
        super().__init__(parent, bg=BG)
        self.app = app
        self.session = session
        self.data_manager = DataManager()
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

        # ---------- export buttons ----------
        export_panel = tk.Frame(inner, bg=BG)
        export_panel.pack(fill=tk.X, pady=(0, PAD))

        _make_button(export_panel, "⬇  Export CSV", self._export_csv, bg=ACCENT).pack(side=tk.LEFT, padx=(0, PAD))
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

    def _export_csv(self) -> None:
        filepath = filedialog.asksaveasfilename(
            parent=self,
            title="Save CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"{self.session.participant_id}_{self.session.location}.csv",
        )
        if not filepath:
            return
        try:
            saved = self.data_manager.export_csv(self.session, filepath)
            messagebox.showinfo("Saved", f"CSV saved to:\n{saved}", parent=self)
        except OSError as exc:
            messagebox.showerror("Error", str(exc), parent=self)

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
