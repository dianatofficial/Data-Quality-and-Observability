import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Union
from uuid import uuid4

import pandas as pd


class BatchExtractor:
    """Extracts, parses, and enriches raw incoming data files and payloads."""

    @staticmethod
    def extract_from_json(file_path: Union[str, Path]) -> List[Dict[str, Any]]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Source data file not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "records" in data:
            return data["records"]
        elif isinstance(data, dict):
            return [data]
        else:
            raise ValueError("Unsupported JSON structure: expected list or dict with 'records'")

    @staticmethod
    def extract_from_csv(file_path: Union[str, Path]) -> List[Dict[str, Any]]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        df = pd.read_csv(path)
        # Convert NaN to None for clean Python dictionary handling
        return df.where(pd.notnull(df), None).to_dict(orient="records")

    @staticmethod
    def compute_batch_checksum(records: List[Dict[str, Any]]) -> str:
        serialized = json.dumps(records, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
