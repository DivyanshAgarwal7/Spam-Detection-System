"""Structured JSON logging for the Flask ML API (issue #1006, part 1).

The API historically emitted ad-hoc ``app.logger.warning(f"...")`` lines with
emoji prefixes and interpolated request context. Those are impossible to parse
reliably in a log pipeline. This module centralises logging on a single JSON
formatter so every line is a self-describing object that a pipeline can index
and correlate by ``request_id``.

Two pieces cooperate:

* :class:`JsonLogFormatter` renders each record as one JSON object with a fixed
  core schema (``ts``, ``level``, ``logger``, ``msg``, ``request_id``) plus any
  structured ``extra=`` fields passed at the call site.
* :class:`RequestIdFilter` stamps the active request's ``g.request_id`` onto
  every record so the id propagates without threading it through call sites. It
  is safe outside an application/request context, falling back to ``"-"``.

Call :func:`configure_logging` once at startup and obtain module loggers with
:func:`get_logger`.

>>> logger = get_logger("ml_api")
>>> isinstance(logger, logging.Logger)
True
"""

from   datetime                 import datetime, timezone
import json
import logging
import sys

__all__ = [
    "configure_logging",
    "get_logger",
    "JsonLogFormatter",
    "RequestIdFilter",
]

# Placeholder emitted when no request context is active (startup, background
# scheduler jobs) so ``request_id`` is always present in the schema.
_NO_REQUEST_ID = "-"

# LogRecord attributes that belong to the logging machinery rather than to
# caller-supplied context. Anything else found on a record is treated as a
# structured extra and emitted alongside the core fields. Derived from a probe
# record so it tracks the running interpreter's LogRecord shape.
_STANDARD_ATTRS = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys()
) | {"message", "asctime", "taskName"}


class JsonLogFormatter(logging.Formatter):
    """Render a log record as a single-line JSON object.

    Core fields are always present; ``extra=`` keyword fields passed at the
    call site are merged in at the top level, and an exception traceback (when
    present) is attached under ``exc_info``.

    >>> record = logging.LogRecord("ml_api", logging.INFO, __file__, 1,
    ...                            "hello", None, None)
    >>> data = json.loads(JsonLogFormatter().format(record))
    >>> data["level"], data["logger"], data["msg"]
    ('INFO', 'ml_api', 'hello')
    """

    def format(self, record):
        payload = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", _NO_REQUEST_ID),
        }
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_ATTRS and key != "request_id"
        }
        payload.update(extras)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # default=str keeps a stray non-serialisable extra from crashing the
        # log call; ensure_ascii=False keeps unicode readable in the sink.
        return json.dumps(payload, default=str, ensure_ascii=False)

    def formatTime(self, record, datefmt=None):
        # ISO 8601 in UTC so lines from different hosts/timezones sort and
        # correlate directly, regardless of the process's local timezone.
        return datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()


class RequestIdFilter(logging.Filter):
    """Inject the active request's ``g.request_id`` onto every record.

    Kept as a filter (not a formatter concern) so the id is available to every
    handler and so the lookup stays safe when there is no Flask application or
    request context, e.g. at import time or inside the background scheduler.
    """

    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = _current_request_id()
        return True


def configure_logging(level=logging.INFO, *, stream=None):
    """Install the JSON formatter + request-id filter on the root logger.

    Idempotent: repeated calls (e.g. a reimport, or a test that imports the app
    twice) are no-ops after the first, so log lines are never duplicated.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return logging.getLogger()

    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    # Replace any default/basicConfig handlers so lines aren't emitted twice
    # and every line goes through the JSON formatter.
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    _CONFIGURED = True
    return root


def get_logger(name):
    """Return a module logger; records flow through the configured root."""
    return logging.getLogger(name)


# Set once by configure_logging(); guards against double-configuration.
_CONFIGURED = False


def _current_request_id():
    # Import lazily and guard on has_request_context so this is safe to call
    # from records emitted outside any Flask context.
    try:
        from flask import g, has_request_context
    except Exception:
        return _NO_REQUEST_ID
    if not has_request_context():
        return _NO_REQUEST_ID
    return getattr(g, "request_id", _NO_REQUEST_ID)
