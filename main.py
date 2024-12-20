import csv
import json
import logging
import sys

import matplotlib.pyplot as plt
import os
import re
import requests
import statistics
from collections import Counter
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# Define a main() function that prints a little greeting.
def main():
    """
    Main entry point of the script. Handles student data processing, encryption, decryption, and report generation.
    If '--decrypt' argument is passed, it decrypts a student's email using the provided key.
    """
    if len(sys.argv) >= 2 and sys.argv[1] == "--decrypt":
        email = input("Enter id to decrypt: ")
        encryption_key = input("Enter encryption key: ")
        processor = StudentDataProcessor(
            encryption_key=encryption_key,
            source_url="https://api.slingacademy.com/v1/sample-data/files/student-scores.json",
        )
        decrypted_email = processor.decrypt_field(id=1)
        print(f"Decrypted email: {decrypted_email}")
        return

    # Initialize StudentDataProcessor to handle the processing pipeline
    processor = StudentDataProcessor(
        source_url="https://api.slingacademy.com/v1/sample-data/files/student-scores.json"
    )
    valid_student_data = processor.fetch_and_process_student_data(file_format="json")

    if not valid_student_data:
        logging.error("No valid student data found.")
        return

    # Save processed student data to JSON and CSV formats
    processor.save_student_data(
        valid_student_data, filename="student_data.json", file_format="json"
    )
    processor.save_student_data(
        valid_student_data, filename="student_data.csv", file_format="csv"
    )

    # Calculate and save summary metrics for student data
    summary_metrics = processor.calculate_summary_metrics(valid_student_data)
    processor.save_student_data(
        summary_metrics, filename="summary_metrics.json", file_format="json"
    )

    # Save subject metrics as a CSV file
    headers = ["Subject"] + list(
        next(iter(summary_metrics["subject_metrics"].values())).keys()
    )
    processor.save_csv(
        summary_metrics["subject_metrics"],
        headers=headers,
        filename="subject_metrics.csv",
        headerOverride="Subject",
    )

    # Save CSV files for gender, career aspiration, and extracurricular activity comparisons
    processor.save_csv(
        [summary_metrics["comparisons"]["by_gender"]], filename="gender_metrics.csv"
    )

    processor.save_csv(
        [summary_metrics["comparisons"]["by_career_aspiration"]],
        filename="career_metrics.csv",
    )

    processor.save_csv(
        [summary_metrics["comparisons"]["by_extracurricular_activities"]],
        filename="extracurricular_metrics.csv",
    )

    # Generate a PNG graph of subject metrics
    processor.generate_report(
        summary_metrics["subject_metrics"], filename="subject_metrics.png"
    )

    # Post low-score records to an external API
    processor.post_low_scores()

    logging.info(f"Summary metrics: {summary_metrics}")


