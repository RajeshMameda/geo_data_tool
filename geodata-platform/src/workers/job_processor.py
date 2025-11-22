import logging
from datetime import datetime
from src.models.job import JobModel, JobStatus, JobStage
from utils.database import DatabaseSession
from workers.vector_processor import process_vector_file

logger = logging.getLogger(__name__)

def process_job(job_id: str):
    """Process a job through all its stages."""
    with DatabaseSession() as session:
        try:
            job = session.query(JobModel).filter(JobModel.id == job_id).first()
            if not job:
                logger.error(f"Job {job_id} not found")
                return

            # Process each stage
            for stage in [JobStage.VALIDATE, JobStage.PREPARE, JobStage.UPLOAD, JobStage.FINALIZE]:
                job.current_stage = stage
                job.status = JobStatus.RUNNING
                job.updated_at = datetime.utcnow()
                session.commit()

                try:
                    if stage == JobStage.VALIDATE:
                        # Validate the input file
                        is_valid = validate_file(job.parameters["file_path"])
                        if not is_valid:
                            raise ValueError("Invalid file format or content")
                            
                    elif stage == JobStage.PREPARE:
                        # Process and chunk the file
                        chunks = process_vector_file(
                            job.parameters["file_path"],
                            job.parameters.get("chunk_size", 5000),
                            job.parameters.get("target_crs", "EPSG:4326")
                        )
                        job.results["chunks"] = [str(c) for c in chunks]
                        job.results["chunk_count"] = len(chunks)
                        
                    elif stage == JobStage.UPLOAD:
                        # Upload chunks to the database
                        uploaded_count = upload_chunks(
                            job.results.get("chunks", []),
                            job_id=job.id
                        )
                        job.results["uploaded_features"] = uploaded_count
                        
                    elif stage == JobStage.FINALIZE:
                        # Finalize the job
                        job.results["completed_at"] = datetime.utcnow().isoformat()
                        job.results["status"] = "success"
                        
                except Exception as e:
                    job.status = JobStatus.FAILED
                    job.errors.append({
                        "stage": stage.value, 
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    session.commit()
                    logger.error(f"Error in stage {stage.value}: {str(e)}", exc_info=True)
                    raise

            # Only mark as completed if all stages succeeded
            job.status = JobStatus.COMPLETED
            job.results["status"] = "completed"
            
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)
            job.status = JobStatus.FAILED
            job.errors.append({
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
        finally:
            job.updated_at = datetime.utcnow()
            # Ensure results is always a dictionary
            if not isinstance(job.results, dict):
                job.results = {}
            session.commit()

def validate_file(file_path: str) -> bool:
    """Validate the input file."""
    # Implement actual validation logic
    return True

def upload_chunks(chunks, job_id=None, db_url=None):
    """
    Upload chunks to the database.
    
    Args:
        chunks: List of chunk file paths
        job_id: ID of the job these chunks belong to
        db_url: Optional database URL (will use DATABASE_URL from env if not provided)
    """
    if not chunks:
        logger.warning("No chunks to upload")
        return

    if not job_id:
        logger.error("No job_id provided for chunk upload")
        raise ValueError("job_id is required for uploading chunks")

    if not db_url:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise ValueError("No database URL provided and DATABASE_URL environment variable not set")

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        total_features = 0
        
        for chunk_path in chunks:
            if not os.path.exists(chunk_path):
                logger.warning(f"Chunk file not found: {chunk_path}")
                continue
                
            try:
                # Read the chunk using geopandas
                gdf = gpd.read_file(chunk_path)
                
                # Convert to features and save to database
                for _, row in gdf.iterrows():
                    feature = FeatureModel(
                        job_id=job_id,
                        properties=row.drop('geometry', errors='ignore').to_dict(),
                        geometry=row.geometry.__geo_interface__ if hasattr(row, 'geometry') and row.geometry else None
                    )
                    session.add(feature)
                    total_features += 1
                
                # Commit after each chunk
                session.commit()
                logger.info(f"Uploaded chunk {chunk_path} with {len(gdf)} features")
                
            except Exception as e:
                session.rollback()
                logger.error(f"Error processing chunk {chunk_path}: {str(e)}")
                raise
                
        logger.info(f"Successfully uploaded {total_features} features from {len(chunks)} chunks")
        return total_features
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error in upload_chunks: {str(e)}")
        raise
    finally:
        session.close()