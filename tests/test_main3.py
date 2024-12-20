# File: tests/test_main3.py

import pytest
import re
from main import StudentDataProcessor


@pytest.fixture
def processor():
    return StudentDataProcessor(
        encryption_key="67d720da118b5a8558a9eeff8fb3b11dc689aebf6fa281c95a1fc16996e6cb75",
        source_url="https://api.slingacademy.com/v1/sample-data/files/student-scores.json")

@pytest.fixture
def mock_student_data(mocker):
    mocker.patch("main.os.path.exists", side_effect=lambda x: x == "student_data.json")
    mocker.patch("builtins.open", mocker.mock_open(read_data="""
    [
        {
            "id": "1",
            "email": "4792c46fbce89bc3be74143005348a9cbbc08ebf6840c5ca54e5ead3b0743bbf5a361c288c1a90beab67206664a5"
        },
        {
            "id": "2",
            "email": "4792c46fbce89bc3be74143005348a9cbbc08ebf6840c5ca54e5ead3b0743bbf5a361c288c1a90beab67206664a5"
        }
    ]
    """))
    return None  # Mocking happens automatically


def test_decrypt_field_valid_id(processor, mock_student_data):

    result = processor.decrypt_field("1")
    assert result is not None
    assert isinstance(result, str)
    assert re.match(processor.EMAIL_REGEX, result)  # Check it's a valid email


def test_decrypt_field_invalid_id(processor, mock_student_data):
    result = processor.decrypt_field("999")
    assert result is None


def test_decrypt_field_no_file(processor, mocker):
    mocker.patch("main.os.path.exists", return_value=False)
    result = processor.decrypt_field("1")
    assert result is None


def test_decrypt_field_incorrect_key(processor, mocker):
    mocker.patch("main.os.path.exists", side_effect=lambda x: x == "student_data.json")
    mocker.patch("builtins.open", mocker.mock_open(read_data="""
    [
        {
            "id": "1",
            "email": "4792c46fbce89bc3be74143005348a9cbbc08ebf6840c5ca54e5ead3b0743bbf5a361c288c1a90beab67206664a5"
        }
    ]
    """))
    processor.encryption_key = bytes.fromhex("cf51483b089d65e0748682b086e7f648f2b6016f261b268a86ed8eda8028cf45")
    result = processor.decrypt_field("1")
    assert result is None
