#!/usr/bin/env python3
"""Main entry point for ManageBac Gradebook Scraper.

This script provides a command-line interface for scraping gradebook data
from ManageBac and exporting it to Excel.

Usage:
    python -m src.main <school_code> <email> <password> <gradebook_url> [--output <path>]

Example:
    python -m src.main myschool teacher@school.edu password123 \\
        "https://myschool.managebac.cn/classes/12345/gradebook/67890"

Requirements: All
"""

import argparse
import logging
import sys
import tkinter as tk
from tkinter import ttk
from getpass import getpass
from typing import Optional

from tqdm import tqdm

from .exceptions import AuthenticationError, ScraperError
from .scraper import GradebookScraper
from .models import GradebookData, Student
from .excel_exporter import ExcelExporter


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application.
    
    Args:
        verbose: If True, set logging level to DEBUG
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr)
        ]
    )


class StudentSelectionWindow:
    """Window for selecting which students to include in the export."""
    
    def __init__(self, students: list[Student]):
        self.students = students
        self.selected_ids: set[str] = set()
        self.result: Optional[set[str]] = None
        
        self.root = tk.Tk()
        self.root.title("Select Students")
        self.root.geometry("400x500")
        self.root.resizable(True, True)
        
        # Center the window
        self.root.eval('tk::PlaceWindow . center')
        
        self._create_widgets()
    
    def _create_widgets(self) -> None:
        """Create all GUI widgets."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Select Students to Export",
            font=("Helvetica", 14, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Search box
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Select all / Deselect all buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            button_frame,
            text="Select All",
            command=self._select_all
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Deselect All",
            command=self._deselect_all
        ).pack(side=tk.LEFT, padx=5)
        
        # Scrollable frame for checkboxes
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Make canvas expand to fill width
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind mouse wheel scrolling globally for macOS
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Create checkboxes for each student
        self.checkbox_vars: dict[str, tk.BooleanVar] = {}
        self.student_checkboxes: dict[str, ttk.Checkbutton] = {}
        
        for student in self.students:
            var = tk.BooleanVar(value=True)
            self.checkbox_vars[student.id] = var
            
            cb = ttk.Checkbutton(
                self.scrollable_frame,
                text=student.name,
                variable=var
            )
            cb.pack(anchor=tk.W, pady=2)
            self.student_checkboxes[student.id] = cb
        
        # Export button
        export_frame = ttk.Frame(main_frame)
        export_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            export_frame,
            text="Export Selected",
            command=self._export
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            export_frame,
            text="Cancel",
            command=self._cancel
        ).pack(side=tk.RIGHT, padx=5)
    
    def _on_canvas_configure(self, event) -> None:
        """Resize the scrollable frame when canvas is resized."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _on_mousewheel(self, event) -> None:
        """Handle mouse wheel scrolling for macOS."""
        self.canvas.yview_scroll(int(-1 * event.delta), "units")
    
    def _on_search_changed(self, *args) -> None:
        """Filter displayed students based on search text."""
        search_text = self.search_var.get().lower().strip()
        
        for student in self.students:
            cb = self.student_checkboxes[student.id]
            if not search_text or search_text in student.name.lower():
                cb.pack(anchor=tk.W, pady=2)
            else:
                cb.pack_forget()
        
        # Reset scroll position to top
        self.canvas.yview_moveto(0)
    
    def _select_all(self) -> None:
        """Select all students (including hidden ones)."""
        for student_id, var in self.checkbox_vars.items():
            var.set(True)
    
    def _deselect_all(self) -> None:
        """Deselect all students (including hidden ones)."""
        for student_id, var in self.checkbox_vars.items():
            var.set(False)
    
    def _export(self) -> None:
        """Export selected students and close window."""
        self.result = {
            student_id
            for student_id, var in self.checkbox_vars.items()
            if var.get()
        }
        self.root.destroy()
    
    def _cancel(self) -> None:
        """Cancel and close window."""
        self.result = None
        self.root.destroy()
    
    def run(self) -> Optional[set[str]]:
        """Run the window and return selected student IDs."""
        self.root.mainloop()
        return self.result


