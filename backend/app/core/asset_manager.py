"""
3D Asset Manager for HabitatCanvas Module Library

Handles loading, validation, and caching of 3D assets (GLTF/GLB files)
for habitat modules with proper scaling and metadata management.
"""

from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import hashlib
import json
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
import mimetypes

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


@dataclass
class AssetInfo:
    """Information about a 3D asset file"""
    file_path: Path
    format: str
    size_bytes: int
    checksum: str
    last_modified: datetime
    metadata: Dict[str, Any]


class AssetCache(BaseModel):
    """Cache entry for 3D assets"""
    asset_id: str = Field(..., description="Unique asset identifier")
    file_path: str = Field(..., description="Path to asset file")
    checksum: str = Field(..., description="File checksum")
    size_bytes: int = Field(..., description="File size in bytes")
    format: str = Field(..., description="Asset format")
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = Field(default=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssetValidationResult(BaseModel):
    """Result of asset validation"""
    is_valid: bool = Field(..., description="Whether the asset is valid")
    errors: List[str] = Field(default_factory=list, description="Validation error messages")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extracted metadata")


class AssetManager:
    """
    Manages 3D assets for the module library with validation, caching, and optimization.
    
    Supports GLTF, GLB, OBJ, and FBX formats with automatic format detection,
    checksum validation, and metadata extraction.
    """
    
    SUPPORTED_FORMATS = {'.gltf', '.glb', '.obj', '.fbx'}
    CACHE_FILE = "asset_cache.json"
    
    def __init__(self, assets_root: Path, cache_ttl_hours: int = 24):
        self.assets_root = Path(assets_root)
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self._cache: Dict[str, AssetCache] = {}
        self._cache_file = self.assets_root / self.CACHE_FILE
        
        # Ensure assets directory exists
        self.assets_root.mkdir(parents=True, exist_ok=True)
        
        # Load existing cache
        self._load_cache()
        
        logger.info(f"AssetManager initialized with root: {self.assets_root}")
    
    def _load_cache(self):
        """Load asset cache from disk"""
        if self._cache_file.exists():
            try:
                with open(self._cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                for asset_id, data in cache_data.items():
                    self._cache[asset_id] = AssetCache.model_validate(data)
                
                logger.info(f"Loaded {len(self._cache)} cached assets")
            
            except Exception as e:
                logger.warning(f"Failed to load asset cache: {str(e)}")
                self._cache = {}
    
    def _save_cache(self):
        """Save asset cache to disk"""
        try:
            cache_data = {
                asset_id: cache_entry.model_dump(mode='json')
                for asset_id, cache_entry in self._cache.items()
            }
            
            with open(self._cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2, default=str)
            
            logger.debug("Asset cache saved to disk")
        
        except Exception as e:
            logger.error(f"Failed to save asset cache: {str(e)}")
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of a file"""
        hash_md5 = hashlib.md5()
        
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {str(e)}")
            return ""
    
    def _detect_format(self, file_path: Path) -> str:
        """Detect asset format from file extension"""
        suffix = file_path.suffix.lower()
        
        if suffix in self.SUPPORTED_FORMATS:
            return suffix[1:]  # Remove the dot
        
        # Try MIME type detection as fallback
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type:
            if 'gltf' in mime_type:
                return 'gltf'
            elif 'glb' in mime_type:
                return 'glb'
        
        return 'unknown'
    
    def _extract_metadata(self, file_path: Path, format: str) -> Dict[str, Any]:
        """Extract metadata from asset file"""
        metadata = {
            'file_name': file_path.name,
            'file_size': file_path.stat().st_size,
            'created': datetime.fromtimestamp(file_path.stat().st_ctime),
            'modified': datetime.fromtimestamp(file_path.stat().st_mtime),
            'format': format
        }
        
        # Format-specific metadata extraction
        if format in ['gltf', 'glb']:
            metadata.update(self._extract_gltf_metadata(file_path))
        elif format == 'obj':
            metadata.update(self._extract_obj_metadata(file_path))
        
        return metadata
    
    def _extract_gltf_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from GLTF/GLB files"""
        metadata = {}
        
        try:
            if file_path.suffix.lower() == '.gltf':
                # Parse JSON GLTF file
                with open(file_path, 'r') as f:
                    gltf_data = json.load(f)
                
                # Extract basic GLTF information
                if 'asset' in gltf_data:
                    asset_info = gltf_data['asset']
                    metadata.update({
                        'gltf_version': asset_info.get('version', 'unknown'),
                        'generator': asset_info.get('generator', 'unknown'),
                        'copyright': asset_info.get('copyright', '')
                    })
                
                # Count nodes, meshes, materials
                metadata.update({
                    'node_count': len(gltf_data.get('nodes', [])),
                    'mesh_count': len(gltf_data.get('meshes', [])),
                    'material_count': len(gltf_data.get('materials', [])),
                    'texture_count': len(gltf_data.get('textures', []))
                })
            
            else:  # GLB file
                # For GLB files, we'd need a proper GLB parser
                # For now, just mark as binary GLTF
                metadata.update({
                    'gltf_version': '2.0',
                    'format': 'binary',
                    'generator': 'unknown'
                })
        
        except Exception as e:
            logger.warning(f"Failed to extract GLTF metadata from {file_path}: {str(e)}")
            metadata['extraction_error'] = str(e)
        
        return metadata
    
    def _extract_obj_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from OBJ files"""
        metadata = {}
        
        try:
            vertex_count = 0
            face_count = 0
            material_files = []
            
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('v '):
                        vertex_count += 1
                    elif line.startswith('f '):
                        face_count += 1
                    elif line.startswith('mtllib '):
                        material_files.append(line.split(' ', 1)[1])
            
            metadata.update({
                'vertex_count': vertex_count,
                'face_count': face_count,
                'material_files': material_files
            })
        
        except Exception as e:
            logger.warning(f"Failed to extract OBJ metadata from {file_path}: {str(e)}")
            metadata['extraction_error'] = str(e)
        
        return metadata
    
    def validate_asset(self, file_path: Path) -> AssetValidationResult:
        """
        Validate a 3D asset file
        
        Args:
            file_path: Path to the asset file
        
        Returns:
            AssetValidationResult with validation status and details
        """
        errors = []
        warnings = []
        metadata = {}
        
        # Check if file exists
        if not file_path.exists():
            errors.append(f"Asset file not found: {file_path}")
            return AssetValidationResult(is_valid=False, errors=errors)
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size == 0:
            errors.append("Asset file is empty")
        elif file_size > 100 * 1024 * 1024:  # 100MB limit
            warnings.append(f"Asset file is large ({file_size / 1024 / 1024:.1f}MB)")
        
        # Detect and validate format
        format = self._detect_format(file_path)
        if format == 'unknown':
            errors.append(f"Unsupported asset format: {file_path.suffix}")
        elif format not in ['gltf', 'glb', 'obj', 'fbx']:
            warnings.append(f"Format {format} has limited support")
        
        # Extract metadata
        if not errors:
            try:
                metadata = self._extract_metadata(file_path, format)
            except Exception as e:
                warnings.append(f"Failed to extract metadata: {str(e)}")
        
        # Format-specific validation
        if format in ['gltf', 'glb'] and not errors:
            gltf_errors, gltf_warnings = self._validate_gltf(file_path, metadata)
            errors.extend(gltf_errors)
            warnings.extend(gltf_warnings)
        
        is_valid = len(errors) == 0
        
        return AssetValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
    
    def _validate_gltf(self, file_path: Path, metadata: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate GLTF-specific requirements"""
        errors = []
        warnings = []
        
        # Check GLTF version
        gltf_version = metadata.get('gltf_version', '')
        if not gltf_version.startswith('2.'):
            warnings.append(f"GLTF version {gltf_version} may not be fully supported")
        
        # Check complexity
        mesh_count = metadata.get('mesh_count', 0)
        if mesh_count > 50:
            warnings.append(f"High mesh count ({mesh_count}) may impact performance")
        
        texture_count = metadata.get('texture_count', 0)
        if texture_count > 20:
            warnings.append(f"High texture count ({texture_count}) may impact loading time")
        
        return errors, warnings
    
    def register_asset(self, asset_id: str, file_path: Path, validate: bool = True) -> bool:
        """
        Register a 3D asset in the manager
        
        Args:
            asset_id: Unique identifier for the asset
            file_path: Path to the asset file (relative to assets_root)
            validate: Whether to validate the asset
        
        Returns:
            True if registration successful, False otherwise
        """
        full_path = self.assets_root / file_path
        
        # Validate asset if requested
        if validate:
            validation_result = self.validate_asset(full_path)
            if not validation_result.is_valid:
                logger.error(f"Asset validation failed for {asset_id}: {validation_result.errors}")
                return False
            
            if validation_result.warnings:
                logger.warning(f"Asset validation warnings for {asset_id}: {validation_result.warnings}")
        
        # Calculate checksum
        checksum = self._calculate_checksum(full_path)
        if not checksum:
            logger.error(f"Failed to calculate checksum for {asset_id}")
            return False
        
        # Detect format
        format = self._detect_format(full_path)
        
        # Create cache entry
        cache_entry = AssetCache(
            asset_id=asset_id,
            file_path=str(file_path),
            checksum=checksum,
            size_bytes=full_path.stat().st_size,
            format=format,
            metadata=self._extract_metadata(full_path, format)
        )
        
        self._cache[asset_id] = cache_entry
        self._save_cache()
        
        logger.info(f"Registered asset: {asset_id} -> {file_path}")
        return True
    
    def get_asset_info(self, asset_id: str) -> Optional[AssetCache]:
        """Get cached information about an asset"""
        cache_entry = self._cache.get(asset_id)
        
        if cache_entry:
            # Update access statistics
            cache_entry.last_accessed = datetime.utcnow()
            cache_entry.access_count += 1
            self._save_cache()
        
        return cache_entry
    
    def get_asset_path(self, asset_id: str) -> Optional[Path]:
        """Get the full path to an asset file"""
        cache_entry = self._cache.get(asset_id)
        if cache_entry:
            return self.assets_root / cache_entry.file_path
        return None
    
    def verify_asset_integrity(self, asset_id: str) -> bool:
        """Verify that an asset file hasn't been corrupted"""
        cache_entry = self._cache.get(asset_id)
        if not cache_entry:
            return False
        
        asset_path = self.assets_root / cache_entry.file_path
        if not asset_path.exists():
            return False
        
        current_checksum = self._calculate_checksum(asset_path)
        return current_checksum == cache_entry.checksum
    
    def list_assets(self, format_filter: Optional[str] = None) -> List[AssetCache]:
        """List all registered assets, optionally filtered by format"""
        assets = list(self._cache.values())
        
        if format_filter:
            assets = [asset for asset in assets if asset.format == format_filter]
        
        return sorted(assets, key=lambda x: x.asset_id)
    
    def remove_asset(self, asset_id: str, delete_file: bool = False) -> bool:
        """Remove an asset from the manager"""
        if asset_id not in self._cache:
            return False
        
        cache_entry = self._cache[asset_id]
        
        if delete_file:
            asset_path = self.assets_root / cache_entry.file_path
            try:
                if asset_path.exists():
                    asset_path.unlink()
                    logger.info(f"Deleted asset file: {asset_path}")
            except Exception as e:
                logger.error(f"Failed to delete asset file {asset_path}: {str(e)}")
        
        del self._cache[asset_id]
        self._save_cache()
        
        logger.info(f"Removed asset: {asset_id}")
        return True
    
    def cleanup_cache(self, max_age_days: int = 30) -> int:
        """Remove old cache entries that haven't been accessed recently"""
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        removed_count = 0
        
        assets_to_remove = [
            asset_id for asset_id, cache_entry in self._cache.items()
            if cache_entry.last_accessed < cutoff_date
        ]
        
        for asset_id in assets_to_remove:
            self.remove_asset(asset_id, delete_file=False)
            removed_count += 1
        
        logger.info(f"Cleaned up {removed_count} old cache entries")
        return removed_count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self._cache:
            return {
                'total_assets': 0,
                'total_size_mb': 0,
                'formats': {},
                'most_accessed': None
            }
        
        total_size = sum(entry.size_bytes for entry in self._cache.values())
        format_counts = {}
        
        for entry in self._cache.values():
            format_counts[entry.format] = format_counts.get(entry.format, 0) + 1
        
        most_accessed = max(self._cache.values(), key=lambda x: x.access_count)
        
        return {
            'total_assets': len(self._cache),
            'total_size_mb': total_size / (1024 * 1024),
            'formats': format_counts,
            'most_accessed': {
                'asset_id': most_accessed.asset_id,
                'access_count': most_accessed.access_count
            }
        }


# Global asset manager instance
_asset_manager: Optional[AssetManager] = None


def get_asset_manager() -> AssetManager:
    """Get the global asset manager instance"""
    global _asset_manager
    if _asset_manager is None:
        assets_path = Path("assets/modules")
        _asset_manager = AssetManager(assets_path)
    return _asset_manager


def initialize_asset_manager(assets_root: Path, cache_ttl_hours: int = 24) -> AssetManager:
    """Initialize the global asset manager with custom settings"""
    global _asset_manager
    _asset_manager = AssetManager(assets_root, cache_ttl_hours)
    return _asset_manager