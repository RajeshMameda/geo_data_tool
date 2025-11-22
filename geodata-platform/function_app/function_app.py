# In function_app/function_app.py
import sys
import os
from pathlib import Path
import azure.functions as func
from pydantic import ValidationError
import json
from datetime import datetime

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now import using the full path from project root
from src.utils import run_migrations
from src.models.job import JobModel, JobStatus, JobStage
from src.utils.logging import configure_logging
from src.utils.database import DatabaseSession
from src.workers.job_processor import process_job

# Configure logging (single instance)
logger = configure_logging(os.getenv("LOG_LEVEL", "INFO"))

try:
    run_migrations()
    logger.info("Database migrations completed successfully")
except Exception as e:
    logger.error(f"Error running database migrations: {str(e)}")

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="ingest", methods=["POST"])
def http_ingest(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP endpoint for starting a new vector ingestion job."""
    try:
        # Parse request
        req_body = req.get_json()
        
        # Validate required fields
        required_fields = ["file_path", "target_crs", "chunk_size"]
        if not all(field in req_body for field in required_fields):
            raise ValueError(f"Missing required fields. Required: {required_fields}")
        
        # Create job in database
        with DatabaseSession() as session:
            job = JobModel(
                job_type="vector_ingestion",
                status=JobStatus.PENDING,
                current_stage=JobStage.VALIDATE,
                parameters=req_body
            )
            session.add(job)
            session.commit()
            
            # Start processing (in background)
            # In production, use a task queue like Celery or Azure Durable Functions
            process_job(job.id)
            
            return func.HttpResponse(
                json.dumps({
                    "job_id": job.id,
                    "status": job.status.value,
                    "message": "Job started successfully",
                    "next_stage": JobStage.VALIDATE.value
                }),
                mimetype="application/json",
                status_code=202
            )
            
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "error": "Invalid request parameters",
                "details": str(e)
            }),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                "error": "Failed to create job",
                "details": str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

@app.route(route="jobs/{job_id}", methods=["GET"])
def get_job_status(req: func.HttpRequest) -> func.HttpResponse:
    """Get the status of a job."""
    try:
        job_id = req.route_params.get("job_id")
        
        with DatabaseSession() as session:
            job = session.query(JobModel).filter(JobModel.id == job_id).first()
            if not job:
                return func.HttpResponse(
                    json.dumps({"error": "Job not found"}),
                    status_code=404,
                    mimetype="application/json"
                )
                
            return func.HttpResponse(
                json.dumps(job.to_dict()),
                mimetype="application/json"
            )
            
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                "error": "Failed to get job status",
                "details": str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

# Health check endpoint
@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    try:
        # Test database connection
        with DatabaseSession() as session:
            session.execute("SELECT 1")
            
        return func.HttpResponse(
            json.dumps({
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat()
            }),
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "status": "unhealthy",
                "error": str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )