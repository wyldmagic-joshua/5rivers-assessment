import json
import logging
from asyncio import timeout

import requests
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define a main() function that prints a little greeting.
def main():
    processor = StudentDataProcessor(source_url="https://api.slingacademy.com/v1/sample-data/files/student-scores.json")
    raw_data = processor.fetch_json_data()
    student_data = processor.parse_student_data(raw_data)
    cleaned_data = processor.handle_missing_null_malformed_data(student_data)
    valid_student_data = processor.process_student_data(cleaned_data)

class StudentDataProcessor:
  REQUIRED_FIELDS = ["id", "first_name", "last_name", "email"]

  def __init__(self, source_url=None):
    self.source_url = source_url

  def fetch_json_data(self):
    logging.debug("fetch_json_data >>")
    try:
      logging.info("Fetching JSON data from %s...", self.source_url)
      response = requests.get(self.source_url, timeout=10)
      response.raise_for_status()
      data = response.json()
      logging.info("JSON data fetched successfully.")
      return data
    except requests.exceptions.RequestException as e:
      logging.error("Error fetching JSON data: %s", str(e))
      return []
    except json.JSONDecodeError as e:
      logging.error("Error decoding JSON data: %s", str(e))
      return []
    finally:
      logging.debug("fetch_json_data <<")

  def parse_student_data(self, raw_data):
    logging.debug("parse_student_data >>")
    try:
      logging.info("Parsing student data...")
      if isinstance(raw_data, list):
        logging.info("JSON data is a list.")
        return raw_data
      else:
        logging.info("Expected a list of student data, but got something else.")
        return []
    except Exception as e:
      logging.error("Unexpected error parsing student data: %s", str(e))
    finally:
      logging.debug("parse_student_data <<")

  def handle_missing_null_malformed_data(self, student_data):
    logging.debug("handle_missing_null_malformed_data >>")
    cleaned_students = []
    for student in student_data:
      try:
        # Remove null values
        cleaned_student = {k: v for k, v in student.items() if v is not None}
        cleaned_students.append(cleaned_student)
      except Exception as e:
        logging.error("Error cleaning student data: %s", str(e))
    logging.info("Total cleaned student records: %d", len(cleaned_students))
    logging.debug("handle_missing_null_malformed_data <<")
    return cleaned_students

  def process_student_data(self, student_data):
    logging.debug("process_student_data >>")
    valid_students = []
    for student in student_data:
      if self.validate_student_record(student):
        valid_students.append(student)
      else:
        logging.warning("Student record is invalid and will be excluded: %s", student)
    logging.info("Total valid student records: %d", len(valid_students))
    logging.debug("process_student_data <<")
    return valid_students

  def validate_student_record(self, student_record):
    missing_fields = [field for field in self.REQUIRED_FIELDS if field not in student_record or not student_record[
      field]]
    if missing_fields:
      logging.error("Student record is missing required fields: %s for student records: %s", missing_fields, student_record)
      return False
    return True

# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
  main()