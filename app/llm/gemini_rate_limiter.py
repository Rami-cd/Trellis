from __future__ import annotations

from collections import deque
import logging
import threading
import time

from app.settings.config import LLM_CONFIG

logger = logging.getLogger(__name__)

_GEMINI_CONFIG = LLM_CONFIG.get("gemini", {})
_RATE_LIMIT_CONFIG = _GEMINI_CONFIG.get("rate_limit", {})
REQUESTS_PER_WINDOW = _RATE_LIMIT_CONFIG.get("requests_per_window", 8)
WINDOW_SECONDS = _RATE_LIMIT_CONFIG.get("sleep_seconds", 60)
MIN_INTERVAL_SECONDS = (
    WINDOW_SECONDS / REQUESTS_PER_WINDOW
    if REQUESTS_PER_WINDOW > 0
    else 0
)

_request_lock = threading.Lock()
_request_timestamps: deque[float] = deque()
_last_request_timestamp = 0.0


def wait_for_gemini_rate_limit() -> None:
    global _last_request_timestamp

    with _request_lock:
        while True:
            now = time.monotonic()

            while _request_timestamps and now - _request_timestamps[0] >= WINDOW_SECONDS:
                _request_timestamps.popleft()

            wait_for_window = 0.0
            if REQUESTS_PER_WINDOW > 0 and len(_request_timestamps) >= REQUESTS_PER_WINDOW:
                wait_for_window = WINDOW_SECONDS - (now - _request_timestamps[0])

            wait_for_interval = 0.0
            if MIN_INTERVAL_SECONDS > 0 and _last_request_timestamp > 0:
                wait_for_interval = MIN_INTERVAL_SECONDS - (now - _last_request_timestamp)

            wait_seconds = max(wait_for_window, wait_for_interval, 0.0)
            if wait_seconds <= 0:
                admitted_at = time.monotonic()
                _request_timestamps.append(admitted_at)
                _last_request_timestamp = admitted_at
                return

            logger.info(
                "Gemini limiter delaying next request by %.1fs to stay within %d requests per %ds.",
                wait_seconds,
                REQUESTS_PER_WINDOW,
                WINDOW_SECONDS,
            )
            time.sleep(wait_seconds)
