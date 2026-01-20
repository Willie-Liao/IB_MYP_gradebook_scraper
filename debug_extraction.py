"""Debug script to check what's being extracted."""

import logging
from src.scraper import GradebookScraper

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# You'll need to provide your credentials
school_code = input("Enter school code: ")
email = input("Enter email: ")
password = input("Enter password: ")
gradebook_url = input("Enter gradebook URL: ")

scraper = GradebookScraper(school_code, email, password)
data = scraper.fetch_data(gradebook_url)

print("\n=== EXTRACTION SUMMARY ===")
print(f"Students: {len(data.students)}")
for s in data.students[:3]:
    print(f"  - {s.name} (ID: {s.id})")

print(f"\nTasks: {len(data.tasks)}")
for t in data.tasks[:3]:
    print(f"  - {t.name} (ID: {t.id})")

print(f"\nScores: {len(data.scores)}")
for sc in data.scores[:5]:
    print(f"  - Student {sc.student_id}, Task {sc.task_id}, {sc.criterion}: {sc.score}, Comment: {sc.comment[:50] if sc.comment else 'None'}")

print(f"\nTerm Grades: {len(data.term_grades)}")
for tg in data.term_grades[:3]:
    print(f"  - {tg.student_name}: {tg.grade}")
