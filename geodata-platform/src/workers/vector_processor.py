import os
import fiona
from fiona.crs import from_epsg
from shapely.geometry import shape, mapping
import geopandas as gpd
from typing import List, Dict, Any
import tempfile
import logging

logger = logging.getLogger(__name__)

def process_vector_file(file_path: str, chunk_size: int, target_crs: str = "EPSG:4326") -> List[Dict[str, Any]]:
    """
    Process a vector file and split it into chunks.
    
    Args:
        file_path: Path to the input vector file
        chunk_size: Number of features per chunk
        target_crs: Target CRS (e.g., "EPSG:4326")
        
    Returns:
        List of chunk file paths
    """
    chunks = []
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Read the input file
        gdf = gpd.read_file(file_path)
        
        # Reproject if needed
        if gdf.crs != target_crs:
            gdf = gdf.to_crs(target_crs)
        
        # Split into chunks
        total_features = len(gdf)
        for i in range(0, total_features, chunk_size):
            chunk = gdf.iloc[i:i + chunk_size]
            chunk_path = os.path.join(temp_dir, f"chunk_{i}.geojson")
            chunk.to_file(chunk_path, driver="GeoJSON")
            chunks.append(chunk_path)
            
        return chunks
        
    except Exception as e:
        logger.error(f"Error processing vector file: {str(e)}")
        raise

def validate_vector_file(file_path: str) -> bool:
    """
    Validate that a file is a valid vector file.
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # Try to open the file with fiona
        with fiona.open(file_path) as src:
            # Check if it has features
            if len(src) == 0:
                logger.warning(f"File {file_path} is empty")
                return False
                
            # Check CRS
            if not src.crs:
                logger.warning(f"File {file_path} has no CRS")
                
        return True
        
    except Exception as e:
        logger.error(f"Invalid vector file {file_path}: {str(e)}")
        return False