# Minimal Execution Processor

Small Python/Pydantic v2 example for reading execution records from JSON, validating them, calculating durations, and summarizing logical jobs.

## Requirements

- Python 3.10+
- Pydantic v2

## Run

```bash
python -m pip install "pydantic>=2,<3"
python main.py sample_inputs/retry_success.json
```

Try other inputs by replacing the filename. To see warnings:

```bash
python main.py sample_inputs/malformed_record.json --verbose
```

## Tests

From the project root:

```bash
python -m unittest discover -s tests -v
```

## Input schema

Each JSON file must contain a list of records:

```json
[
  {
    "job_id": "job-1",
    "status": "completed",
    "started_at": 100,
    "finished_at": 105,
    "attempt": 1
  }
]
```

Timestamps are Unix-epoch numbers in seconds. `finished_at` may be `null` or omitted for unfinished jobs. Status values are case-insensitive; `success`/`succeeded` map to `completed`, and `failure`/`error` map to `failed`. Unknown status strings become `unknown`.

## Summary semantics

- `total_jobs`: distinct `job_id` values among valid records. If every record for a job is malformed, that job cannot be counted.
- The highest attempt number determines the outcome.
- Identical records for the highest attempt count once; conflicting highest-attempt records are excluded from success/failure counts.
- A job is considered retried if any valid record has `attempt > 1`.
- The average duration includes only completed highest-attempt records with a valid duration. Completed jobs with missing/invalid duration still count as successful, but do not enter the average. If there are no valid durations, the average is `0.0`.
- `OK_WITH_WARNINGS` means one or more records were skipped for schema validation errors. A semantically invalid duration is represented as `null` and excluded from the average; it does not make the file-level status a warning.
- Missing files, invalid JSON syntax, and a non-list JSON root raise `FileNotFoundError`, `JSONDecodeError`, and `ValueError`, respectively.
