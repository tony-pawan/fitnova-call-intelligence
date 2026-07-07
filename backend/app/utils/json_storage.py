import os
import json
from typing import Any, Union
from backend.app.core.logging import get_logger

logger = get_logger("SYSTEM")

def save_json(file_path: str, data: Union[dict, list]) -> bool:
    """
    Persists dictionary/list data to a JSON file. Creates parent directories if missing.
    Uses utf-8 encoding.
    """
    try:
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
            
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to write JSON metadata to '{file_path}': {e}")
        return False

def load_json(file_path: str) -> Any:
    """
    Loads JSON data from file. Returns None if file is missing or fails to parse.
    """
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON from '{file_path}': {e}")
        return None
