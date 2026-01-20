# ManageBac Gradebook Scraper

A Python tool for scraping gradebook data from ManageBac and exporting it to Excel format with student selection capabilities.

## Features

- 🔐 Secure authentication with ManageBac
- 📊 Export gradebook data to Excel with organized columns
- 👥 Interactive student selection GUI
- 📝 Automatic comment extraction
- 🎯 Criterion-based score organization (A, B, C, D)
- 📈 Term grade inclusion
- 🔄 Session management with auto-reauthentication

## Requirements

- Python 3.10 or higher
- ManageBac account with teacher access
- Internet connection

## Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python3 -m src.main <school_code> <email> <password> <gradebook_url>
```

### Parameters

- `school_code`: Your school's ManageBac subdomain (e.g., `myschool` for `myschool.managebac.cn`)
- `email`: Your ManageBac email address
- `password`: Your ManageBac password (optional if using `--prompt-password`)
- `gradebook_url`: Full URL of the gradebook page to scrape

### Examples

**Basic usage with all arguments:**
```bash
python3 -m src.main myschool teacher@school.edu password123 \
    "https://myschool.managebac.cn/teacher/classes/12345/gradebook/term/67890/tasks"
```

**Prompt for password (more secure):**
```bash
python3 -m src.main myschool teacher@school.edu --prompt-password \
    "https://myschool.managebac.cn/teacher/classes/12345/gradebook/term/67890/tasks"
```

**Specify custom output file:**
```bash
python3 -m src.main myschool teacher@school.edu password123 \
    "https://myschool.managebac.cn/teacher/classes/12345/gradebook/term/67890/tasks" \
    --output my_grades.xlsx
```

**Enable verbose logging:**
```bash
python3 -m src.main myschool teacher@school.edu password123 \
    "https://myschool.managebac.cn/teacher/classes/12345/gradebook/term/67890/tasks" \
    --verbose
```

### Command-Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--output PATH` | `-o` | Specify output Excel file path (default: auto-generated in `gradebook/` folder) |
| `--prompt-password` | `-p` | Prompt for password securely instead of passing on command line |
| `--verbose` | `-v` | Enable verbose logging for debugging |

## How It Works

1. **Authentication**: Logs into ManageBac using your credentials
2. **Data Extraction**: Scrapes student names, tasks, scores, comments, and term grades
3. **Student Selection**: Opens a GUI window to select which students to export
4. **Excel Export**: Creates an organized Excel file with:
   - Student names in the first column
   - Task columns with criterion scores (A, B, C, D)
   - Comment columns adjacent to each score
   - Term grades in a dedicated column
   - Additional evaluation columns for manual input

## Output Format

Excel files are saved in the `gradebook/` folder with the naming pattern:
```
gradebook/gradebook_<class_name>_<term_name>_<timestamp>.xlsx
```

### Excel Structure

| Student Name | Task1 (A) | Task1 (A) Comment | Task1 (B) | Task1 (B) Comment | ... | Term Grade | Classroom Behaviour | ... |
|--------------|-----------|-------------------|-----------|-------------------|-----|------------|---------------------|-----|
| John Doe     | A: 7      | Great work        | B: 6      |                   | ... | 7          |                     | ... |
| Jane Smith   | A: 8      |                   | B: 7      | Good effort       | ... | 8          |                     | ... |

## Student Selection GUI

After data extraction, a GUI window appears allowing you to:
- ✅ Select/deselect individual students
- 🔍 Search for students by name
- ✔️ Select all / Deselect all
- 📤 Export only selected students

## Security Notes

- ⚠️ **Never commit credentials to version control**
- Use `--prompt-password` flag for secure password entry
- The `gradebook/` folder is git-ignored to protect student data
- Excel exports contain sensitive student information - handle with care

## Troubleshooting

### Authentication Failed
- Verify your school code, email, and password are correct
- Check that your account has teacher access to the gradebook
- Ensure you're using the correct ManageBac domain (`.managebac.cn`)

### No Data Extracted
- Verify the gradebook URL is correct and accessible
- Check that the gradebook page has loaded completely in your browser
- Try running with `--verbose` flag to see detailed logs

### Session Expired
- The tool automatically re-authenticates if the session expires
- If issues persist, try running the command again

## Development

### Running Tests
```bash
pytest
```

### Debug Scripts

The repository includes several debug scripts:

- `debug_extraction.py` - Check what data is being extracted
- `debug_html_structure.py` - Inspect HTML structure and save page
- `diagnose_extraction.py` - Comprehensive diagnostic tool
- `check_excel.py` - Verify Excel file structure

## Project Structure

```
.
├── src/
│   ├── main.py           # CLI entry point
│   ├── scraper.py        # Main orchestrator
│   ├── auth.py           # Authentication logic
│   ├── extractors.py     # Data extraction modules
│   ├── excel_exporter.py # Excel export functionality
│   ├── models.py         # Data models
│   └── exceptions.py     # Custom exceptions
├── tests/                # Test suite
├── gradebook/            # Output folder (git-ignored)
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## License

This tool is for educational purposes. Ensure compliance with your institution's data handling policies when using scraped data.

## Support

For issues or questions, please check the troubleshooting section or review the debug scripts for diagnostic information.
