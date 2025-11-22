from typing import Dict, Any, List
from .base import JobBaseMixin, JobStage, JobStatus
from loguru import logger

class VectorIngestionJob(JobBaseMixin):
    """Job for ingesting vector data into the system."""
    
    JOB_TYPE = "vector_ingestion"

    def create_tasks_for_stage(self, stage: JobStage) -> List[Dict[str, Any]]:
        """Create tasks for the specified stage of processing."""
        if stage == JobStage.VALIDATE:
            return [{
                "function": "validate_vector_file",
                "args": [self.parameters.file_path],
                "kwargs": {"target_crs": self.parameters.target_crs}
            }]
        elif stage == JobStage.PREPARE:
            return [{
                "function": "prepare_and_chunk",
                "args": [self.parameters.file_path],
                "kwargs": {"chunk_size": self.parameters.chunk_size}
            }]
        elif stage == JobStage.UPLOAD:
            # This would be generated based on the chunks from PREPARE stage
            chunks = self.results.get('chunks', [])
            return [{
                "function": "upload_chunk",
                "args": [chunk],
                "kwargs": {"job_id": self.job_id}
            } for chunk in chunks]
        elif stage == JobStage.FINALIZE:
            return [{
                "function": "finalize_ingestion",
                "args": [self.job_id],
                "kwargs": {}
            }]
        return []

    def finalize_job(self) -> Dict[str, Any]:
        """Finalize the job and return results."""
        self.update_status(JobStatus.COMPLETED)
        return {
            "job_id": self.job_id,
            "status": self.status,
            "results": self.results,
            "processed_at": self.updated_at.isoformat()
        }