import json
import tempfile
import unittest
from pathlib import Path

from models import Execution, ExecutionStatus
from ExecutionProcessor import ExecutionProcessor

BASE = Path(__file__).resolve().parents[1]
SAMPLES = BASE / "sample_inputs"


class ExecutionProcessorTests(unittest.TestCase):
    def setUp(self):
        self.processor = ExecutionProcessor()

    def process_sample(self, name):
        return self.processor.process(str(SAMPLES / name))

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            self.processor.process(str(SAMPLES / "does-not-exist.json"))

    def test_invalid_json(self):
        with self.assertRaises(json.JSONDecodeError):
            self.process_sample("invalid_json.json")

    def test_wrong_root_type(self):
        with self.assertRaises(ValueError):
            self.process_sample("wrong_root.json")

    def test_malformed_record_is_skipped_and_warns(self):
        response = self.process_sample("malformed_record.json")
        self.assertEqual(response.total_records, 2)
        self.assertEqual(response.validation_errors, 1)
        self.assertEqual(response.status, "OK_WITH_WARNINGS")
        self.assertEqual(response.summary.total_jobs, 1)

    def test_running_job_has_no_duration(self):
        response = self.process_sample("running.json")
        records = self.processor.read_file(str(SAMPLES / "running.json")).data
        self.assertIsNone(self.processor.calculate_execution_duration(records[0]))
        self.assertEqual(response.summary.successful_jobs, 0)

    def test_zero_duration_is_valid(self):
        response = self.process_sample("zero_duration.json")
        self.assertEqual(response.summary.successful_jobs, 1)
        self.assertEqual(response.summary.avg_successful_job_duration, 0.0)

    def test_finish_before_start_has_no_duration(self):
        response = self.process_sample("invalid_duration.json")
        self.assertEqual(response.summary.successful_jobs, 1)
        # Job is successful, but its invalid duration is excluded from the average.
        self.assertEqual(response.summary.avg_successful_job_duration, 0.0)

    def test_failed_attempt_then_successful_attempt(self):
        response = self.process_sample("retry_success.json")
        self.assertEqual(response.summary.total_jobs, 1)
        self.assertEqual(response.summary.successful_jobs, 1)
        self.assertEqual(response.summary.failed_jobs, 0)
        self.assertEqual(response.summary.retried_jobs, 1)
        self.assertEqual(response.summary.avg_successful_job_duration, 3.0)

    def test_final_attempt_failed(self):
        response = self.process_sample("retry_failed.json")
        self.assertEqual(response.summary.failed_jobs, 1)
        self.assertEqual(response.summary.successful_jobs, 0)
        self.assertEqual(response.summary.retried_jobs, 1)

    def test_identical_duplicate_highest_attempt_counts_once(self):
        response = self.process_sample("duplicate.json")
        self.assertEqual(response.summary.total_jobs, 1)
        self.assertEqual(response.summary.successful_jobs, 1)

    def test_conflicting_highest_attempt_excluded_from_outcome(self):
        response = self.process_sample("conflict.json")
        self.assertEqual(response.summary.total_jobs, 1)
        self.assertEqual(response.summary.successful_jobs, 0)
        self.assertEqual(response.summary.failed_jobs, 0)

    def test_no_successful_jobs_average_is_zero(self):
        response = self.process_sample("no_successes.json")
        self.assertEqual(response.summary.successful_jobs, 0)
        self.assertEqual(response.summary.avg_successful_job_duration, 0.0)

    def test_status_alias_and_unknown_status(self):
        alias = Execution.model_validate({
            "job_id": "a", "started_at": 1, "finished_at": 2,
            "attempt": 1, "status": " SUCCESS "
        })
        unknown = Execution.model_validate({
            "job_id": "b", "started_at": 1, "attempt": 1,
            "status": "unexpected-status"
        })
        self.assertEqual(alias.status, ExecutionStatus.COMPLETED)
        self.assertEqual(unknown.status, ExecutionStatus.UNKNOWN)

    def test_non_finite_timestamp_is_skipped(self):
        response = self.process_sample("non_finite_timestamp.json")
        self.assertEqual(response.validation_errors, 1)
        self.assertEqual(response.summary.total_jobs, 0)
        self.assertEqual(response.status, "OK_WITH_WARNINGS")

    def test_read_file_counts_all_records_including_invalid(self):
        response = self.process_sample("mixed_records.json")
        self.assertEqual(response.total_records, 3)
        self.assertEqual(response.validation_errors, 1)
        self.assertEqual(response.summary.total_jobs, 2)


if __name__ == "__main__":
    unittest.main()
