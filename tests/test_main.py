import pytest
from main import StudentDataProcessor

@pytest.fixture
def processor():
    return StudentDataProcessor(
        encryption_key="67d720da118b5a8558a9eeff8fb3b11dc689aebf6fa281c95a1fc16996e6cb75",
        source_url="https://api.slingacademy.com/v1/sample-data/files/student-scores.json")

@pytest.fixture
def example_student_data():
    return [
        {
            "id": 1,
            "first_name": "Paul",
            "last_name": "Casey",
            "email": "Paul@test.com",
            "gender": "male",
            "part_time_job": False,
            "absence_days": 3,
            "extracurricular_activities": False,
            "weekly_self_study_hours": 27,
            "career_aspiration": "Lawyer",
            "math_score": 73,
            "history_score": 81,
            "physics_score": 93,
            "chemistry_score": 97,
            "biology_score": 63,
            "english_score": 80,
            "geography_score": 87,
        },
        {
            "id": 2,
            "first_name": "Danielle",
            "last_name": "Sandoval",
            "email": "Danielle@test.com",
            "gender": "female",
            "part_time_job": False,
            "absence_days": 2,
            "extracurricular_activities": False,
            "weekly_self_study_hours": 47,
            "career_aspiration": "Doctor",
            "math_score": 90,
            "history_score": 86,
            "physics_score": 96,
            "chemistry_score": 100,
            "biology_score": 90,
            "english_score": 88,
            "geography_score": 90,
        },
    ]


def test_process_student_data_valid_records(processor, example_student_data):
    result = processor.process_student_data(example_student_data)
    assert len(result) == 2
    assert result[0]["first_name"] == "Paul"
    assert result[1]["first_name"] == "Danielle"


def test_process_student_data_encrypted_email(processor, example_student_data):
    result = processor.process_student_data(example_student_data)
    for student in result:
        assert "@" not in student["email"]  # Ensure email is encrypted


def test_process_student_data_low_scores(processor, example_student_data, mocker):
    mock_check = mocker.spy(processor, "check_for_low_scores")
    processor.process_student_data(example_student_data)
    assert mock_check.call_count == len(example_student_data)


def test_process_student_data_duplicate_example(processor):
    duplicate_data = [
        {
            "id": 1,
            "first_name": "Paul",
            "last_name": "Casey",
            "email": "4792c46fbce89bc3be74143005348a9cbbc08ebf6840c5ca54e5ead3b0743bbf5a361c288c1a90beab67206664a5",
        },
        {
            "id": 1,
            "first_name": "Paul",
            "last_name": "Casey",
            "email": "4792c46fbce89bc3be74143005348a9cbbc08ebf6840c5ca54e5ead3b0743bbf5a361c288c1a90beab67206664a5",
        },
    ]
    result = processor.process_student_data(duplicate_data)
    assert len(result) == 1


def test_process_student_data_missing_field(processor):
    incomplete_data = [{"id": 3, "first_name": "Missing", "last_name": "Email"}]
    result = processor.process_student_data(incomplete_data)
    assert result == []
