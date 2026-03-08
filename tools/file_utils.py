"""
File operation utilities for the newsletter automation pipeline.
"""

import os
import json
import hashlib
import shutil
import logging
from pathlib import Path
from typing import Union, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Create directory if it doesn't exist.

    Args:
        path: Directory path to create

    Returns:
        Path object for the directory
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def read_file(path: Union[str, Path], encoding: str = 'utf-8') -> str:
    """
    Read file contents with error handling.

    Args:
        path: File path to read
        encoding: File encoding (default: utf-8)

    Returns:
        File contents as string

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    try:
        return file_path.read_text(encoding=encoding)
    except Exception as e:
        logger.error(f"Error reading file {path}: {e}")
        raise IOError(f"Cannot read file {path}: {e}")


def write_file(
    path: Union[str, Path],
    content: str,
    encoding: str = 'utf-8',
    create_dirs: bool = True
) -> Path:
    """
    Write content to file with error handling.

    Args:
        path: File path to write
        content: Content to write
        encoding: File encoding (default: utf-8)
        create_dirs: Create parent directories if needed

    Returns:
        Path object for the written file
    """
    file_path = Path(path)

    if create_dirs:
        ensure_directory(file_path.parent)

    try:
        file_path.write_text(content, encoding=encoding)
        logger.debug(f"Written file: {path}")
        return file_path
    except Exception as e:
        logger.error(f"Error writing file {path}: {e}")
        raise IOError(f"Cannot write file {path}: {e}")


def read_json(path: Union[str, Path]) -> dict:
    """
    Read and parse JSON file.

    Args:
        path: Path to JSON file

    Returns:
        Parsed JSON as dict
    """
    content = read_file(path)
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {e}")
        raise ValueError(f"Invalid JSON in {path}: {e}")


def write_json(
    path: Union[str, Path],
    data: dict,
    indent: int = 2,
    create_dirs: bool = True
) -> Path:
    """
    Write dict to JSON file.

    Args:
        path: Path for JSON file
        data: Data to serialize
        indent: JSON indentation
        create_dirs: Create parent directories if needed

    Returns:
        Path object for the written file
    """
    content = json.dumps(data, indent=indent, ensure_ascii=False, default=str)
    return write_file(path, content, create_dirs=create_dirs)


def get_file_hash(path: Union[str, Path], algorithm: str = 'sha256') -> str:
    """
    Calculate hash of file contents for deduplication.

    Args:
        path: Path to file
        algorithm: Hash algorithm (default: sha256)

    Returns:
        Hex digest of file hash
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    hash_func = hashlib.new(algorithm)
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hash_func.update(chunk)

    return hash_func.hexdigest()


def cleanup_temp_files(
    temp_dir: Union[str, Path],
    max_age_days: int = 7,
    dry_run: bool = False
) -> list:
    """
    Clean up old temporary files.

    Args:
        temp_dir: Temporary directory path
        max_age_days: Delete files older than this
        dry_run: If True, just report what would be deleted

    Returns:
        List of deleted (or would-be-deleted) file paths
    """
    temp_path = Path(temp_dir)
    if not temp_path.exists():
        return []

    deleted = []
    now = datetime.now()

    for file_path in temp_path.rglob('*'):
        if file_path.is_file():
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            age_days = (now - mtime).days

            if age_days > max_age_days:
                if dry_run:
                    logger.info(f"Would delete: {file_path}")
                else:
                    try:
                        file_path.unlink()
                        logger.info(f"Deleted: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete {file_path}: {e}")
                        continue
                deleted.append(str(file_path))

    return deleted


def get_output_path(
    base_dir: Union[str, Path],
    prefix: str = "",
    suffix: str = "",
    extension: str = ".md",
    use_date: bool = True
) -> Path:
    """
    Generate a timestamped output file path.

    Args:
        base_dir: Base directory for output
        prefix: File name prefix
        suffix: File name suffix
        extension: File extension
        use_date: Include date in filename

    Returns:
        Path for output file
    """
    ensure_directory(base_dir)

    if use_date:
        date_str = datetime.now().strftime("%Y-%m")
        filename = f"{prefix}{date_str}{suffix}{extension}"
    else:
        filename = f"{prefix}{suffix}{extension}"

    return Path(base_dir) / filename
