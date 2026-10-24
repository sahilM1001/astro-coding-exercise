import json
from pathlib import Path
from typing import List
import logging
from pydantic import ValidationError
from models import Execution, JSONProcessingResult, ProcessingResponse, ExecutionStatus, ExecutionSummary



logger = logging.getLogger(__name__)

class ExecutionProcessor:
    def __init__(self) -> None:
        pass

    def read_file(self, file_path: str) -> JSONProcessingResult:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found at path {file_path}")
        
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            raise ValueError("Expected the JSON root to be a list of execution records")
        
        executions = []
        invalid = 0
        for index, obj in enumerate(data):
            try:
                executions.append(Execution.model_validate(obj))
            except ValidationError as e:
                invalid += 1
                logger.warning("Skipping malformed record at index %d: %s. Errors: %s",
                    index,
                    obj,
                    e) 
                
        return JSONProcessingResult(data=executions, validation_errors=invalid, total_records = len(data))
    
    def calculate_execution_duration(self, record: Execution) -> float | None:
        if record.status not in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED):
            return None
         
        if record.finished_at is None or record.finished_at < record.started_at:
            return None

        return record.finished_at - record.started_at

    def calculate_summary(self, records: list[Execution]) -> ExecutionSummary:
        # Group all attempts by logical job.
        jobs: dict[str, list[Execution]] = {}

        for record in records:
            jobs.setdefault(record.job_id, []).append(record)

        total_jobs = len(jobs)
        successful_jobs = 0
        failed_jobs = 0
        retried_jobs = 0
        successful_durations: list[float] = []

        for job_id, attempts in jobs.items():
            # A job required retries if any attempt number exceeds 1.
            if any(record.attempt > 1 for record in attempts):
                retried_jobs += 1

            # Find the highest attempt number for this job.
            max_attempt = max(record.attempt for record in attempts)
            latest_attempts = [
                record for record in attempts
                if record.attempt == max_attempt
            ]

            # Conflicting records for the latest attempt make the
            # logical job's final state ambiguous.
            signatures = {
                (
                    record.status,
                    record.started_at,
                    record.finished_at,
                )
                for record in latest_attempts
            }

            if len(signatures) > 1:
                logger.warning(
                    "Conflicting records for job_id=%s, attempt=%d; "
                    "excluding from outcome metrics",
                    job_id,
                    max_attempt,
                )
                continue

            # Identical duplicate records are treated as one attempt.
            latest = latest_attempts[0]

            if latest.status == ExecutionStatus.COMPLETED:
                successful_jobs += 1

                if latest.execution_duration is not None:
                    successful_durations.append(latest.execution_duration)

            elif latest.status == ExecutionStatus.FAILED:
                failed_jobs += 1

        avg_duration = (
            sum(successful_durations) / len(successful_durations)
            if successful_durations
            else 0.0
        )

        return ExecutionSummary(
            total_jobs=total_jobs,
            successful_jobs=successful_jobs,
            failed_jobs=failed_jobs,
            avg_successful_job_duration=avg_duration,
            retried_jobs=retried_jobs,
        )

    def process(self, file_path: str) -> ProcessingResponse:
        # read file
        json_processing_resp = self.read_file(file_path)
        records = json_processing_resp.data
        validation_errors = json_processing_resp.validation_errors
        total_records = json_processing_resp.total_records

        #update execution duration
        for record in records:
            record.execution_duration = self.calculate_execution_duration(record)

        # calculate summary
        summary = self.calculate_summary(records)

        return ProcessingResponse(
        status = "OK_WITH_WARNINGS" if validation_errors else "OK",
        summary=summary,
        validation_errors=validation_errors,
        total_records=total_records,
    )

