import os
import logging
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from .database import get_database_url, get_session

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), '..', 'migrations')

def run_migrations():
    """Run all pending database migrations."""
    logger.info("Checking for pending database migrations...")
    
    # Get the highest applied migration version
    with get_session() as session:
        # Create migrations table if it doesn't exist
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                version INTEGER NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))
        session.commit()
        
        # Get the current migration version
        result = session.execute(text("""
            SELECT MAX(version) as current_version 
            FROM migrations
        """)).fetchone()
        current_version = result[0] if result[0] is not None else 0
    
    # Find and apply new migrations
    migration_files = sorted([
        f for f in os.listdir(MIGRATIONS_DIR)
        if f.endswith('.sql') and f.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'))
    ])
    
    applied_migrations = 0
    
    for migration_file in migration_files:
        version = int(migration_file.split('_')[0])
        if version > current_version:
            try:
                with get_session() as session:
                    # Read the migration file
                    with open(os.path.join(MIGRATIONS_DIR, migration_file), 'r') as f:
                        sql = f.read()
                    
                    # Split SQL into individual statements and execute them one by one
                    logger.info(f"Applying migration: {migration_file}")
                    for statement in sql.split(';'):
                        statement = statement.strip()
                        if statement:  # Skip empty statements
                            session.execute(text(statement))
                    
                    # Record the migration
                    session.execute(
                        text("""
                            INSERT INTO migrations (version, name)
                            VALUES (:version, :name)
                        """),
                        {"version": version, "name": migration_file}
                    )
                    session.commit()
                    applied_migrations += 1
                    
            except SQLAlchemyError as e:
                logger.error(f"Error applying migration {migration_file}: {str(e)}")
                raise
    
    if applied_migrations == 0:
        logger.info("Database is up to date")
    else:
        logger.info(f"Applied {applied_migrations} migration(s)")
    
    return applied_migrations