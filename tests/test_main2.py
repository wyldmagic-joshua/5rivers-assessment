import pytest
from main import StudentDataProcessor


@pytest.fixture
def processor():
    return StudentDataProcessor(
        encryption_key="67d720da118b5a8558a9eeff8fb3b11dc689aebf6fa281c95a1fc16996e6cb75",
        source_url="https://api.slingacademy.com/v1/sample-data/files/student-scores.json")


@pytest.fixture
def sample_field():
    return "sample_data"


def test_encrypt_field_valid_input(processor, sample_field):
    encrypted_value = processor.encrypt_field(sample_field)
    assert encrypted_value is not None
    assert isinstance(encrypted_value, str)
    assert len(encrypted_value) > 32  # IV (16 bytes) + encrypted data (at least 1 byte)


def test_encrypt_field_empty_string(processor):
    encrypted_value = processor.encrypt_field("")
    assert encrypted_value is None


def test_encrypt_field_none_input(processor):
    encrypted_value = processor.encrypt_field(None)
    assert encrypted_value is None


def test_encrypt_field_same_field_yields_different_encryption(processor, sample_field):
    encrypted_value_1 = processor.encrypt_field(sample_field)
    encrypted_value_2 = processor.encrypt_field(sample_field)
    assert encrypted_value_1 != encrypted_value_2
