"""
JSON data loader implementation with orjson.
"""

import orjson
from pathlib import Path
from typing import Any, Iterator, List, Optional
from uuid import UUID

from structlog import get_logger

from app.domain.entities.client import Client, Gender
from app.infrastructure.data_loading.interfaces import JsonLoader

logger = get_logger(__name__)


class ClientJsonLoader(JsonLoader[Client]):
    """
    Loads clients from JSON file using orjson.

    Expected JSON format:
        {"id": "...", "age": 41, "gender": "Мужчина", "net_worth": 2514729.46}

    Handles:
    - Missing/null IDs
    - Age as float or int
    - Gender mapping
    - Net worth with various formats
    """

    REQUIRED_FIELDS = {"id", "age", "gender", "net_worth"}
    MAX_FILE_SIZE = 100 * 1024 * 1024
    MAX_RECORD_SIZE = 1024 * 1024
    MAX_CHUNK_SIZE = 10000

    def __init__(self, chunk_size: int = 1000):
        """
        Initialize JSON loader.

        Args:
            chunk_size: Number of records per chunk for streaming.
        """
        self.chunk_size = min(chunk_size, self.MAX_CHUNK_SIZE)

    def supports(self, source: Path) -> bool:
        """Check if file is JSON."""
        if not source.exists():
            return False
        return source.suffix.lower() == ".json"

    def _validate_file(self, source: Path) -> None:
        """Validate file before processing."""
        if not source.exists():
            raise FileNotFoundError(f"JSON file not found: {source}")

        if not source.is_file():
            raise ValueError(f"Path is not a file: {source}")

        file_size = source.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File too large: {file_size} bytes > {self.MAX_FILE_SIZE} "
                "bytes"
            )

        if file_size == 0:
            raise ValueError(f"File is empty: {source}")

    def load(self, source: Path) -> Iterator[Client]:
        """
        Load clients from JSON file using orjson.

        Handles both:
        - JSON array: [{"id": "..."}, {"id": "..."}]
        - JSON lines: {"id": "..."}\n{"id": "..."}

        Args:
            source: Path to JSON file.

        Yields:
            Client entities.
        """
        self._validate_file(source)

        logger.info(f"Loading clients from {source}")

        try:
            with open(source, "rb") as f:
                first_byte = f.read(1)
                f.seek(0)

                if first_byte == b"[":
                    yield from self._load_array_safe(f)
                else:
                    yield from self._load_lines_safe(f)

        except orjson.JSONDecodeError as e:
            logger.error(f"JSON decode error in {source}: {e}")
            raise ValueError(f"Invalid JSON format: {e}") from e
        except Exception as e:
            logger.error(f"Failed to load JSON file: {e}")
            raise

    def _load_array_safe(self, file) -> Iterator[Client]:
        """Safely load from JSON array using orjson."""
        try:
            data = orjson.loads(file.read())
        except orjson.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON array: {e}")
            raise

        if not isinstance(data, list):
            raise ValueError("JSON must be an array of objects")

        if len(data) > self.MAX_CHUNK_SIZE * 10:
            logger.warning(f"Large array detected: {len(data)} items")

        logger.info(f"Found {len(data)} clients in JSON array")

        valid_count = 0
        for item in data:
            client = self._dict_to_client(item)
            if client:
                valid_count += 1
                yield client

        logger.debug(f"Successfully parsed {valid_count}/{len(data)} clients")

    def _load_lines_safe(self, file) -> Iterator[Client]:
        """Safely load from JSON lines format using orjson."""
        chunk: List[dict] = []
        line_count = 0
        error_count = 0

        for line_num, line in enumerate(file, 1):
            line = line.strip()
            if not line:
                continue

            if len(line) > self.MAX_RECORD_SIZE:
                logger.warning(f"Line {line_num} exceeds max size, skipping")
                error_count += 1
                continue

            try:
                if isinstance(line, bytes):
                    item = orjson.loads(line)
                else:
                    item = orjson.loads(line.encode("utf-8"))

                if not isinstance(item, dict):
                    logger.warning(
                        f"Line {line_num} is not a JSON object, skipping"
                    )
                    error_count += 1
                    continue

                chunk.append(item)
                line_count += 1

                if len(chunk) >= self.chunk_size:
                    yield from self._process_chunk_safe(chunk)
                    chunk = []

            except orjson.JSONDecodeError as e:
                logger.warning(f"Failed to parse line {line_num}: {e}")
                error_count += 1
                continue
            except (UnicodeError, ValueError) as e:
                logger.warning(f"Encoding error on line {line_num}: {e}")
                error_count += 1
                continue

        if chunk:
            yield from self._process_chunk_safe(chunk)

        if error_count > 0:
            logger.warning(
                f"Processed {line_count} lines with {error_count} errors"
            )

    def _process_chunk_safe(self, chunk: List[dict]) -> Iterator[Client]:
        """Process a chunk of JSON objects with size validation."""
        for item in chunk:
            try:
                client = self._dict_to_client(item)
                if client:
                    yield client
            except Exception as e:
                logger.warning(f"Failed to process record: {e}")
                continue

    def load_stream(
        self, source: Path, chunk_size: int = 1000
    ) -> Iterator[List[Client]]:
        """Load JSON data in chunks with validation."""
        if chunk_size > self.MAX_CHUNK_SIZE:
            logger.warning(
                "Chunk size {chunk_size} exceeds maximum, "
                f"using {self.MAX_CHUNK_SIZE}"
            )
            chunk_size = self.MAX_CHUNK_SIZE

        self.chunk_size = chunk_size
        clients = list(self.load(source))

        for i in range(0, len(clients), chunk_size):
            yield clients[i: i + chunk_size]

    def _dict_to_client(self, data: dict) -> Optional[Client]:
        """
        Convert JSON dict to Client entity with security checks.

        Handles:
        - Missing/null ID -> skip client
        - Age as float -> convert to int
        - Gender string -> enum mapping
        - Net worth with comma/scientific notation
        - Prevents injection attacks
        """
        try:
            if not isinstance(data, dict):
                logger.debug("Skipping non-dict record")
                return None

            client_id = self._parse_uuid(data.get("id"))
            if not client_id:
                logger.debug("Skipping client without valid ID")
                return None

            age = self._parse_age(data.get("age"))

            gender = self._parse_gender(data.get("gender"))

            net_worth = self._parse_net_worth(data.get("net_worth"))

            if age is None or net_worth is None:
                logger.debug(
                    f"Skipping client {client_id} - missing required data"
                )
                return None

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
        """Parse UUID from various formats with validation."""
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()
            if value.lower() in ("null", "none", ""):
                return None

        try:
            str_value = str(value).strip()
            if len(str_value) != 36 or str_value.count("-") != 4:
                return None

            return UUID(str_value)
        except (ValueError, AttributeError, TypeError):
            return None

    def _parse_age(self, value: Any) -> Optional[int]:
        """Parse age with validation and bounds checking."""
        if value is None:
            return None

        try:
            if isinstance(value, (int, float)):
                age_float = float(value)
            elif isinstance(value, str):
                value = value.strip()
                if value.lower() in ("null", "none", ""):
                    return None
                age_float = float(value)
            else:
                return None

            if not age_float.is_integer():
                return None

            age = int(age_float)

            if not (0 <= age <= 150):
                logger.debug(f"Age out of valid range: {age}")
                return None

            return age

        except (ValueError, TypeError):
            return None

    def _parse_gender(self, value: Any) -> Gender:
        """Parse gender string to enum with sanitization."""
        if value is None:
            return Gender.UNKNOWN

        try:
            if isinstance(value, str):
                str_value = value.strip()
                if len(str_value) > 50:
                    return Gender.UNKNOWN
            else:
                str_value = str(value).strip()
        except (ValueError, TypeError):
            return Gender.UNKNOWN

        gender_map = {
            "Мужчина": Gender.MALE,
            "Женщина": Gender.FEMALE,
            "Другой": Gender.OTHER,
        }

        return gender_map.get(str_value, Gender.UNKNOWN)

    def _parse_net_worth(self, value: Any) -> Optional[float]:
        """Parse net worth with validation and bounds checking."""
        if value is None:
            return None

        try:
            if isinstance(value, (int, float)):
                net_worth = float(value)
            elif isinstance(value, str):
                str_value = value.strip()
                if str_value.lower() in ("null", "none", ""):
                    return None

                str_value = str_value.replace(" ", "")

                if "," in str_value and "." not in str_value:
                    str_value = str_value.replace(",", ".")

                if "e" in str_value.lower():
                    str_value = str_value.lower()

                net_worth = float(str_value)
            else:
                return None

            if net_worth < 0:
                logger.debug(f"Negative net worth: {net_worth}")
                return None

            if net_worth > 1e12:
                logger.debug(
                    f"Net worth exceeds reasonable limit: {net_worth}"
                )
                return None

            return net_worth

        except (ValueError, TypeError):
            return None
