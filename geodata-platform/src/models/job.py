from sqlalchemy import Column, String, Enum as SQLEnum, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid
from enum import Enum as PyEnum  # Add this import

Base = declarative_base()

# Update these enums to inherit from PyEnum
class JobStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobStage(str, PyEnum):
    VALIDATE = "validate"
    PREPARE = "prepare"
    UPLOAD = "upload"
    FINALIZE = "finalize"

class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_type = Column(String, nullable=False)
    # Update these lines to use SQLEnum with the enum values
    status = Column(SQLEnum(JobStatus, values_callable=lambda x: [e.value for e in JobStatus]), default=JobStatus.PENDING)
    current_stage = Column(SQLEnum(JobStage, values_callable=lambda x: [e.value for e in JobStage]), nullable=True)
    parameters = Column(JSON, nullable=False)
    results = Column(JSON, default=dict)
    errors = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "job_id": self.id,
            "job_type": self.job_type,
            "status": self.status.value if hasattr(self.status, 'value') else self.status,
            "current_stage": self.current_stage.value if self.current_stage else None,
            "parameters": self.parameters,
            "results": self.results,
            "errors": self.errors,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }