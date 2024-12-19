import csv
import json
import logging
import os
import re
import requests
import statistics
from collections import Counter
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define a main() function that prints a little greeting.
def main():
    processor = StudentDataProcessor(source_url="https://api.slingacademy.com/v1/sample-data/files/student-scores.json")
    valid_student_data = processor.fetch_and_process_student_data(file_format="json")

    if not valid_student_data:
      logging.error("No valid student data found.")
      return

    processor.save_student_data(valid_student_data, filename="student_data.json", file_format="json")
    processor.save_student_data(valid_student_data, filename="student_data.csv", file_format="csv")

    summary_metrics = processor.calculate_summary_metrics(valid_student_data)
    processor.save_student_data(summary_metrics, filename="summary_metrics.json", file_format="json")

    headers = ['Subject'] + list(next(iter(summary_metrics['subject_metrics'].values())).keys())
    processor.save_csv(summary_metrics['subject_metrics'], headers=headers,
                       filename="subject_metrics.csv", headerOverride="Subject")

    processor.save_csv([summary_metrics['comparisons']['by_gender']],
                       filename="gender_metrics.csv")

    processor.save_csv([summary_metrics['comparisons']['by_career_aspiration']],
                       filename="career_metrics.csv")

    processor.save_csv([summary_metrics['comparisons']['by_extracurricular_activities']],
                       filename="extracurricular_metrics.csv")

    processor.generate_report(summary_metrics['subject_metrics'], filename="subject_metrics.png")

    processor.post_low_scores()

    logging.info(f"Summary metrics: {summary_metrics}")

