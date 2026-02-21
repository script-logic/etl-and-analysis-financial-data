from datetime import datetime, timedelta, timezone
import sys


def get_cutoff_date(days: int) -> datetime:
    if sys.version_info >= (3, 12):
        result = datetime.now(timezone.utc) - timedelta(days=days)
    else:
        result = datetime.utcnow() - timedelta(days=days)

    return result