class StudentDataProcessor:
    """
    Processes student data from an API, performs encryption, decryption, and data transformations.
    """

    REQUIRED_FIELDS = [
        "id",
        "first_name",
        "last_name",
        "email",
    ]  # Required fields for student records
    EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"  # Regular expression for email validation
    low_score_requests = []  # Stores low-score requests to be posted to an external API
    seen_students = set()  # Tracks seen students to prevent duplicates

    def __init__(self, source_url=None, encryption_key=None):
        """
        Initializes the StudentDataProcessor.

        :param source_url: URL to fetch student data from.
        :type source_url: str
        :param encryption_key Optional encryption key for encrypting email fields.
        :type encryption_key: Optional[str]
        """
        self.source_url = source_url

        if not encryption_key:
            self.encryption_key = os.urandom(32)
        else:
            self.encryption_key = bytes.fromhex(encryption_key)

        if not encryption_key:
            print(
                f"Encryption key not provided. Using random key: {self.encryption_key.hex()}"
            )

    def fetch_and_process_student_data(self, file_format="json"):
        """
        Fetches and processes student data based on the provided file format.

        This function attempts to load student data from local JSON or CSV files if they
        exist. If the specified format file is not available, it will fetch the data
        from an external source, parse it, handle missing, null, or malformed entries,
        and then process the cleaned data.

        :param file_format: Specifies the format in which student data should be fetched.
            Acceptable values are "json" or "csv".
            If the format is not specified, defaults to "json".
        :type file_format: str
        :return: Processed student data. If an error occurs during processing,
            an empty list is returned.
        :rtype: list
        """
        logging.debug("fetch_and_process_student_data >>")
        try:
            if file_format.lower() == "json" and os.path.exists("student_data.json"):
                with open("student_data.json", "r") as file:
                    return json.load(file)
            elif file_format.lower() == "csv" and os.path.exists("student_data.csv"):
                with open("student_data.csv", "r") as file:
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
        """
        Fetches JSON data from a specified source URL and returns the parsed result.

        This method retrieves JSON data from the URL specified by `self.source_url`. It performs
        a GET request, validates the response status, and attempts to decode the JSON content.
        If the JSON content is malformed or the request fails due to network issues or any other
        related exceptions, appropriate logging is performed, and an empty list is returned.

        :raises requests.exceptions.RequestException: If any network-related error or issue occurs
            during the HTTP request.
        :raises json.JSONDecodeError: If the JSON response data is malformed or cannot be parsed.
        :return: Parsed JSON data as a Python dictionary or list. If an error occurs or the JSON is
            malformed, an empty list is returned.
        :rtype: Union[dict, list]
        """
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
        """
        Parses student data from the provided raw input. The method expects a list of
        student data in JSON format. If the input meets the expectation, it returns
        the input data. Otherwise, it returns an empty list. The method logs detailed
        information about the process for debugging purposes.

        :param raw_data: The raw input data to be parsed. Must be of type list containing
            JSON objects representing student data.
        :type raw_data: list
        :return: The parsed student data if input type is correct, otherwise an empty list.
        :rtype: list
        """
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
        """
        Processes a list of student data dictionaries to clean missing, null, or malformed
        entries by removing entries with null values. Each student is represented as a dictionary,
        and this function ensures a cleaned and consistent dataset for further processing.

        :param student_data: List of dictionaries representing student data. Each dictionary
            contains key-value pairs where keys are the attributes of the student, and values
            represent the corresponding attribute values.
        :type student_data: list[dict]
        :return: A list of dictionaries representing the cleaned student data. Each dictionary
            is guaranteed to contain only non-null values.
        :rtype: list[dict]
        """
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
        """
        Processes a list of student data records and filters valid student entries.

        The function validates each student record from the input data, ensuring it meets
        proper validation rules. It maintains a unique set of processed student records
        to avoid duplicates, encrypts certain sensitive fields (e.g., "email"), and performs
        additional checks such as monitoring for low scores. Invalid records are excluded
        from the output result.

        :param student_data: A list of dictionaries, where each dictionary contains the
            data for an individual student. Expected dictionary keys include 'first_name',
            'last_name', 'email', and other fields required for processing.
        :return: A list of dictionaries corresponding to valid student entries
            after processing, de-duplication, and field modifications.
        :rtype: list[dict]
        """
        logging.debug("process_student_data >>")
        valid_students = {}

        for student in student_data:
            if self.validate_student_record(student):
                # Create a unique identifier (can be customized to fit needs)
                student_identifier = (
                    student.get("first_name"),
                    student.get("last_name"),
                    student.get("email"),
                )

                if student_identifier in self.seen_students:
                    logging.warning(
                        f"Duplicate student record found, updating: {student}"
                    )
                    valid_students[student_identifier].update(student)
                    continue  # Skip this duplicate record

                self.seen_students.add(student_identifier)  # Mark this student as seen

                if student["email"]:
                    student["email"] = self.encrypt_field(student["email"])
                self.check_for_low_scores(student)
                valid_students[student_identifier] = student
            else:
                logging.warning(
                    "Student record is invalid and will be excluded: %s", student
                )
        logging.info("Total valid student records: %d", len(valid_students))
        logging.debug("process_student_data <<")
        return list(valid_students.values())

    def validate_student_record(self, student_record):
        """
        Validates a student record to ensure all required fields are present and valid.

        A student record must contain all fields specified in REQUIRED_FIELDS and adhere to
        the defined formats, such as email matching EMAIL_REGEX. Missing or improperly formatted
        fields are logged as errors.

        :param student_record: The dictionary containing student information to be validated.
        :type student_record: dict
        :return: Returns True if the student record is valid; otherwise, False.
        :rtype: bool
        """
        missing_fields = [
            field
            for field in self.REQUIRED_FIELDS
            if field not in student_record or not student_record[field]
        ]
        if missing_fields:
            logging.error(
                "Student record is missing required fields: %s for student records: %s",
                missing_fields,
                student_record,
            )
            return False
        if not re.match(self.EMAIL_REGEX, student_record.get("email", "")):
            logging.error(
                "Invalid email format for student: %s", student_record["email"]
            )
        return True

    def encrypt_field(self, field):
        """
        Encrypt a provided field using AES encryption in CFB mode.

        This method takes a string input, encrypts it using a randomly generated
        initialization vector (IV) and a pre-configured encryption key, and
        returns the combined result as a hexadecimal string. The encryption
        process incorporates the provided field encoded in UTF-8 and ensures
        the final output is securely formatted.

        :param field: The plaintext string to be encrypted.
        :type field: str
        :return: Returns the IV concatenated with the encrypted field as a hex string.
                 If the input is invalid or an error occurs, returns None.
        :rtype: str or None
        """
        logging.debug("encrypt_field >>")
        try:
            if not field:
                return None

            iv = os.urandom(16)
            cipher = Cipher(
                algorithms.AES(self.encryption_key),
                modes.CFB(iv),
                backend=default_backend(),
            )
            encryptor = cipher.encryptor()
            encrypted_field = (
                encryptor.update(field.encode("utf-8")) + encryptor.finalize()
            )
            return iv.hex() + encrypted_field.hex()
        except Exception as e:
            logging.error(f"Error encrypting email: {e}")
            return None
        finally:
            logging.debug("encrypt_field <<")

    def decrypt_field(self, id=None):
        """
        Decrypts the email field for a specific student record based on the provided ID. This
        function fetches student data from either a JSON or CSV file, locates the record with
        the given ID, and decrypts the email field using the AES encryption algorithm.

        :param id: The unique identifier of the student record to be decrypted.
        :type id: Optional[str]
        :return: The decrypted email address of the student, or None if the record is not
            found or decryption fails.
        :rtype: Optional[str]
        """
        logging.debug("decrypt_field >>")

        student_data = []
        if os.path.exists("student_data.json"):
            with open("student_data.json", "r") as file:
                student_data = json.load(file)
        elif os.path.exists("student_data.csv"):
            with open("student_data.csv", "r") as file:
                reader = csv.DictReader(file)
                student_data = [row for row in reader]

        student_record = next((x for x in student_data if x["id"] == id), None)
        if student_record is None:
            logging.error("Student record not found.")
            return None

        iv = bytes.fromhex(student_record["email"][:32])
        encrypted_bytes = bytes.fromhex(student_record["email"][32:])
        cipher = Cipher(
            algorithms.AES(self.encryption_key),
            modes.CFB(iv),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        decrypted_email = decryptor.update(encrypted_bytes) + decryptor.finalize()
        logging.debug("decrypt_field <<")
        return decrypted_email.decode("utf-8")

    def check_for_low_scores(self, student_record):
        """
        Checks for any low scores in the student's record and, if found, prepares a payload
        with the student's information and low scores for a POST request.

        A score is considered "low" if:
        - The key for the score ends with "_score".
        - The score is an integer or float type.
        - The score is less than 65.

        If there are low scores, the function logs the findings and appends a payload
        containing the student's information and low scores to the `low_score_requests` list.

        :param student_record: A dictionary containing details about a student, including their
            scores across subjects. Must include a valid "id", "first_name", "last_name", and
            "email" as keys, along with keys for subjects ending in "_score".
        :type student_record: dict

        :raises requests.exceptions.RequestException: If an error occurs when attempting to post
            the low-score information using an HTTP request.

        :return: None
        """
        logging.debug("post_low_scores >>")
        try:
            low_score_subjects = {
                subject: score
                for subject, score in student_record.items()
                if subject.endswith("_score")
                and isinstance(score, (int, float))
                and score < 65
            }

            if low_score_subjects:
                logging.debug(f"Low score subjects found for student: {student_record}")
                url = "https://httpbin.org/post"
                payload = {
                    "id": student_record["id"],
                    "first_name": student_record["first_name"],
                    "last_name": student_record["last_name"],
                    "email": student_record["email"],
                    "low_scores": low_score_subjects,
                }
                self.low_score_requests.append(payload)
        except requests.exceptions.RequestException as e:
            logging.error(
                f"Error posting low score for student {student_record['id']}: {e}"
            )
        finally:
            logging.debug("post_low_scores <<")

    def post_low_scores(self):
        """
        Post low score records to an external API.

        This method attempts to send the accumulated low score records to an external
        API endpoint using a POST request. If successful, the records are transmitted
        and a successful response is logged. In the event of a failure during the HTTP
        request, an error message is logged.

        :raises requests.exceptions.RequestException: Raised if there is an
            issue with the HTTP request during posting (e.g., connection issues,
            timeouts, or HTTP errors).
        :return: None
        """
        logging.debug("post_low_scores >>")
        try:
            if self.low_score_requests:
                logging.info(f"Posting low score records: {self.low_score_requests}")
                response = requests.post(
                    "https://httpbin.org/post", json=self.low_score_requests
                )
                response.raise_for_status()
                logging.debug(
                    f"Low score records posted successfully: {response.json()}"
                )
        except requests.exceptions.RequestException as e:
            logging.error(f"Error posting low score records: {e}")

    def save_csv(
        self,
        student_data,
        headers=None,
        filename=None,
        headerOverride=None,
        delimiter="\t",
    ):
        """
        This method saves the provided student data into a CSV file. The data can be written
        using either default or custom headers, and offers an option to override the headers
        with a specified key. The delimiter for the CSV file can also be configured. The method
        logs activities during its execution.

        :param student_data: A list of dictionaries containing student data to be written into
            the CSV file. Each dictionary represents a row in the file.
        :type student_data: list of dict
        :param headers: Optional parameter that specifies the headers to be used in the CSV
            file. If not provided, the keys of the first dictionary in student_data will be used.
            Defaults to None.
        :type headers: list, optional
        :param filename: The name of the output CSV file where the student data will be saved.
        :type filename: str
        :param headerOverride: Optional parameter that can be used to override the header with
            a specific key for writing row-specific data. Defaults to None.
        :type headerOverride: str, optional
        :param delimiter: The delimiter to be used in the CSV file. Defaults to tab ("\t").
        :type delimiter: str
        :return: None
        """
        logging.debug("save_csv >>")
        with open(filename, mode="w", newline="") as file:
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
        """
        Save student data to a JSON file.

        This method takes in student data in a dictionary format and saves it to a specified
        file in JSON format. If the filename is not provided, it uses a default value. Logging
        is used to record the progress of this operation.

        :param student_data: The data structure containing student details to be saved.
        :type student_data: dict
        :param filename: The name of the file where the student data should be saved.
                         Defaults to None.
        :type filename: str, optional
        :return: None
        """
        logging.debug("save_json >>")
        with open(filename, "w") as file:
            json.dump(student_data, file, indent=4)
        logging.info(f"Processed student data saved to {filename} in JSON format.")
        logging.debug("save_json <<")

    def save_student_data(
        self, student_data, filename="student_data.csv.json", file_format="json"
    ):
        """
        Saves the given student data to a file in the specified format. Supported formats
        include 'json' and 'csv'. If the format is not supported, an error message will
        be logged. In case of an exception during the saving process, the exception will
        also be logged.

        :param student_data: The data that represents students, which will be saved to a
                             file in the specified format.
        :type student_data: Any
        :param filename: The name of the file where the student data should be saved. The
                         default value is 'student_data.csv.json'.
        :type filename: str, optional
        :param file_format: The format in which the student data should be saved. Supported
                            formats are 'json' and 'csv'. The default value is 'json'.
        :type file_format: str, optional
        :return: None
        """
        logging.debug("save_student_data >>")
        try:
            if file_format.lower() == "json":
                self.save_json(student_data, filename=filename)
            elif file_format.lower() == "csv":
                self.save_csv(student_data, filename=filename)
            else:
                logging.error(f"Unsupported file format: {format}")
        except Exception as e:
            logging.error(f"Error saving {filename} to disk: {e}")
        finally:
            logging.debug("save_student_data <<")

    def calculate_summary_metrics(self, student_data, file_format="json"):
        """
        Calculate summary statistics and comparison metrics for a list of student data.

        This method processes student information to compute summary metrics for
        various subjects, including their mean, median, standard deviation, maximum,
        and minimum scores. Additionally, it performs categorical comparisons of
        students by gender, career aspirations, and extracurricular activities.

        :param student_data: A list of dictionaries, where each dictionary contains
            individual student details such as subject scores, gender, career aspiration,
            and extracurricular activities.
        :type student_data: list[dict]

        :param file_format: The format in which results should be returned. Defaults
            to 'json'.
        :type file_format: str

        :return: A dictionary with two main keys: 'subject_metrics', which contains
            detailed statistics for each subject, and 'comparisons', which holds
            comparisons grouped by gender, career aspirations, and extracurricular
            activities.
        :rtype: dict
        """
        logging.debug("calculate_summary_metrics >>")
        try:
            subject_scores = {
                subject: []
                for subject in [
                    "math_score",
                    "history_score",
                    "physics_score",
                    "chemistry_score",
                    "biology_score",
                    "english_score",
                    "geography_score",
                ]
            }

            for student in student_data:
                for subject in subject_scores.keys():
                    if subject in student and isinstance(
                        student[subject], (int, float)
                    ):
                        subject_scores[subject].append(student[subject])

            subject_metrics = {
                subject: {
                    "mean": statistics.mean(scores) if scores else 0,
                    "median": statistics.median(scores) if scores else 0,
                    "stdev": statistics.stdev(scores) if len(scores) > 1 else 0,
                    "max": max(scores) if scores else 0,
                    "min": min(scores) if scores else 0,
                }
                for subject, scores in subject_scores.items()
            }

            comparisons = {
                "by_gender": Counter(
                    [student.get("gender") for student in student_data]
                ),
                "by_career_aspiration": Counter(
                    [student.get("career_aspiration") for student in student_data]
                ),
                "by_extracurricular_activities": Counter(
                    [
                        student.get("extracurricular_activities")
                        for student in student_data
                    ]
                ),
            }

            metrics = {"subject_metrics": subject_metrics, "comparisons": comparisons}

            logging.info(f"Summary metrics calculated: {metrics}")
            return metrics
        except Exception as e:
            logging.error(f"Error calculating summary metrics: {e}")
            return {}
        finally:
            logging.debug("calculate_summary_metrics <<")

    def generate_report(self, subject_metrics, filename="graph.png"):
        """
        Generates a bar graph representation of average scores by subject
        and saves it as an image file. The graph is created using the
        data provided in `subject_metrics`, with each subject on the x-axis
        and their corresponding mean score as bars.

        :param subject_metrics: A dictionary containing the subject names
            as keys and a dictionary of their metrics as values. The metric
            dictionary should have a key "mean" for the mean score.
        :type subject_metrics: dict[str, dict[str, float]]
        :param filename: Optional. The filename where the graph image will
            be saved. Defaults to "graph.png".
        :type filename: str
        :return: None
        """
        logging.debug("generate_report >>")
        try:
            subjects = list(subject_metrics.keys())
            means = [metrics["mean"] for metrics in subject_metrics.values()]

            plt.figure(figsize=(10, 6))
            plt.bar(subjects, means, color="skyblue")
            plt.xlabel("Subjects")
            plt.ylabel("Average Score")
            plt.title("Average Scores by Subject")
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
if __name__ == "__main__":
    main()
