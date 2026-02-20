"""
JSON data loader implementation.
"""

import json
from pathlib import Path
from typing import Any, Iterator, List, Optional
from uuid import UUID

from app.domain.entities.client import Client, Gender
from app.infrastructure.data_loading.interfaces import JsonLoader
import logging

logger = logging.getLogger(__name__)


class ClientJsonLoader(JsonLoader[Client]):
    """
    Loads clients from JSON file.

    Expected JSON format:
        {"id": "...", "age": 41, "gender": "Мужчина", "net_worth": 2514729.46}

    Handles:
    - Missing/null IDs
    - Age as float or int
    - Gender mapping
    - Net worth with various formats
    """

    REQUIRED_FIELDS = {"id", "age", "gender", "net_worth"}

    def __init__(self, chunk_size: int = 1000):
        """
        Initialize JSON loader.

        Args:
            chunk_size: Number of records per chunk for streaming.
        """
        self.chunk_size = chunk_size

    def supports(self, source: Path) -> bool:
        """Check if file is JSON."""
        return source.suffix.lower() == ".json"

    def load(self, source: Path) -> Iterator[Client]:
        """
        Load clients from JSON file.

        Handles both:
        - JSON array: [{"id": "..."}, {"id": "..."}]
        - JSON lines: {"id": "..."}\n{"id": "..."}

        Args:
            source: Path to JSON file.

        Yields:
            Client entities.
        """
        if not source.exists():
            raise FileNotFoundError(f"JSON file not found: {source}")

        logger.info(f"Loading clients from {source}")

        try:
            with open(source, "r", encoding="utf-8") as f:
                first_char = f.read(1)
                f.seek(0)

                if first_char == "[":
                    yield from self._load_array(f)
                else:
                    yield from self._load_lines(f)

        except Exception as e:
            logger.error(f"Failed to load JSON file: {e}")
            raise

    def _load_array(self, file) -> Iterator[Client]:
        """Load from JSON array."""
        data = json.load(file)

        if not isinstance(data, list):
            raise ValueError("JSON must be an array of objects")

        logger.info(f"Found {len(data)} clients in JSON array")

        for item in data:
            client = self._dict_to_client(item)
            if client:
                yield client

    def _load_lines(self, file) -> Iterator[Client]:
        """Load from JSON lines format."""
        chunk: List[dict] = []

        for line_num, line in enumerate(file, 1):
            line = line.strip()
            if not line:
                continue

            try:
                item = json.loads(line)
                chunk.append(item)

                if len(chunk) >= self.chunk_size:
                    yield from self._process_chunk(chunk)
                    chunk = []

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse line {line_num}: {e}")
                continue

        if chunk:
            yield from self._process_chunk(chunk)

    def _process_chunk(self, chunk: List[dict]) -> Iterator[Client]:
        """Process a chunk of JSON objects."""
        for item in chunk:
            client = self._dict_to_client(item)
            if client:
                yield client

    def load_stream(
        self, source: Path, chunk_size: int = 1000
    ) -> Iterator[List[Client]]:
        """Load JSON data in chunks."""
        self.chunk_size = chunk_size
        clients = list(self.load(source))

        for i in range(0, len(clients), chunk_size):
            yield clients[i: i + chunk_size]

    def _dict_to_client(self, data: dict) -> Optional[Client]:
        """
        Convert JSON dict to Client entity.

        Handles:
        - Missing/null ID -> skip client
        - Age as float -> convert to int
        - Gender string -> enum mapping
        - Net worth with comma/scientific notation
        """
        try:
            client_id = self._parse_uuid(data.get("id"))
            if not client_id:
                logger.debug("Skipping client without valid ID")
                return None

            age = self._parse_age(data.get("age"))

            gender = self._parse_gender(data.get("gender"))

            net_worth = self._parse_net_worth(data.get("net_worth"))

            return Client(
                id=client_id,
                age=age,
                gender=gender,
                net_worth=net_worth,
            )

        except Exception as e:
            logger.warning(f"Failed to parse client: {e}")
            return None

    def _parse_uuid(self, value: Any) -> Optional[UUID]:
        """Parse UUID from various formats."""
        if not value or value == "null":
            return None

        try:
            return UUID(str(value).strip())
        except (ValueError, AttributeError):
            return None

    def _parse_age(self, value: Any) -> Optional[int]:
        """Parse age (handle float)."""
        if value is None or value == "":
            return None

        try:
            if isinstance(value, float):
                return int(value) if value.is_integer() else None

            if isinstance(value, str):
                value = value.strip()
                if "." in value:
                    float_val = float(value)
                    return int(float_val) if float_val.is_integer() else None
                return int(value)

            return int(value)

        except (ValueError, TypeError):
            return None

    def _parse_gender(self, value: Any) -> Gender:
        """Parse gender string to enum."""
        if not value:
            return Gender.UNKNOWN

        gender_map = {
            "Мужчина": Gender.MALE,
            "Женщина": Gender.FEMALE,
            "Другой": Gender.OTHER,
        }

        return gender_map.get(str(value).strip(), Gender.UNKNOWN)

    def _parse_net_worth(self, value: Any) -> Optional[float]:
        """Parse net worth (handle comma and scientific notation)."""
        if value is None or value == "":
            return None

        try:
            if isinstance(value, (int, float)):
                return float(value)

            str_value = str(value).strip().replace(" ", "")

            if "," in str_value and "." not in str_value:
                str_value = str_value.replace(",", ".")

            if "e" in str_value.lower():
                return float(str_value)

            return float(str_value)

        except (ValueError, TypeError):
            return None
