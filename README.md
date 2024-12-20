# Student Data Processor

This Python script processes student data, performs encryption/decryption on email addresses, generates summary metrics, saves reports in various formats, and visualizes key statistics through graphs. The script can also send notifications for students with low scores to an external API.

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Arguments](#arguments)
- [File Structure](#file-structure)
- [Methods and Functions](#methods-and-functions)
- [Error Handling](#error-handling)
- [Logging](#logging)

---

## Features

- **Data Retrieval:** Fetch student data from a local file or remote API.
- **Data Cleaning:** Remove null, missing, or malformed data.
- **Data Validation:** Ensure required fields are present and emails are valid.
- **Data Encryption/Decryption:** Encrypt and decrypt student email addresses using AES encryption.
- **Data Persistence:** Save student data in both CSV and JSON formats.
- **Summary Metrics:** Calculate subject-level statistics such as mean, median, standard deviation, min, and max scores.
- **Data Visualization:** Generate a graph of subject metrics and save it as a PNG file.
- **Notifications:** Send a POST request to an external API if any student has a low score (below 65) in any subject.

---

## Installation

1. Clone this repository to your local machine:
   ```bash
   git clone https://github.com/your-repo-url/student-data-processor.git
   cd student-data-processor
   ```

2. Install required dependencies:
   ```bash
   pip install -r cryptography
   pip install -r matplotlib
   pip install -r requests
   ```

3. Run the script:
   ```bash
   python student_data_processor.py
   ```

---

## Usage

Run the script to process student data, save reports, and generate graphs:
```bash
python student_data_processor.py
```

To decrypt an email address for a student with a specific ID, use the `--decrypt` argument:
```bash
python student_data_processor.py --decrypt
```

You will be prompted to enter the **student ID** and the **encryption key**.

---

## Arguments

| Argument    | Description                             | Example Usage              |
|-------------|-----------------------------------------|----------------------------|
| `--decrypt` | Decrypts the email for a student record | `python student_data_processor.py --decrypt` |

---

## File Structure

```
student-data-processor/
├── student_data_processor.py    # Main script file
├── student_data.json             # Sample student data (auto-generated if not present)
├── student_data.csv              # Sample student data (auto-generated if not present)
├── summary_metrics.json          # Summary of all subject metrics
├── subject_metrics.csv           # CSV file of subject-level metrics
├── gender_metrics.csv            # CSV file of gender comparisons
├── career_metrics.csv            # CSV file of career aspiration comparisons
├── extracurricular_metrics.csv   # CSV file of extracurricular activity comparisons
└── subject_metrics.png           # PNG file of the subject metric graph
```

---

## Methods and Functions

### **`main()`**
- Handles command-line arguments for decryption.
- Calls `StudentDataProcessor` to process student data.

### **`StudentDataProcessor`**

#### **`__init__(self, source_url=None, encryption_key=None)`**
- Initializes with a source URL and an optional encryption key.

#### **`fetch_and_process_student_data(file_format="json")`**
- Fetches student data from a local file or API.
- Parses, cleans, and processes student data.

#### **`fetch_json_data()`**
- Fetches JSON data from the source URL.

#### **`parse_student_data(raw_data)`**
- Parses the raw JSON into structured student data.

#### **`handle_missing_null_malformed_data(student_data)`**
- Removes null or malformed entries from the student records.

#### **`process_student_data(student_data)`**
- Validates student records, encrypts sensitive data, and checks for low scores.

#### **`validate_student_record(student_record)`**
- Checks if required fields are present and validates the email format.

#### **`encrypt_field(field)`**
- Encrypts email addresses using AES encryption.

#### **`decrypt_field(id=None)`**
- Decrypts a student's email using their ID.

#### **`check_for_low_scores(student_record)`**
- Checks for subject scores below 65 and adds them to a list of low-score requests.

#### **`post_low_scores()`**
- Sends POST requests for students with low scores to an external API.

#### **`save_csv(student_data, filename)`**
- Saves student data as a CSV file.

#### **`save_json(student_data, filename)`**
- Saves student data as a JSON file.

#### **`save_student_data(student_data, filename, file_format)`**
- Saves student data in either CSV or JSON format.

#### **`calculate_summary_metrics(student_data)`**
- Calculates metrics (mean, median, etc.) for each subject.
- Compares students by gender, career aspiration, and extracurricular activity.

#### **`generate_report(subject_metrics, filename="graph.png")`**
- Generates a bar graph of average scores for each subject and saves it as a PNG file.

---

## Error Handling

- **File Not Found**: If `student_data.json` or `student_data.csv` is not found, the script automatically fetches the data from the API.
- **Encryption Errors**: If encryption or decryption fails, errors are logged.
- **Data Validation**: If student records have missing required fields or invalid emails, errors are logged, and the records are skipped.
- **Network Issues**: If the API for student data or low-score notifications fails, errors are logged.

---

## Logging

The script logs every action taken, and error messages are captured at critical points, such as:
- Missing required fields.
- JSON parsing errors.
- CSV and JSON save errors.
- Encryption and decryption errors.
- Network issues when contacting an external API.

**Logging format**:
```
[YYYY-MM-DD HH:MM:SS] - LEVEL - Message
```

Example log message:
```
2024-12-01 14:32:20 - INFO - Fetching JSON data from https://api.slingacademy.com/v1/sample-data/files/student-scores.json...
```

---

## Example Usage

1. **Run the script to process student data and generate reports:**
    ```bash
    python student_data_processor.py
    ```

2. **Decrypt an email for a student record using the --decrypt option:**
    ```bash
    python student_data_processor.py --decrypt
    ```
    You will be prompted to enter the student ID and the encryption key.

---

## Contributing

If you'd like to contribute to this project, please fork the repository and create a pull request. For major changes, please open an issue first to discuss the change.

---

## License

This project is licensed under the MIT License. See the LICENSE file for more details.

---

## Contact

If you have any questions, suggestions, or feedback, please open an issue on GitHub or contact the project maintainer.

