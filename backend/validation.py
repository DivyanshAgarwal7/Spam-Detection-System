"""Centralized, declarative request-schema validation (issue #1024).

Handlers in ``api.py`` historically re-implemented the same input checks inline
-- "is the body a JSON object?", "is ``text`` a non-empty string?", "is
``correct_label`` a known class?" -- each returning its own error envelope. That
scattered the request contract across the handlers and made it drift from the
served OpenAPI document.

This module holds that contract in one place. Each endpoint declares a
:class:`RequestSchema` (body fields and/or query parameters) in
:func:`default_request_schemas`, and the :func:`validate_schema` decorator
enforces it before the handler runs. A single request can fail several
constraints; the validator collects **every** offending field rather than
stopping at the first, and reports them together through
:func:`errors.error_response` (with the full list under ``violations``).

The same declarations are the single source of truth the OpenAPI generator
reads (issue #1024, PR 2/2), so enforcement and documentation cannot drift.

Design notes:

* A field is validated in the order presence -> type -> enum -> length, and the
  first failing constraint for that field wins (you cannot length-check a value
  that is not a string). Different fields are independent, so all of their
  first failures accumulate.
* A rule may override the ``(code, message)`` used for a given constraint so a
  migrated endpoint reproduces its exact legacy envelope (e.g. ``/predict``
  keeps ``NO_TEXT_PROVIDED`` / ``INVALID_TEXT_TYPE`` / ``TEXT_TOO_LONG``).
* A schema may declare an ``aggregate_code`` so that any violation collapses to
  one legacy envelope (e.g. ``/feedback`` always answers ``INVALID_FEEDBACK`` /
  "Invalid feedback data"), while still listing the individual violations.

>>> _type_ok("string", "hi")
True
>>> _type_ok("integer", True)   # JSON booleans are not integers
False
>>> _type_ok("number", 3)
True
"""

from __future__ import annotations

from   dataclasses              import dataclass
from   enum                     import StrEnum
from   functools                import wraps
import json

from   errors                   import ErrorCode, error_response
from   flask                    import g, request

__all__ = [
    "Constraint",
    "Violation",
    "FieldRule",
    "BodySpec",
    "QuerySpec",
    "RequestSchema",
    "configure",
    "register_schema",
    "get_schema",
    "registered_schemas",
    "default_request_schemas",
    "validate_schema",
    "DEFAULT_MAX_MESSAGE_LENGTH",
    "DEFAULT_FEEDBACK_LABELS",
]

# Fallbacks used only when the registry is built without the running app's real
# configuration (e.g. the OpenAPI document is generated in a pure-spec test that
# never imports api.py). At runtime api.configure() overrides these with the
# settings-derived limit and the model's actual label classes.
DEFAULT_MAX_MESSAGE_LENGTH = 5000
DEFAULT_FEEDBACK_LABELS = ("ham", "spam", "smishing")


class Constraint(StrEnum):
    """The kinds of check a :class:`FieldRule` can fail, in evaluation order."""

    PRESENCE = "presence"
    TYPE = "type"
    ENUM = "enum"
    MAX_LENGTH = "max_length"
    MIN_LENGTH = "min_length"


# Maps the schema type name (also emitted verbatim into OpenAPI) to the concrete
# check. bool is excluded from the numeric types because JSON distinguishes
# ``true``/``false`` from numbers even though Python's ``bool`` subclasses ``int``.
def _type_ok(type_name, value):
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    return True


@dataclass(slots=True)
class Violation:
    """One failed constraint for one field."""

    field: str
    constraint: Constraint
    code: ErrorCode
    message: str

    def to_dict(self):
        return {
            "field": self.field,
            "constraint": self.constraint.value,
            "code": self.code.value,
            "message": self.message,
        }


@dataclass(slots=True)
class FieldRule:
    """A declared constraint set for a single body field or query parameter.

    ``type`` doubles as the OpenAPI type name. ``coerce_str`` mirrors the legacy
    ``str(value or "")`` handling some endpoints applied before checking a field
    (so a numeric value is stringified rather than rejected). ``enforced=False``
    documents a field in OpenAPI without rejecting requests -- used where the
    legacy handler accepted values outside the documented set.

    ``codes`` maps a :class:`Constraint` to a ``(ErrorCode, message_template)``
    pair; the template is ``str.format``-ed with ``name``, ``type``, ``value``,
    ``length``, ``min_length``, ``max_length`` and ``enum``.
    """

    name: str
    type: str | None = None
    required: bool = False
    enum: tuple | None = None
    min_length: int | None = None
    max_length: int | None = None
    non_empty: bool = False
    coerce_str: bool = False
    enforced: bool = True
    default: object = None
    description: str = ""
    codes: dict | None = None


