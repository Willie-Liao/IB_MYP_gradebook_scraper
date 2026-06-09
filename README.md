# ManageBac Gradebook Scraper

A Python GUI tool for scraping IB MYP gradebook data from ManageBac and exporting it to Excel.

## Features

- Secure authentication with ManageBac (school derived from URL)
- Scrapes **Term Grades** page: student names, final grade, criterion A–D
- Scrapes **Tasks** page: assessment scores and comments
- Interactive student selection before export
- Excel export with term profile columns plus per-task scores

## Requirements

- Python 3.10 or higher
- ManageBac teacher account
- Internet connection

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env   # then edit with your ManageBac credentials
```

## Usage

Launch the GUI:

```bash
python3 -m src.gui
```

### Fields

| Field | Description |
|-------|-------------|
| **Gradebook URL** | Any ManageBac URL for the class/term (tasks or term-grades link) |
| **Email** | Prefilled from `.env` (`MANAGEBAC_EMAIL`) if set |
| **Password** | Prefilled from `.env` (`MANAGEBAC_PASSWORD`) if set |
| **Output Dir** | Prefilled from `.env` (`MANAGEBAC_OUTPUT_DIR`, default `gradebook/`) |

Example URL:

```
https://myschool.managebac.cn/teacher/classes/12345/gradebook/term/67890/tasks
```

### Workflow

1. Log in (school code and domain parsed from the URL)
2. Fetch term grades page (`myp-term-grades`) and tasks page
3. Select students in the picker window
4. Choose where to save the Excel file

## Excel layout

| Columns | Content |
|---------|---------|
| Student Name | From term grades page |
| Term Grade | Final grade (out of 8) |
| Criterion A–D | Term criterion scores |
| Task columns | Per-assessment criterion scores |
| Comment columns | Teacher comments per task/criterion |

## Development

```bash
pytest tests/
```

Re-index GitNexus after structural changes:

```bash
node .gitnexus/run.cjs analyze
```
