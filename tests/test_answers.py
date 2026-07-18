"""The declarative answer engine maps known screening questions and refuses to guess others."""
from pathlib import Path
import pytest
from ats_autopilot.answers import AnswerBook

ANSWERS = Path(__file__).resolve().parent.parent / "config" / "answers.yaml"


@pytest.fixture
def book():
    return AnswerBook.load(ANSWERS)


@pytest.mark.parametrize("label,expected", [
    ("Are you at least 18 years of age?", "Yes"),
    ("Are you legally authorized to work in the country?", "Yes"),
    ("Will you require sponsorship for employment visa status?", "No"),
    ("Have you previously been employed by this company?", "No"),
    ("How did you hear about this job?", "Company website"),
    ("Are you able to work EST hours?", "Yes"),
])
def test_known_questions_answered(book, label, expected):
    assert book.answer_for(label) == expected


def test_unknown_question_is_not_guessed(book):
    # Anything we don't have an explicit rule for must return None (→ surfaced as unmapped).
    assert book.answer_for("What is your favorite programming paradigm and why?") is None