@dataclass(slots=True)
class BodySpec:
    """Declares the JSON body contract.

    ``mode="strict_object"`` rejects a non-object / malformed body up front with
    ``object_error_code`` (``/predict``); ``mode="lenient"`` treats a missing or
    non-object body as an empty object and lets the field rules speak
    (``/feedback``).
    """

    fields: tuple = ()
    mode: str = "lenient"
    object_error_code: ErrorCode = ErrorCode.INVALID_JSON_BODY


@dataclass(slots=True)
class QuerySpec:
    """Declares the query-parameter contract.

    Integer/number parameters are coerced leniently: an uncoercible value falls
    back to the rule's ``default`` (matching Flask's ``request.args.get(...,
    type=int)``) rather than rejecting, so endpoints that previously tolerated
    junk query strings keep doing so.
    """

    fields: tuple = ()


@dataclass(slots=True)
class RequestSchema:
    """The full request contract for one endpoint, keyed by its URL path."""

    endpoint: str
    methods: tuple = ("POST",)
    summary: str = ""
    body: BodySpec | None = None
    query: QuerySpec | None = None
    aggregate_code: ErrorCode | None = None
    aggregate_message: str | None = None
    status: int = 400


_REGISTRY: dict = {}


def register_schema(schema):
    """Register (or replace) the schema for ``schema.endpoint``."""
    _REGISTRY[schema.endpoint] = schema


def get_schema(endpoint):
    """Return the registered schema for ``endpoint`` or ``None``."""
    return _REGISTRY.get(endpoint)


def registered_schemas():
    """Return a shallow copy of the endpoint -> schema registry."""
    return dict(_REGISTRY)


def configure(
    *,
    max_message_length=DEFAULT_MAX_MESSAGE_LENGTH,
    feedback_labels=DEFAULT_FEEDBACK_LABELS,
):
    """Rebuild and register the default schemas with runtime configuration.

    Called at import with fallbacks, and again by ``api.py`` once the real
    message-length cap and model label classes are known, so enforcement uses
    the live configuration.
    """
    for schema in default_request_schemas(
        max_message_length=max_message_length,
        feedback_labels=feedback_labels,
    ).values():
        register_schema(schema)