class StudentDataProcessor:
  REQUIRED_FIELDS = ["id", "first_name", "last_name", "email"]
  EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
  low_score_requests = []
  seen_students = set()

  def __init__(self, source_url=None, encryption_key=None):
    self.source_url = source_url
    self.encryption_key = encryption_key.encode('utf-8') if encryption_key else os.urandom(32)
    if not encryption_key:
      print(f"Encryption key not provided. Using random key: {self.encryption_key.hex()}")

  def fetch_and_process_student_data(self, file_format='json'):
    logging.debug("fetch_and_process_student_data >>")
    try:
      if file_format.lower() == 'json' and os.path.exists('student_data.json'):
        with open('student_data.json', 'r') as file:
          return json.load(file)
      elif file_format.lower() == 'csv' and os.path.exists('student_data.csv'):
        with open('student_data.csv', 'r') as file:
          reader = csv.DictReader(file)
          return [row for row in reader]
      else:
        raw_data = self.fetch_json_data()
        student_data = self.parse_student_data(raw_data)
        cleaned_data = self.handle_missing_null_malformed_data(student_data)
        return self.process_student_data(cleaned_data)
    except Exception as e:
      logging.error(f"Error fetching student data: {e}")
      return []
    finally:
      logging.debug("fetch_and_process_student_data <<")

  def fetch_json_data(self):
    logging.debug("fetch_json_data >>")
    try:
      logging.info("Fetching JSON data from %s...", self.source_url)
      response = requests.get(self.source_url, timeout=10)
      response.raise_for_status()
      logging.info("Data fetched successfully.")
      data = response.text

      try:
        parsed_data = json.loads(data)
        logging.info("JSON data validated successfully.")
        return parsed_data
      except json.JSONDecodeError as e:
        logging.error(f"Malformed JSON data: {e}")
        return []
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
    valid_students = {}

    for student in student_data:
      if self.validate_student_record(student):
        # Create a unique identifier (can be customized to fit needs)
        student_identifier = (student.get('first_name'), student.get('last_name'), student.get('email'))

        if student_identifier in self.seen_students:
          logging.warning(f"Duplicate student record found, updating: {student}")
          valid_students[student_identifier].update(student)
          continue  # Skip this duplicate record

        self.seen_students.add(student_identifier)  # Mark this student as seen

        if student['email']:
          student['email'] = self.encrypt_field(student['email'])
        self.check_for_low_scores(student)
        valid_students[student_identifier] = student
      else:
        logging.warning("Student record is invalid and will be excluded: %s", student)
    logging.info("Total valid student records: %d", len(valid_students))
    logging.debug("process_student_data <<")
    return list(valid_students.values())

  def validate_student_record(self, student_record):
    missing_fields = [field for field in self.REQUIRED_FIELDS if field not in student_record or not student_record[
      field]]
    if missing_fields:
      logging.error("Student record is missing required fields: %s for student records: %s", missing_fields, student_record)
      return False
    if not re.match(self.EMAIL_REGEX, student_record.get('email', '')):
      logging.error("Invalid email format for student: %s", student_record['email'])
    return True

  def encrypt_field(self, field):
    logging.debug("encrypt_field >>")
    try:
      if not field:
        return None

      iv = os.urandom(16)
      cipher = Cipher(algorithms.AES(self.encryption_key), modes.CFB(iv), backend=default_backend())
      encryptor = cipher.encryptor()
      encrypted_field = encryptor.update(field.encode('utf-8')) + encryptor.finalize()
      return iv.hex() + encrypted_field.hex()
    except Exception as e:
      logging.error(f"Error encrypting email: {e}")
      return None
    finally:
      logging.debug("encrypt_field <<")


  def check_for_low_scores(self, student_record):
    logging.debug("post_low_scores >>")
    try:
      low_score_subjects = {
        subject: score for subject, score in student_record.items()
        if subject.endswith('_score') and isinstance(score, (int, float)) and score < 65
      }

      if low_score_subjects:
        logging.info(f"Low score subjects found for student: {student_record}")
        url = 'https://httpbin.org/post'
        payload = {
          'id': student_record['id'],
          'first_name': student_record['first_name'],
          'last_name': student_record['last_name'],
          'email': student_record['email'],
          'low_scores':low_score_subjects
        }
        self.low_score_requests.append(payload)
    except requests.exceptions.RequestException as e:
      logging.error(f"Error posting low score for student {student_record['id']}: {e}")
    finally:
      logging.debug("post_low_scores <<")

  def post_low_scores(self):
    logging.debug("post_low_scores >>")
    try:
      if self.low_score_requests:
        logging.info(f"Posting low score records: {self.low_score_requests}")
        response = requests.post('https://httpbin.org/post', json=self.low_score_requests)
        response.raise_for_status()
        logging.debug(f"Low score records posted successfully: {response.json()}")
    except requests.exceptions.RequestException as e:
      logging.error(f"Error posting low score records: {e}")

  def save_csv(self, student_data, headers=None, filename=None, headerOverride=None, delimiter='\t'):
    logging.debug("save_csv >>")
    with open(filename, mode='w', newline='') as file:
      if headers is None:
        headers = student_data[0].keys()

      writer = csv.DictWriter(file, fieldnames=headers, delimiter=delimiter)

      writer.writeheader()

      if headerOverride is None:
        writer.writerows(student_data)
      else:
        for override, metrics in student_data.items():
          row = {headerOverride: override}
          row.update(metrics)
          writer.writerow(row)
      logging.info(f"Student data saved to {filename} in CSV format.")
    logging.debug("save_csv <<")

  def save_json(self, student_data, filename=None):
    logging.debug("save_json >>")
    with open(filename, 'w') as file:
      json.dump(student_data, file, indent=4)
    logging.info(f"Processed student data saved to {filename} in JSON format.")
    logging.debug("save_json <<")

  def save_student_data(self, student_data, filename="student_data.csv.json", file_format='json'):
    logging.debug("save_student_data >>")
    try:
      if file_format.lower() == 'json':
       self.save_json(student_data, filename=filename)
      elif file_format.lower() == 'csv':
        self.save_csv(student_data, filename=filename)
      else:
        logging.error(f"Unsupported file format: {format}")
    except Exception as e:
      logging.error(f"Error saving {filename} to disk: {e}")
    finally:
      logging.debug("save_student_data <<")

  def calculate_summary_metrics(self, student_data, file_format='json'):
    logging.debug("calculate_summary_metrics >>")
    try:
      subject_scores = {subject: [] for subject in
                        ['math_score', 'history_score', 'physics_score', 'chemistry_score', 'biology_score',
                         'english_score', 'geography_score']}

      for student in student_data:
        for subject in subject_scores.keys():
          if subject in student and isinstance(student[subject], (int, float)):
            subject_scores[subject].append(student[subject])

      subject_metrics = {
        subject: {
          'mean': statistics.mean(scores) if scores else 0,
          'median': statistics.median(scores) if scores else 0,
          'stdev': statistics.stdev(scores) if len(scores) > 1 else 0,
          'max': max(scores) if scores else 0,
          'min': min(scores) if scores else 0
        } for subject, scores in subject_scores.items()
      }

      comparisons = {
        'by_gender': Counter([student.get('gender') for student in student_data]),
        'by_career_aspiration': Counter([student.get('career_aspiration') for student in student_data]),
        'by_extracurricular_activities': Counter(
          [student.get('extracurricular_activities') for student in student_data])
      }

      metrics = {
        'subject_metrics': subject_metrics,
        'comparisons': comparisons
      }

      logging.info(f"Summary metrics calculated: {metrics}")
      return metrics
    except Exception as e:
      logging.error(f"Error calculating summary metrics: {e}")
      return {}
    finally:
      logging.debug("calculate_summary_metrics <<")

  def generate_report(self, subject_metrics, filename="graph.png"):
    logging.debug("generate_report >>")
    try:
      subjects = list(subject_metrics.keys())
      means = [metrics['mean'] for metrics in subject_metrics.values()]

      plt.figure(figsize=(10, 6))
      plt.bar(subjects, means, color='skyblue')
      plt.xlabel('Subjects')
      plt.ylabel('Average Score')
      plt.title('Average Scores by Subject')
      plt.xticks(rotation=45, ha="right")
      plt.tight_layout()
      plt.savefig(filename)
      logging.info(f"Graph saved as {filename}")
    except Exception as e:
      logging.error(f"Error generating graph: {e}")
    finally:
      plt.close()

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

# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
  main()