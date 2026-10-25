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

## Review notes (post-exercise)



Automated checks: all 15 unit tests pass (`python -m unittest discover -s tests -v`). Sample inputs under `sample_inputs/` behave consistently with the semantics above.



### Behavior



- **Latest attempt wins.** If attempt 1 completed and attempt 2 is `running` or an unknown status string, the job stays in `total_jobs` (and may count as `retried_jobs`) but is not included in `successful_jobs` or `failed_jobs`.

- **Conflicting latest attempts.** Duplicate highest-attempt rows with different status/timestamps are excluded from success/failure counts but still contribute to `total_jobs` and `retried_jobs` when `attempt > 1` appears anywhere for that job.





###Implementation improvements



1. **Expose unresolved outcomes in the summary** — Add something like `unresolved_jobs` (or split into `running_jobs`, `unknown_jobs`, `conflicted_jobs`) in `ExecutionSummary` when the highest attempt is not a clear `completed`/`failed` winner, so callers can reconcile `total_jobs` with success/failure counts without reading logs.

2. **Tighten retry semantics** — Today `retried_jobs` increments if *any* record has `attempt > 1`, even when the latest attempt is ambiguous or non-terminal. Optionally count retries only when `max(attempt) > 1` *and* a definitive latest outcome exists, or when a later attempt exists after a failed earlier one (closer to “required retries” in the exercise wording).

3. **Richer conflict detection** — Conflicts are detected only on `(status, started_at, finished_at)`. Two rows with the same timestamps but different `job_id` casing or extra ignored fields are already handled; consider whether differing `execution_duration`-relevant edge cases (e.g. one row missing `finished_at`) should count as conflict vs invalid semantics.

4. **Typed processing status** — Replace free-form `ProcessingResponse.status: str` with a small enum (`OK`, `OK_WITH_WARNINGS`) so downstream code and tests do not rely on string literals.

