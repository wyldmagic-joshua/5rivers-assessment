# File: tests/test_main4.py

import pytest
from main import StudentDataProcessor


@pytest.fixture
def processor():
    return StudentDataProcessor()


def test_calculate_summary_metrics_realistic_sample_data(processor):
    student_data = [
        {
            "id": 1,
            "first_name": "Paul",
            "last_name": "Casey",
            "email": "4792c46fbce89bc3be74143005348a9cbbc08ebf6840c5ca54e5ead3b0743bbf5a361c288c1a90beab67206664a5",
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
            "geography_score": 87
        },
        {
            "id": 2,
            "first_name": "Danielle",
            "last_name": "Sandoval",
            "email": "0802beb5718e064c5d51dfd9743d578af2ba7f2b0a187c0f30a4bd6eeb12fdc18011f4054a7e0e96a29f777970fb209257a18a2732",
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
            "geography_score": 90
        }
    ]

    result = processor.calculate_summary_metrics(student_data)

    # Assertions for subject metrics
    assert result["subject_metrics"]["math_score"]["mean"] == 81.5
    assert result["subject_metrics"]["history_score"]["mean"] == 83.5
    assert result["subject_metrics"]["physics_score"]["mean"] == 94.5
    assert result["subject_metrics"]["chemistry_score"]["mean"] == 98.5
    assert result["subject_metrics"]["biology_score"]["mean"] == 76.5
    assert result["subject_metrics"]["english_score"]["mean"] == 84
    assert result["subject_metrics"]["geography_score"]["mean"] == 88.5

    assert result["subject_metrics"]["math_score"]["max"] == 90
    assert result["subject_metrics"]["math_score"]["min"] == 73
    assert result["subject_metrics"]["history_score"]["max"] == 86
    assert result["subject_metrics"]["history_score"]["min"] == 81

    # Assertions for comparisons
    assert result["comparisons"]["by_gender"]["male"] == 1
    assert result["comparisons"]["by_gender"]["female"] == 1
    assert result["comparisons"]["by_career_aspiration"]["Lawyer"] == 1
    assert result["comparisons"]["by_career_aspiration"]["Doctor"] == 1
    assert result["comparisons"]["by_extracurricular_activities"][False] == 2