def default_request_schemas(*, max_message_length, feedback_labels):
    """Return the endpoint -> :class:`RequestSchema` map for the core routes.

    This is the single source of truth for both request enforcement and the
    generated OpenAPI request bodies/parameters.
    """
    labels = tuple(feedback_labels)
    return {
        "/predict": RequestSchema(
            endpoint="/predict",
            methods=("POST",),
            summary="Classify a message or URL",
            body=BodySpec(
                mode="strict_object",
                fields=(
                    FieldRule(
                        name="text",
                        type="string",
                        non_empty=True,
                        max_length=max_message_length,
                        description="Message body or URL to classify.",
                        codes={
                            Constraint.PRESENCE: (
                                ErrorCode.NO_TEXT_PROVIDED,
                                "No text provided",
                            ),
                            Constraint.TYPE: (
                                ErrorCode.INVALID_TEXT_TYPE,
                                "'text' must be a string, got {type}",
                            ),
                            Constraint.MAX_LENGTH: (
                                ErrorCode.TEXT_TOO_LONG,
                                "'text' exceeds maximum length of "
                                "{max_length} characters (got {length})",
                            ),
                        },
                    ),
                    # Documented enum only: the classifier treats any non-'url'
                    # value as a message, so enforcing the enum would newly
                    # reject inputs the endpoint has always accepted.
                    FieldRule(
                        name="type",
                        type="string",
                        enum=("message", "url"),
                        default="message",
                        enforced=False,
                        description=(
                            "Route to the URL classifier when set to 'url'; "
                            "otherwise the text classifier is used."
                        ),
                    ),
                ),
            ),
        ),
        "/feedback": RequestSchema(
            endpoint="/feedback",
            methods=("POST",),
            summary="Submit a labelling correction",
            # The endpoint has always answered a single INVALID_FEEDBACK /
            # "Invalid feedback data" 400 for any bad field; keep that envelope
            # while still enumerating each problem under ``violations``.
            aggregate_code=ErrorCode.INVALID_FEEDBACK,
            aggregate_message="Invalid feedback data",
            body=BodySpec(
                mode="lenient",
                fields=(
                    FieldRule(
                        name="text",
                        type="string",
                        coerce_str=True,
                        non_empty=True,
                        description="Message the correction applies to.",
                    ),
                    FieldRule(
                        name="predicted_label",
                        type="string",
                        description="Label the model originally produced.",
                    ),
                    FieldRule(
                        name="correct_label",
                        type="string",
                        coerce_str=True,
                        enum=labels,
                        description=(
                            "Corrected label; must be one of the model's known "
                            "classes (e.g. ham, spam, smishing)."
                        ),
                    ),
                ),
            ),
        ),
        "/feedback/stats": RequestSchema(
            endpoint="/feedback/stats",
            methods=("GET",),
            summary="Aggregate view of collected feedback",
        ),
        "/importance": RequestSchema(
            endpoint="/importance",
            methods=("GET",),
            summary="Global feature importance for the classifier",
        ),
        "/spam-insights": RequestSchema(
            endpoint="/spam-insights",
            methods=("GET",),
            summary="Top spam keywords, phrases and category indicators",
            query=QuerySpec(
                fields=(
                    FieldRule(
                        name="limit",
                        type="integer",
                        default=10,
                        description="Max keywords/phrases to return.",
                    ),
                    FieldRule(
                        name="category",
                        type="string",
                        default=None,
                        description="Filter source metrics to a threat category.",
                    ),
                )
            ),
        ),
        # Registered for the single-source OpenAPI generator. The endpoint also
        # accepts a multipart .eml upload and derives its "no headers" error
        # from the file/JSON combination, which a pure body schema cannot
        # express, so its presence check stays in the handler.
        "/analyze-email-header": RequestSchema(
            endpoint="/analyze-email-header",
            methods=("POST",),
            summary="SPF/DKIM/DMARC analysis of raw email headers",
            body=BodySpec(
                mode="lenient",
                fields=(
                    FieldRule(
                        name="headers",
                        type="string",
                        enforced=False,
                        description="Raw email headers as a single string.",
                    ),
                ),
            ),
        ),
    }


