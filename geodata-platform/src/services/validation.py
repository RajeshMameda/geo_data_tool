from typing import Dict, Any
import fiona
from loguru import logger

def validate_vector_file(file_path: str, target_crs: str) -> Dict[str, Any]:
    """Validate a vector file for format, CRS, and geometry."""
    try:
        with fiona.open(file_path) as src:
            # Check CRS
            file_crs = src.crs.get('init', '').lower() if src.crs else None
            if file_crs and file_crs != target_crs.lower():
                logger.warning(f"File CRS ({file_crs}) differs from target CRS ({target_crs})")

            # Check geometry types
            geom_types = set(feature['geometry']['type'] for feature in src)
            if not geom_types:
                raise ValueError("No geometries found in the file")

            # Get feature count
            feature_count = len(src)

        return {
            "valid": True,
            "crs": file_crs or "unknown",
            "geometry_types": list(geom_types),
            "feature_count": feature_count
        }

    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        return {
            "valid": False,
            "error": str(e)
        }