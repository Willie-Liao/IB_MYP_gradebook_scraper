#!/usr/bin/env python3
"""Comprehensive diagnostic script for extraction issues."""

import logging
import sys
from bs4 import BeautifulSoup
from src.scraper import GradebookScraper

# Enable detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(name)s - %(message)s'
)

def main():
    print("=== ManageBac Gradebook Extraction Diagnostics ===\n")
    
    # Get credentials
    school_code = input("Enter school code: ").strip()
    email = input("Enter email: ").strip()
    password = input("Enter password: ").strip()
    gradebook_url = input("Enter gradebook URL: ").strip()
    
    if not all([school_code, email, password, gradebook_url]):
        print("Error: All fields are required")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("STEP 1: Authentication")
    print("="*60)
    
    scraper = GradebookScraper(school_code, email, password)
    try:
        scraper.authenticate()
        print("✓ Authentication successful")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("STEP 2: Fetching Gradebook Page")
    print("="*60)
    
    try:
        response = scraper.session_manager.get(gradebook_url)
        soup = BeautifulSoup(response.content, "lxml")
        print(f"✓ Page fetched successfully ({len(response.content)} bytes)")
        
        # Save HTML for manual inspection
        with open("debug_gradebook.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        print("✓ Saved HTML to debug_gradebook.html")
    except Exception as e:
        print(f"✗ Failed to fetch page: {e}")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("STEP 3: Analyzing HTML Structure")
    print("="*60)
    
    # Collect all classes
    all_classes = set()
    for elem in soup.find_all(True):
        classes = elem.get("class")
        if classes:
            if isinstance(classes, list):
                all_classes.update(classes)
            else:
                all_classes.add(str(classes))
    
    print(f"Total unique classes found: {len(all_classes)}")
    
    # Look for relevant classes
    relevant_keywords = ['grade', 'task', 'student', 'score', 'column', 'criterion']
    relevant_classes = [cls for cls in all_classes if any(kw in str(cls).lower() for kw in relevant_keywords)]
    
    print(f"\nRelevant classes ({len(relevant_classes)}):")
    for cls in sorted(relevant_classes)[:20]:
        print(f"  - {cls}")
    if len(relevant_classes) > 20:
        print(f"  ... and {len(relevant_classes) - 20} more")
    
    print("\n" + "="*60)
    print("STEP 4: Extracting Students")
    print("="*60)
    
    from src.extractors import StudentExtractor
    students = StudentExtractor.extract(soup)
    print(f"✓ Extracted {len(students)} students")
    for i, student in enumerate(students[:5]):
        print(f"  {i+1}. {student.name} (ID: {student.id})")
    if len(students) > 5:
        print(f"  ... and {len(students) - 5} more")
    
    print("\n" + "="*60)
    print("STEP 5: Extracting Tasks")
    print("="*60)
    
    from src.extractors import TaskExtractor
    tasks = TaskExtractor.extract(soup)
    print(f"{'✓' if tasks else '✗'} Extracted {len(tasks)} tasks")
    
    if not tasks:
        print("\n⚠ NO TASKS FOUND - This is the problem!")
        print("\nLooking for task-related elements...")
        
        # Try to find any elements that might be tasks
        potential_task_elements = soup.find_all(attrs={"data-original-title": True})
        print(f"  Elements with data-original-title: {len(potential_task_elements)}")
        
        task_links = soup.find_all("a", href=lambda h: bool(h and "/tasks/" in str(h)))
        print(f"  Links containing '/tasks/': {len(task_links)}")
        if task_links:
            print(f"    Example: {task_links[0].get('href')}")
        
        columns = soup.find_all(class_=lambda c: bool(c and "column" in str(c)))
        print(f"  Elements with 'column' in class: {len(columns)}")
        
    else:
        for i, task in enumerate(tasks[:5]):
            print(f"  {i+1}. {task.name} (ID: {task.id})")
        if len(tasks) > 5:
            print(f"  ... and {len(tasks) - 5} more")
    
    print("\n" + "="*60)
    print("STEP 6: Extracting Scores")
    print("="*60)
    
    from src.extractors import ScoreExtractor
    scores = ScoreExtractor.extract(soup, students, tasks)
    print(f"{'✓' if scores else '✗'} Extracted {len(scores)} scores")
    
    if not scores:
        print("\n⚠ NO SCORES FOUND!")
        print("\nLooking for score-related elements...")
        
        score_candidates = soup.find_all(class_=lambda c: bool(c and "score" in str(c).lower()))
        print(f"  Elements with 'score' in class: {len(score_candidates)}")
        
        grade_elements = soup.find_all(class_=lambda c: bool(c and "grade" in str(c).lower()))
        print(f"  Elements with 'grade' in class: {len(grade_elements)}")
        
        student_grade_elements = soup.find_all(attrs={"data-student": True})
        print(f"  Elements with data-student attribute: {len(student_grade_elements)}")
        
    else:
        for i, score in enumerate(scores[:10]):
            comment_preview = score.comment[:30] + "..." if score.comment and len(score.comment) > 30 else score.comment
            print(f"  {i+1}. Student {score.student_id}, Task {score.task_id}, {score.criterion}: {score.score}, Comment: {comment_preview or 'None'}")
        if len(scores) > 10:
            print(f"  ... and {len(scores) - 10} more")
    
    print("\n" + "="*60)
    print("STEP 7: Summary")
    print("="*60)
    
    print(f"Students: {len(students)}")
    print(f"Tasks: {len(tasks)}")
    print(f"Scores: {len(scores)}")
    
    if not tasks:
        print("\n❌ PRIMARY ISSUE: No tasks extracted")
        print("   This prevents score extraction and Excel export")
        print("   Check debug_gradebook.html to see the actual HTML structure")
    elif not scores:
        print("\n❌ PRIMARY ISSUE: No scores extracted")
        print("   Tasks were found but scores couldn't be extracted")
        print("   Check debug_gradebook.html to see the actual HTML structure")
    else:
        print("\n✓ All extractions successful!")
        
        # Check for comments
        scores_with_comments = [s for s in scores if s.comment]
        print(f"\nScores with comments: {len(scores_with_comments)} / {len(scores)}")
        if len(scores_with_comments) == 0:
            print("⚠ No comments found - check if comments exist in the HTML")

if __name__ == "__main__":
    main()
