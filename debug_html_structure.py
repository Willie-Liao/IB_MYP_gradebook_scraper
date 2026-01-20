"""Debug script to save HTML and inspect structure."""

import logging
from src.scraper import GradebookScraper
from bs4 import BeautifulSoup

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# You'll need to provide your credentials
school_code = input("Enter school code: ")
email = input("Enter email: ")
password = input("Enter password: ")
gradebook_url = input("Enter gradebook URL: ")

scraper = GradebookScraper(school_code, email, password)
scraper.authenticate()

# Fetch the page
print("\nFetching gradebook page...")
response = scraper.session_manager.get(gradebook_url)
soup = BeautifulSoup(response.content, "lxml")

# Save HTML for inspection
with open("gradebook_page.html", "w", encoding="utf-8") as f:
    f.write(soup.prettify())
print("Saved HTML to gradebook_page.html")

# Check for key elements
print("\n=== ELEMENT ANALYSIS ===")

# Check for gradebook table
gradebook_table = soup.find(class_=lambda c: bool(c and "gradebook-table" in str(c)))
print(f"Gradebook table found: {gradebook_table is not None}")
if gradebook_table:
    print(f"  Classes: {gradebook_table.get('class')}")

# Check for task columns
task_columns = soup.find_all(class_=lambda c: bool(c and "gradebook-table-card" in str(c)))
print(f"\nTask columns found: {len(task_columns)}")
if task_columns:
    print(f"  First column classes: {task_columns[0].get('class')}")

# Check for score elements
score_elements = soup.find_all(class_=lambda c: bool(c and "js-student-grade" in str(c)))
print(f"\nScore elements found: {len(score_elements)}")
if score_elements:
    print(f"  First score classes: {score_elements[0].get('class')}")
    print(f"  First score attributes: {score_elements[0].attrs}")

# Check for student elements
student_elements = soup.find_all(attrs={"data-student": True})
print(f"\nStudent elements found: {len(student_elements)}")
if student_elements:
    print(f"  First student ID: {student_elements[0].get('data-student')}")

# List all unique classes in the page
all_classes = set()
for elem in soup.find_all(True):
    classes = elem.get("class")
    if classes:
        if isinstance(classes, list):
            all_classes.update(classes)
        else:
            all_classes.add(str(classes))

print(f"\n=== ALL CLASSES IN PAGE ({len(all_classes)}) ===")
for cls in sorted(all_classes):
    if any(keyword in str(cls).lower() for keyword in ['grade', 'task', 'student', 'score', 'column']):
        print(f"  {cls}")
