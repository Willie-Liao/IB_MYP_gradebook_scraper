#!/usr/bin/env python3
"""GUI entry point for ManageBac Gradebook Scraper."""

from __future__ import annotations

import logging
import os
import re
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# Support `python src/gui.py` (IDE Run) as well as `python -m src.gui`
if __package__ in (None, ""):
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    __package__ = "src"

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(_PROJECT_ROOT / ".env")


_load_dotenv()

from .exceptions import AuthenticationError, ScraperError
from .excel_exporter import ExcelExporter
from .models import GradebookData, Student, TermGrade
from .scraper import GradebookScraper
from .student_picker import filter_gradebook_data


DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Downloads")


class GradebookScraperGUI:
    """GUI for ManageBac login, scrape, student selection, and export."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("ManageBac Gradebook Scraper")
        self.root.geometry("700x700")

        self.gradebook_data: GradebookData | None = None
        self.student_vars: dict[str, tk.BooleanVar] = {}
        self._mousewheel_handler = None

        self.create_login_frame()
        self.create_student_frame()
        self.create_status_frame()

        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            handlers=[logging.StreamHandler(sys.stderr)],
        )

    def create_login_frame(self) -> None:
        """Create the login/URL input section."""
        frame = ttk.LabelFrame(self.root, text="Task Configuration", padding=10)
        frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame, text="Gradebook URL:").grid(row=0, column=0, sticky="w", pady=2)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(frame, textvariable=self.url_var, width=70)
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky="ew", pady=2)

        ttk.Label(frame, text="Email:").grid(row=1, column=0, sticky="w", pady=2)
        self.email_var = tk.StringVar(value=os.environ.get("MANAGEBAC_EMAIL", ""))
        self.email_entry = ttk.Entry(frame, textvariable=self.email_var, width=40)
        self.email_entry.grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Password:").grid(row=2, column=0, sticky="w", pady=2)
        self.password_var = tk.StringVar(value=os.environ.get("MANAGEBAC_PASSWORD", ""))
        self.password_entry = ttk.Entry(frame, textvariable=self.password_var, width=40, show="*")
        self.password_entry.grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Output Dir:").grid(row=3, column=0, sticky="w", pady=2)
        self.output_var = tk.StringVar(value=DEFAULT_OUTPUT_DIR)
        self.output_entry = ttk.Entry(frame, textvariable=self.output_var, width=50)
        self.output_entry.grid(row=3, column=1, sticky="ew", pady=2)
        ttk.Button(frame, text="Browse", command=self.browse_output).grid(row=3, column=2, padx=5)

        self.fetch_btn = ttk.Button(frame, text="Fetch Students", command=self.fetch_students)
        self.fetch_btn.grid(row=4, column=1, pady=10)

        frame.columnconfigure(1, weight=1)

    def create_student_frame(self) -> None:
        """Create the student selection section."""
        frame = ttk.LabelFrame(self.root, text="Select Students to Export", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Select All", command=self.select_all).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Select None", command=self.select_none).pack(side="left", padx=5)

        ttk.Label(btn_frame, text="Search:").pack(side="left", padx=(20, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.filter_students())
        self.search_entry = ttk.Entry(btn_frame, textvariable=self.search_var, width=25)
        self.search_entry.pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear", command=self.clear_search).pack(side="left", padx=5)

        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        self.student_list_frame = ttk.Frame(canvas)

        self.student_list_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas_window = canvas.create_window(
            (0, 0), window=self.student_list_frame, anchor="nw", width=canvas.winfo_width()
        )

        def on_canvas_resize(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", on_canvas_resize)
        canvas.configure(yscrollcommand=scrollbar.set)

        def on_mousewheel(event):
            if abs(event.delta) < 120:
                scroll_units = -event.delta
            else:
                scroll_units = int(-event.delta / 120) * 3
            canvas.yview_scroll(scroll_units, "units")

        canvas.focus_set()
        canvas.bind("<Enter>", lambda e: canvas.focus_set())
        canvas.bind("<MouseWheel>", on_mousewheel)
        self.student_list_frame.bind("<MouseWheel>", on_mousewheel)
        self._mousewheel_handler = on_mousewheel

        bottom_btn_frame = ttk.Frame(frame)
        bottom_btn_frame.pack(side="bottom", fill="x", pady=10)

        self.export_btn = ttk.Button(
            bottom_btn_frame,
            text="Export Selected",
            command=self.export_selected,
            state="disabled",
        )
        self.export_btn.pack(side="left", padx=5)

        canvas.pack(side="left", fill="both", expand=True, pady=10)
        scrollbar.pack(side="right", fill="y")

    def create_status_frame(self) -> None:
        """Create the status/log section."""
        frame = ttk.LabelFrame(self.root, text="Status", padding=10)
        frame.pack(fill="x", padx=10, pady=5)

        self.status_label = ttk.Label(frame, text="Enter gradebook URL and click 'Fetch Students'")
        self.status_label.pack()

        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.pack(fill="x", pady=5)

    def browse_output(self) -> None:
        directory = filedialog.askdirectory()
        if directory:
            self.output_var.set(directory)

    def set_status(self, text: str) -> None:
        self.status_label.config(text=text)
        self.root.update()

    def fetch_students(self) -> None:
        url = self.url_var.get().strip()
        email = self.email_var.get().strip()
        password = self.password_var.get()

        if not url:
            messagebox.showerror("Error", "Please enter a gradebook URL")
            return
        if not email:
            messagebox.showerror("Error", "Please enter your email")
            return
        if not password:
            messagebox.showerror("Error", "Please enter your password")
            return

        self.fetch_btn.config(state="disabled")
        self.export_btn.config(state="disabled")
        self.progress.start()
        self.set_status("Logging in...")

        thread = threading.Thread(
            target=self._fetch_students_thread,
            args=(url, email, password),
            daemon=True,
        )
        thread.start()

    def _fetch_students_thread(self, url: str, email: str, password: str) -> None:
        try:
            scraper = GradebookScraper.from_gradebook_url(url, email, password)
            self.root.after(0, lambda: self.set_status("Fetching term grades and tasks..."))
            scraper.authenticate()
            gradebook_data = scraper.fetch_data(url)
            self.root.after(0, lambda: self._populate_student_list(gradebook_data))
        except AuthenticationError as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Authentication failed: {e}"))
            self.root.after(0, lambda: self.set_status("Authentication failed"))
        except ScraperError as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Scraping failed: {e}"))
            self.root.after(0, lambda: self.set_status("Scraping failed"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.set_status("Error occurred"))
        finally:
            self.root.after(0, lambda: self.fetch_btn.config(state="normal"))
            self.root.after(0, self.progress.stop)

    def _term_grade_for(self, student: Student) -> TermGrade | None:
        if not self.gradebook_data:
            return None
        for tg in self.gradebook_data.term_grades:
            if tg.student_name == student.name:
                return tg
        return None

    def _student_checkbox_text(self, student: Student) -> str:
        tg = self._term_grade_for(student)
        if not tg:
            return student.name

        parts = [f"grade: {tg.grade}"]
        criteria = []
        for label, value in (
            ("A", tg.criterion_a),
            ("B", tg.criterion_b),
            ("C", tg.criterion_c),
            ("D", tg.criterion_d),
        ):
            if value:
                criteria.append(f"{label}:{value}")
        if criteria:
            parts.append(", ".join(criteria))
        return f"{student.name} ({', '.join(parts)})"

    def _populate_student_list(self, gradebook_data: GradebookData) -> None:
        for widget in self.student_list_frame.winfo_children():
            widget.destroy()
        self.student_vars.clear()
        self.gradebook_data = gradebook_data

        if not gradebook_data.students:
            ttk.Label(self.student_list_frame, text="No students found").pack()
            self.set_status("No students found")
            return

        for student in gradebook_data.students:
            var = tk.BooleanVar(value=True)
            self.student_vars[student.id] = var
            cb = ttk.Checkbutton(
                self.student_list_frame,
                text=self._student_checkbox_text(student),
                variable=var,
            )
            cb.pack(fill="x", anchor="w", pady=2)
            if self._mousewheel_handler:
                cb.bind("<MouseWheel>", self._mousewheel_handler)

        self.export_btn.config(state="normal")
        self.set_status(f"Found {len(gradebook_data.students)} students")

    def select_all(self) -> None:
        for var in self.student_vars.values():
            var.set(True)

    def select_none(self) -> None:
        for var in self.student_vars.values():
            var.set(False)

    def clear_search(self) -> None:
        self.search_var.set("")

    def filter_students(self) -> None:
        search_text = self.search_var.get().lower()
        for widget in self.student_list_frame.winfo_children():
            if isinstance(widget, ttk.Checkbutton):
                student_text = widget.cget("text").lower()
                if search_text in student_text:
                    widget.pack(anchor="w", pady=2)
                else:
                    widget.pack_forget()

    def export_selected(self) -> None:
        if not self.gradebook_data:
            messagebox.showwarning("Warning", "No gradebook data loaded")
            return

        selected_ids = {sid for sid, var in self.student_vars.items() if var.get()}
        if not selected_ids:
            messagebox.showwarning("Warning", "No students selected")
            return

        output_dir = self.output_var.get().strip()
        if not output_dir:
            messagebox.showerror("Error", "Please specify output directory")
            return

        filtered = filter_gradebook_data(self.gradebook_data, selected_ids)
        filename = self._export_filename(filtered)
        output_path = os.path.join(output_dir, filename)

        self.export_btn.config(state="disabled")
        self.fetch_btn.config(state="disabled")
        self.progress.start()
        self.set_status("Exporting...")

        thread = threading.Thread(
            target=self._export_thread,
            args=(filtered, output_path),
            daemon=True,
        )
        thread.start()

    def _export_filename(self, data: GradebookData) -> str:
        class_part = self._safe_filename_part(data.class_name or "class")
        term_part = self._safe_filename_part(data.term_name or "term")
        return f"{class_part}_{term_part}_gradebook.xlsx"

    @staticmethod
    def _safe_filename_part(value: str) -> str:
        cleaned = str(value).strip().replace(" ", "_")
        return re.sub(r"(?u)[^-\w.]", "", cleaned) or "export"

    def _export_thread(self, data: GradebookData, output_path: str) -> None:
        try:
            saved = ExcelExporter.export(data, output_path)
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Complete",
                    f"Export complete!\n\nStudents exported: {len(data.students)}\n\n{saved}",
                ),
            )
            self.root.after(0, lambda: self.set_status(f"Exported to: {saved}"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.set_status("Export failed"))
        finally:
            self.root.after(0, lambda: self.export_btn.config(state="normal"))
            self.root.after(0, lambda: self.fetch_btn.config(state="normal"))
            self.root.after(0, self.progress.stop)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    GradebookScraperGUI().run()


if __name__ == "__main__":
    main()