def validate_schema(endpoint):
    """Enforce the registered schema for ``endpoint`` before the handler runs.

    The wrapped view still runs unchanged when no schema is registered, so the
    decorator is safe to apply broadly. On success the parsed body dict and the
    coerced query params are stashed on ``g`` (``g.schema_body`` /
    ``g.schema_query``) so the handler can consume already-validated values.
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            schema = get_schema(endpoint)
            if schema is None:
                return f(*args, **kwargs)

            body_data, body_error = _parse_body(schema)
            if body_error is not None:
                return body_error

            violations = []
            if schema.body is not None:
                _check_fields(schema.body.fields, body_data, violations)
            query_data = _validate_query(schema, violations)

            if violations:
                return _render_violations(schema, violations)

            g.schema_body = body_data
            g.schema_query = query_data
            return f(*args, **kwargs)

        return wrapper

    return decorator


def _parse_body(schema):
    """Return ``(body_dict, error_response_or_None)`` for the request body."""
    spec = schema.body
    if spec is None:
        return {}, None

    request_id = getattr(g, "request_id", "unknown")
    if spec.mode == "strict_object":
        data = request.get_json(silent=True)
        if data is None:
            raw_body = request.get_data(cache=True)
            if raw_body:
                # get_json(silent=True) returns None for both malformed JSON and
                # the valid literal ``null``; tell them apart so a well-formed
                # ``null`` is not reported as malformed.
                try:
                    json.loads(raw_body)
                except ValueError:
                    return None, error_response(
                        spec.object_error_code,
                        "Request body must be a valid JSON object",
                        schema.status,
                        request_id=request_id,
                    )
                return None, error_response(
                    spec.object_error_code,
                    "Request body must be a JSON object, got NoneType",
                    schema.status,
                    request_id=request_id,
                )
            return {}, None
        if not isinstance(data, dict):
            return None, error_response(
                spec.object_error_code,
                f"Request body must be a JSON object, got {type(data).__name__}",
                schema.status,
                request_id=request_id,
            )
        return data, None

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        data = {}
    return data, None


def _check_fields(fields, source, violations):
    for rule in fields:
        if not rule.enforced:
            continue
        present = rule.name in source
        value = source.get(rule.name)
        violation = _check_rule(rule, present, value)
        if violation is not None:
            violations.append(violation)


def _check_rule(rule, present, value):
    """Return the first :class:`Violation` for ``rule`` or ``None``."""
    if rule.coerce_str:
        value = "" if (not present or value is None) else str(value)
        present = True

    if rule.required and (not present or value is None):
        return _violation(rule, Constraint.PRESENCE, value)

    if rule.non_empty:
        is_blank = (
            not present
            or value is None
            or (isinstance(value, str) and not value.strip())
        )
        if is_blank:
            return _violation(rule, Constraint.PRESENCE, value)

    if not present or value is None:
        return None

    if rule.type is not None and not _type_ok(rule.type, value):
        return _violation(rule, Constraint.TYPE, value)

    if rule.enum is not None and value not in rule.enum:
        return _violation(rule, Constraint.ENUM, value)

    if isinstance(value, str):
        if rule.max_length is not None and len(value) > rule.max_length:
            return _violation(rule, Constraint.MAX_LENGTH, value)
        if rule.min_length is not None and len(value) < rule.min_length:
            return _violation(rule, Constraint.MIN_LENGTH, value)

    return None


def _validate_query(schema, violations):
    """Coerce and validate query params, appending any violations."""
    out = {}
    if schema.query is None:
        return out

    for rule in schema.query.fields:
        present = rule.name in request.args
        raw = request.args.get(rule.name)

        if not present:
            if rule.enforced and rule.required:
                violations.append(_violation(rule, Constraint.PRESENCE, None))
            out[rule.name] = rule.default
            continue

        coerced = raw
        if rule.type in ("integer", "number"):
            try:
                coerced = int(raw) if rule.type == "integer" else float(raw)
            except (TypeError, ValueError):
                # Mirror Flask's lenient ``type=`` coercion: fall back to the
                # default instead of rejecting a junk value.
                coerced = rule.default

        if rule.enforced and rule.enum is not None and coerced not in rule.enum:
            violations.append(_violation(rule, Constraint.ENUM, coerced))

        out[rule.name] = coerced

    return out


def _violation(rule, constraint, value):
    ctx = {
        "name": rule.name,
        "type": type(value).__name__,
        "value": value,
        "min_length": rule.min_length,
        "max_length": rule.max_length,
        "length": len(value) if isinstance(value, (str, list, dict)) else None,
        "enum": list(rule.enum) if rule.enum is not None else None,
    }
    override = (rule.codes or {}).get(constraint)
    if override is not None:
        code, template = override
        message = template.format(**ctx)
    else:
        code = ErrorCode.SCHEMA_VALIDATION_FAILED
        message = _default_message(rule, constraint, ctx)
    return Violation(rule.name, constraint, code, message)


def _default_message(rule, constraint, ctx):
    if constraint is Constraint.PRESENCE:
        return f"'{rule.name}' is required"
    if constraint is Constraint.TYPE:
        return f"'{rule.name}' must be of type {rule.type}, got {ctx['type']}"
    if constraint is Constraint.ENUM:
        return f"'{rule.name}' must be one of {ctx['enum']}"
    if constraint is Constraint.MAX_LENGTH:
        return f"'{rule.name}' must be at most {rule.max_length} characters"
    if constraint is Constraint.MIN_LENGTH:
        return f"'{rule.name}' must be at least {rule.min_length} characters"
    return f"'{rule.name}' failed validation"


def _render_violations(schema, violations):
    request_id = getattr(g, "request_id", "unknown")
    extra = {"violations": [v.to_dict() for v in violations]}

    if schema.aggregate_code is not None:
        return error_response(
            schema.aggregate_code,
            schema.aggregate_message or "Request failed validation",
            schema.status,
            request_id=request_id,
            extra=extra,
        )

    if len(violations) == 1:
        only = violations[0]
        return error_response(
            only.code,
            only.message,
            schema.status,
            request_id=request_id,
            extra=extra,
        )

    summary = "Request failed validation: " + "; ".join(
        f"{v.field}: {v.message}" for v in violations
    )
    return error_response(
        ErrorCode.SCHEMA_VALIDATION_FAILED,
        summary,
        schema.status,
        request_id=request_id,
        extra=extra,
    )


# Populate the registry at import with fallbacks so validation is active even
# before api.configure() supplies the live configuration.
configure()
