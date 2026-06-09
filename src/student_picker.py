"""Student selection GUI and gradebook filtering."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from .models import GradebookData, Student


class StudentSelectionWindow:
    """Window for selecting which students to include in the export."""

    def __init__(self, students: list[Student]):
        self.students = students
        self.result: Optional[set[str]] = None

        self.root = tk.Tk()
        self.root.title("Select Students")
        self.root.geometry("400x500")
        self.root.resizable(True, True)
        self.root.eval("tk::PlaceWindow . center")
        self._create_widgets()

    def _create_widgets(self) -> None:
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            main_frame,
            text="Select Students to Export",
            font=("Helvetica", 14, "bold"),
        ).pack(pady=(0, 10))

        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)
        ttk.Entry(search_frame, textvariable=self.search_var, width=30).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(button_frame, text="Select All", command=self._select_all).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Deselect All", command=self._deselect_all).pack(
            side=tk.LEFT, padx=5
        )

        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

        self.checkbox_vars: dict[str, tk.BooleanVar] = {}
        self.student_checkboxes: dict[str, ttk.Checkbutton] = {}
        for student in self.students:
            var = tk.BooleanVar(value=True)
            self.checkbox_vars[student.id] = var
            cb = ttk.Checkbutton(self.scrollable_frame, text=student.name, variable=var)
            cb.pack(anchor=tk.W, pady=2)
            self.student_checkboxes[student.id] = cb

        export_frame = ttk.Frame(main_frame)
        export_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(export_frame, text="Export Selected", command=self._export).pack(
            side=tk.RIGHT, padx=5
        )
        ttk.Button(export_frame, text="Cancel", command=self._cancel).pack(
            side=tk.RIGHT, padx=5
        )

    def _on_canvas_configure(self, event) -> None:
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event) -> None:
        self.canvas.yview_scroll(int(-1 * event.delta), "units")

    def _on_search_changed(self, *args) -> None:
        search_text = self.search_var.get().lower().strip()
        for student in self.students:
            cb = self.student_checkboxes[student.id]
            if not search_text or search_text in student.name.lower():
                cb.pack(anchor=tk.W, pady=2)
            else:
                cb.pack_forget()
        self.canvas.yview_moveto(0)

    def _select_all(self) -> None:
        for var in self.checkbox_vars.values():
            var.set(True)

    def _deselect_all(self) -> None:
        for var in self.checkbox_vars.values():
            var.set(False)

    def _export(self) -> None:
        self.result = {
            student_id for student_id, var in self.checkbox_vars.items() if var.get()
        }
        self.root.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.root.destroy()

    def run(self) -> Optional[set[str]]:
        self.root.mainloop()
        return self.result


def filter_gradebook_data(data: GradebookData, selected_ids: set[str]) -> GradebookData:
    filtered_students = [s for s in data.students if s.id in selected_ids]
    selected_names = {s.name for s in filtered_students}
    filtered_scores = [s for s in data.scores if s.student_id in selected_ids]
    filtered_term_grades = [
        tg for tg in data.term_grades if tg.student_name in selected_names
    ]
    return GradebookData(
        students=filtered_students,
        tasks=data.tasks,
        scores=filtered_scores,
        term_grades=filtered_term_grades,
        class_name=data.class_name,
        term_name=data.term_name,
    )
