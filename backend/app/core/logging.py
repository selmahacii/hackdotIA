import logging
import re
from typing import Any

from app.config import settings

SENSITIVE_PATTERNS = [
    re.compile(r"(password[\"']?\s*[:=]\s*[\"']?)([^\"'\s,]+)", re.IGNORECASE),
    re.compile(r"(secret[\"']?\s*[:=]\s*[\"']?)([^\"'\s,]+)", re.IGNORECASE),
    re.compile(r"(api[-_]?key[\"']?\s*[:=]\s*[\"']?)([^\"'\s,]+)", re.IGNORECASE),
    re.compile(r"(bearer\s+)([a-zA-Z0-9\-_.]+\.[a-zA-Z0-9\-_.]+\.[a-zA-Z0-9\-_]+)", re.IGNORECASE),
    re.compile(r"(authorization[\"']?\s*[:=]\s*[\"']?)([^\"'\s,]+)", re.IGNORECASE),
]


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._sanitize(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._sanitize(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._sanitize(arg) for arg in record.args)
        return True

    @staticmethod
    def _sanitize(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        sanitized = value
        for pattern in SENSITIVE_PATTERNS:
            sanitized = pattern.sub(r"\1[REDACTED]", sanitized)
        return sanitized


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("smart_elderly")
    numeric_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveDataFilter())
        logger.addHandler(handler)

    return logger


logger = setup_logging()
