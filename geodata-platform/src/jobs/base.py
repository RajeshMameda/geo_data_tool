from enum import Enum, auto
from typing import List, Dict, Any, Optional, TypeVar, Generic
from pydantic import BaseModel, validator, Field
from datetime import datetime
import uuid
from loguru import logger

T = TypeVar('T')

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobStage(str, Enum):
    VALIDATE = "validate"
    PREPARE = "prepare"
    UPLOAD = "upload"
    FINALIZE = "finalize"

class JobParameters(BaseModel):
    file_path: str = Field(..., description="Path to the input file")
    target_crs: str = Field("EPSG:4326", description="Target CRS (e.g., EPSG:4326)")
    chunk_size: int = Field(5000, description="Number of features per chunk (1000-50000)")

    @validator('chunk_size')
    def validate_chunk_size(cls, v):
        if not 1000 <= v <= 50000:
            raise ValueError('chunk_size must be between 1000 and 50000')
        return v

class JobBaseMixin(Generic[T]):
    JOB_TYPE: str
    STAGES = [JobStage.VALIDATE, JobStage.PREPARE, JobStage.UPLOAD, JobStage.FINALIZE]
    
    def __init__(self, parameters: Dict[str, Any]):
        self.parameters = JobParameters(**parameters)
        self.job_id = str(uuid.uuid4())
        self.status = JobStatus.PENDING
        self.current_stage = None
        self.results = {}
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.errors = []

    def update_status(self, status: JobStatus, error: Optional[str] = None):
        """Update job status and log changes."""
        self.status = status
        self.updated_at = datetime.utcnow()
        if error:
            self.errors.append(error)
            logger.error(f"Job {self.job_id} failed: {error}")
        else:
            logger.info(f"Job {self.job_id} status: {status}")

    def create_tasks_for_stage(self, stage: JobStage) -> List[Dict[str, Any]]:
        """Create tasks for the given stage. Must be implemented by subclasses."""
        raise NotImplementedError

    def finalize_job(self) -> Dict[str, Any]:
        """Finalize job processing. Must be implemented by subclasses."""
        raise NotImplementedError

    def run_stage(self, stage: JobStage):
        """Execute all tasks for a given stage."""
        if stage not in self.STAGES:
            raise ValueError(f"Invalid stage: {stage}")

        self.current_stage = stage
        self.update_status(JobStatus.RUNNING)
        
        try:
            tasks = self.create_tasks_for_stage(stage)
            # In a real implementation, you would execute tasks here
            # and update self.results with the outcomes
            logger.info(f"Executing {len(tasks)} tasks for stage {stage}")
            
        except Exception as e:
            self.update_status(JobStatus.FAILED, str(e))
            raise