def filter_gradebook_data(data: GradebookData, selected_ids: set[str]) -> GradebookData:
    """Filter gradebook data to only include selected students.
    
    Args:
        data: Original gradebook data
        selected_ids: Set of student IDs to include
        
    Returns:
        Filtered GradebookData
    """
    # Filter students
    filtered_students = [s for s in data.students if s.id in selected_ids]
    
    # Get selected student names for term grade filtering
    selected_names = {s.name for s in filtered_students}
    
    # Filter scores
    filtered_scores = [s for s in data.scores if s.student_id in selected_ids]
    
    # Filter term grades
    filtered_term_grades = [tg for tg in data.term_grades if tg.student_name in selected_names]
    
    return GradebookData(
        students=filtered_students,
        tasks=data.tasks,  # Keep all tasks
        scores=filtered_scores,
        term_grades=filtered_term_grades,
        class_name=data.class_name,
        term_name=data.term_name
    )


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application.
    
    Args:
        verbose: If True, set logging level to DEBUG
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr)
        ]
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Scrape gradebook data from ManageBac and export to Excel.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage with all arguments
    python -m src.main myschool teacher@school.edu password123 \\
        "https://myschool.managebac.cn/classes/12345/gradebook/67890"
    
    # Prompt for password (more secure)
    python -m src.main myschool teacher@school.edu --prompt-password \\
        "https://myschool.managebac.cn/classes/12345/gradebook/67890"
    
    # Specify output file
    python -m src.main myschool teacher@school.edu password123 \\
        "https://myschool.managebac.cn/classes/12345/gradebook/67890" \\
        --output grades.xlsx
        """
    )
    
    parser.add_argument(
        "school_code",
        help="School's ManageBac subdomain code (e.g., 'myschool' for myschool.managebac.cn)"
    )
    
    parser.add_argument(
        "email",
        help="Your ManageBac email address"
    )
    
    parser.add_argument(
        "password",
        nargs="?",
        default=None,
        help="Your ManageBac password (omit to use --prompt-password)"
    )
    
    parser.add_argument(
        "gradebook_url",
        help="Full URL of the gradebook page to scrape"
    )
    
    parser.add_argument(
        "--output", "-o",
        dest="output_path",
        default=None,
        help="Output Excel file path (default: auto-generated)"
    )
    
    parser.add_argument(
        "--prompt-password", "-p",
        action="store_true",
        help="Prompt for password securely instead of passing on command line"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args()


def main() -> int:
    """Main entry point for the scraper.
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    args = parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Get password
    password = args.password
    if args.prompt_password or password is None:
        password = getpass("Enter your ManageBac password: ")
    
    if not password:
        tqdm.write("Error: Password is required")
        return 1
    
    try:
        # Create scraper and run
        tqdm.write("=" * 60)
        tqdm.write("ManageBac Gradebook Scraper")
        tqdm.write("=" * 60)
        
        scraper = GradebookScraper(
            school_code=args.school_code,
            email=args.email,
            password=password
        )
        
        # Authenticate
        scraper.authenticate()
        
        # Fetch data (without exporting yet)
        gradebook_data = scraper.fetch_data(gradebook_url=args.gradebook_url)
        
        # Show student selection window
        tqdm.write("Opening student selection window...")
        selection_window = StudentSelectionWindow(gradebook_data.students)
        selected_ids = selection_window.run()
        
        if selected_ids is None:
            tqdm.write("Export cancelled by user")
            return 0
        
        if not selected_ids:
            tqdm.write("No students selected. Export cancelled.")
            return 0
        
        tqdm.write(f"Selected {len(selected_ids)} students for export")
        
        # Filter data to only include selected students
        filtered_data = filter_gradebook_data(gradebook_data, selected_ids)
        
        # Export to Excel
        tqdm.write("Exporting to Excel...")
        output_file = ExcelExporter.export(filtered_data, args.output_path)
        
        tqdm.write("=" * 60)
        tqdm.write(f"Success! Gradebook exported to: {output_file}")
        tqdm.write("=" * 60)
        
        return 0
        
    except AuthenticationError as e:
        tqdm.write(f"Authentication failed: {e}")
        return 2
        
    except ScraperError as e:
        tqdm.write(f"Scraping failed: {e}")
        return 3
        
    except KeyboardInterrupt:
        tqdm.write("\nOperation cancelled by user")
        return 130
        
    except Exception as e:
        logging.exception("Unexpected error occurred")
        tqdm.write(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
