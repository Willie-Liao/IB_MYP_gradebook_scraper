"""Property tests for TermGradeExtractor.

Feature: managebac-gradebook-scraper, Property 4: Term Grade Extraction Accuracy
Validates: Requirements 5.2, 5.3, 5.4, 5.5
"""

from hypothesis import given, settings, strategies as st
from bs4 import BeautifulSoup

from src.extractors import TermGradeExtractor


grade_strategy = st.sampled_from(["1", "2", "3", "4", "5", "6", "7", "8", "INC", "N/A"])

student_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Zs")),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip())


@st.composite
def term_grade_data_strategy(draw: st.DrawFn) -> tuple[str, str]:
    student_name = draw(student_name_strategy)
    grade = draw(grade_strategy)
    return (student_name, grade)


@st.composite
def term_grade_list_strategy(draw: st.DrawFn) -> list[tuple[str, str]]:
    return draw(
        st.lists(
            term_grade_data_strategy(),
            min_size=0,
            max_size=30,
            unique_by=lambda x: x[0].strip(),
        )
    )


def generate_term_grades_html(term_grades: list[tuple[str, str]]) -> str:
    """Generate HTML matching ManageBac fusion-card term grades layout."""
    student_cards = ""
    for index, (student_name, grade) in enumerate(term_grades):
        student_cards += f"""
        <div class="fusion-card student-grade js-student-total">
            <div class="fusion-card-header">
                <h4 class="cell flex-fill student-name">
                    <a class="text-break" href="/teacher/users/{1000 + index}">{student_name}</a>
                </h4>
                <div class="cell final-grade">
                    <p class="text-success js-final-grade-final">{grade}</p>
                </div>
            </div>
            <div class="fusion-card-body with-padding">
                <div class="criteria-grade">
                    <div class="form-group flex-fill">
                        <label>A: Knowing</label>
                        <input type="radio" value="5" checked>
                    </div>
                </div>
            </div>
        </div>
        """

    return f"""
    <html>
    <body>
        <div id="gradebook-form">
            <div class="grid-table-main">
                {student_cards}
            </div>
        </div>
    </body>
    </html>
    """


@given(term_grades=term_grade_list_strategy())
@settings(max_examples=100)
def test_term_grade_extraction_accuracy(term_grades: list[tuple[str, str]]) -> None:
    html = generate_term_grades_html(term_grades)
    soup = BeautifulSoup(html, "lxml")
    extracted = TermGradeExtractor.extract(soup)

    assert len(extracted) == len(term_grades)

    extracted_dict = {tg.student_name: tg.grade for tg in extracted}
    for student_name, grade in term_grades:
        expected_name = student_name.strip()
        assert expected_name in extracted_dict
        assert extracted_dict[expected_name] == grade


def test_empty_gradebook_returns_empty_list() -> None:
    html = """
    <html><body>
        <div class="grid-table-main"></div>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    assert TermGradeExtractor.extract(soup) == []


def test_missing_student_cards_returns_empty_list() -> None:
    html = """
    <html><body>
        <div class="some-other-class">
            <h4 class="student-name">Test Student</h4>
        </div>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    assert TermGradeExtractor.extract(soup) == []


def test_special_grade_values_preserved() -> None:
    html = """
    <html><body>
        <div class="grid-table-main">
            <div class="fusion-card student-grade">
                <h4 class="student-name"><a class="text-break">Student One</a></h4>
                <div class="final-grade"><p class="js-final-grade-final">INC</p></div>
            </div>
            <div class="fusion-card student-grade">
                <h4 class="student-name"><a class="text-break">Student Two</a></h4>
                <div class="final-grade"><p class="js-final-grade-final">N/A</p></div>
            </div>
            <div class="fusion-card student-grade">
                <h4 class="student-name"><a class="text-break">Student Three</a></h4>
                <div class="final-grade"><p class="js-final-grade-final">7</p></div>
            </div>
        </div>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    extracted = TermGradeExtractor.extract(soup)
    extracted_dict = {tg.student_name: tg.grade for tg in extracted}

    assert extracted_dict["Student One"] == "INC"
    assert extracted_dict["Student Two"] == "N/A"
    assert extracted_dict["Student Three"] == "7"


def test_criterion_scores_from_points_buttons() -> None:
    """Live ManageBac uses points-button bars without a criteria-grade wrapper."""
    html = """
    <html><body>
        <div class="fusion-card student-grade">
            <h4 class="student-name"><a class="text-break" href="/teacher/users/42">Ada</a></h4>
            <div class="final-grade"><p class="js-final-grade-final">6</p></div>
            <div class="form-group flex-fill">
                <label>A: Knowing and understanding</label>
                <div class="points-bar">
                    <div aria-pressed="false" class="points-button btn final-criteria-score">N/A</div>
                    <div aria-pressed="true" class="points-button btn final-criteria-score selected">6</div>
                </div>
            </div>
            <div class="form-group flex-fill">
                <label>B: Planning</label>
                <div class="points-bar">
                    <div aria-pressed="true" class="points-button btn final-criteria-score selected">5</div>
                </div>
            </div>
        </div>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    extracted = TermGradeExtractor.extract(soup)

    assert len(extracted) == 1
    assert extracted[0].criterion_a == "6"
    assert extracted[0].criterion_b == "5"


def test_criterion_scores_extracted() -> None:
    html = """
    <html><body>
        <div class="fusion-card student-grade">
            <h4 class="student-name"><a class="text-break" href="/teacher/users/42">Ada</a></h4>
            <div class="final-grade"><p class="js-final-grade-final">6</p></div>
            <div class="criteria-grade">
                <div class="form-group flex-fill">
                    <label>A: Knowing</label>
                    <input type="radio" value="6" checked>
                </div>
                <div class="form-group flex-fill">
                    <label>B: Planning</label>
                    <input type="radio" value="5" checked>
                </div>
            </div>
        </div>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    extracted = TermGradeExtractor.extract(soup)

    assert len(extracted) == 1
    assert extracted[0].user_id == "42"
    assert extracted[0].criterion_a == "6"
    assert extracted[0].criterion_b == "5"
