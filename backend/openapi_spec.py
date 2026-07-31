"""Hand-authored OpenAPI 3.0 document for the Flask ML API.

``build_spec()`` returns a plain ``dict`` describing the service's HTTP
contract: ``info``, ``servers``, the ``X-Internal-Secret`` security scheme,
and ``paths``/``components`` for the API's routes. It is served verbatim at
``GET /openapi.json`` and rendered by the Swagger UI at ``GET /docs``.

Response shapes stay hand-written: the ``/predict`` response has a rich,
evolving shape (``confidence``, ``domain_analysis``, ``url_risk``,
``explanation``, ``severity``, ...) that a generator would not capture
faithfully. Request bodies and query parameters, however, are generated from
the same :mod:`validation` schema registry that enforces them at runtime
(issue #1024), so the documented request contract cannot drift from what the
service actually accepts. To keep the hand-authored parts honest,
``test_openapi_coverage`` asserts every non-static registered rule is
documented here.

>>> spec = build_spec()
>>> spec["openapi"]
'3.0.3'
>>> "/predict" in spec["paths"]
True
>>> body = spec["paths"]["/predict"]["post"]["requestBody"]
>>> body["content"]["application/json"]["schema"]["required"]
['text']
"""

from __future__ import annotations


__all__ = ["build_spec"]

OPENAPI_VERSION = "3.0.3"
API_VERSION = "1.0.0"

# All routes except the handful of unauthenticated probes require the shared
# secret the trusted Node/Express backend attaches to every request. The
# document sets this scheme globally (see build_spec) and public operations
# opt out with an empty ``security: []``.
_SECURITY_SCHEME_NAME = "InternalSecret"
_SECURITY_SCHEME = {
    "type": "apiKey",
    "in": "header",
    "name": "X-Internal-Secret",
    "description": (
        "Shared service-to-service secret. The Flask ML API rejects any "
        "non-public request whose X-Internal-Secret header does not match "
        "the configured INTERNAL_SECRET with 403."
    ),
}

# Reusable inline reference to a JSON error envelope.
_ERROR = {"$ref": "#/components/schemas/Error"}


def build_spec():
    """Return the full OpenAPI 3.0 document for the Flask ML API as a dict.

    The result is JSON-serialisable and stable across calls (no runtime state
    is read), so it can be cached or diffed by consumers.
    """
    paths = {}
    paths.update(_core_paths())
    paths.update(_extended_paths())

    # Overwrite the request bodies/parameters of any documented path that has a
    # registered validation schema, so the served contract is generated from
    # the exact definitions used to enforce requests (single source of truth).
    _apply_registered_schemas(paths)

    schemas = {}
    schemas.update(_core_schemas())
    schemas.update(_extended_schemas())

    return {
        "openapi": OPENAPI_VERSION,
        "info": {
            "title": "Spam Detection System - Flask ML API",
            "version": API_VERSION,
            "description": (
                "Machine-learning inference service for the Spam Detection "
                "System. Classifies messages and URLs as spam / ham / "
                "smishing / offensive, analyses email headers, and exposes "
                "feedback, insights and inbox-scanning endpoints. All routes "
                "except liveness/readiness probes require the "
                "X-Internal-Secret header set by the Node/Express gateway."
            ),
        },
        "servers": [
            {"url": "http://127.0.0.1:5000", "description": "Local development"},
        ],
        "security": [{_SECURITY_SCHEME_NAME: []}],
        "paths": paths,
        "components": {
            "securitySchemes": {_SECURITY_SCHEME_NAME: _SECURITY_SCHEME},
            "schemas": schemas,
        },
    }


# ============================================================================
# CORE ROUTES (PR 1/2): /predict, /feedback, /feedback/stats, /spam-insights,
# /importance, /analyze-email-header, /health
# ============================================================================


def _core_paths():
    return {
        "/health": {
            "get": {
                "summary": "Legacy health probe (alias)",
                "operationId": "getHealth",
                "tags": ["System"],
                "security": [],
                "responses": {
                    "200": _json_response(
                        "Service is up.",
                        {"$ref": "#/components/schemas/HealthStatus"},
                    )
                },
            }
        },
        "/health/live": {
            "get": {
                "summary": "Liveness probe",
                "operationId": "getHealthLive",
                "tags": ["System"],
                "security": [],
                "responses": {
                    "200": _json_response(
                        "Process is up. Always 200 while the server runs, "
                        "independent of downstream dependencies.",
                        {"$ref": "#/components/schemas/HealthStatus"},
                    )
                },
            }
        },
        "/health/ready": {
            "get": {
                "summary": "Readiness probe",
                "operationId": "getHealthReady",
                "tags": ["System"],
                "security": [],
                "responses": {
                    "200": _json_response(
                        "Serving state, spam-words DB and rate-limit store are "
                        "all healthy.",
                        {"$ref": "#/components/schemas/ReadinessStatus"},
                    ),
                    "503": _error_response(
                        "A dependency is unavailable or the service is draining."
                    ),
                },
            }
        },
        "/predict": {
            "post": {
                "summary": "Classify a message or URL",
                "operationId": "predict",
                "tags": ["Prediction"],
                "description": (
                    "Responses are served from a content-addressed cache keyed "
                    "by the normalised input, the prediction options and the "
                    "live model version; a model hot-swap invalidates it. Send "
                    "`Cache-Control: no-cache` or `?fresh=1` to bypass the "
                    "lookup and force a fresh computation. The `X-Cache` "
                    "response header reports whether the body was served from "
                    "cache."
                ),
                "parameters": [
                    {
                        "name": "fresh",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "string", "enum": ["1"]},
                        "description": (
                            "Set to '1' to bypass the response cache and force "
                            "a fresh computation (equivalent to sending "
                            "Cache-Control: no-cache)."
                        ),
                    },
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/PredictRequest"}
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": (
                            "Prediction result with confidence, URL risk and "
                            "explanation details."
                        ),
                        "headers": {"X-Cache": _x_cache_header()},
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/PredictionResponse"
                                }
                            }
                        },
                    },
                    "400": _error_response("Missing/invalid text or body."),
                    "403": _error_response("Missing or invalid internal secret."),
                    "500": _error_response("Inference error."),
                },
            }
        },
        "/feedback": {
            "post": {
                "summary": "Submit a labelling correction",
                "operationId": "submitFeedback",
                "tags": ["Feedback"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/FeedbackRequest"}
                        }
                    },
                },
                "responses": {
                    "201": _json_response(
                        "Feedback recorded.",
                        {"$ref": "#/components/schemas/MessageResponse"},
                    ),
                    "400": _error_response(
                        "Empty text or correct_label outside the known labels."
                    ),
                    "503": _error_response("Feedback file lock could not be acquired."),
                },
            }
        },
        "/feedback/stats": {
            "get": {
                "summary": "Aggregate view of collected feedback",
                "operationId": "getFeedbackStats",
                "tags": ["Feedback"],
                "responses": {
                    "200": _json_response(
                        "Feedback totals, correction rate and recent submissions.",
                        {"$ref": "#/components/schemas/FeedbackStats"},
                    )
                },
            }
        },
        "/spam-insights": {
            "get": {
                "summary": "Top spam keywords, phrases and category indicators",
                "operationId": "getSpamInsights",
                "tags": ["Insights"],
                "parameters": [
                    {
                        "name": "limit",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "integer", "default": 10},
                        "description": "Max keywords/phrases to return.",
                    },
                    {
                        "name": "category",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "string"},
                        "description": "Filter source metrics to a threat category.",
                    },
                ],
                "responses": {
                    "200": _json_response(
                        "Insight metrics.",
                        {"$ref": "#/components/schemas/SpamInsights"},
                    )
                },
            }
        },
        "/importance": {
            "get": {
                "summary": "Global feature importance for the classifier",
                "operationId": "getFeatureImportance",
                "tags": ["Insights"],
                "responses": {
                    "200": _json_response(
                        "Top weighted features.",
                        {"$ref": "#/components/schemas/FeatureImportance"},
                    ),
                    "500": _error_response("Failed to compute importance."),
                },
            }
        },
        "/analyze-email-header": {
            "post": {
                "summary": "SPF/DKIM/DMARC analysis of raw email headers",
                "operationId": "analyzeEmailHeader",
                "tags": ["Email"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/EmailHeaderRequest"
                            }
                        },
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "file": {
                                        "type": "string",
                                        "format": "binary",
                                        "description": "An .eml file to analyse.",
                                    }
                                },
                            }
                        },
                    },
                },
                "responses": {
                    "200": _json_response(
                        "Header trust analysis.",
                        {"$ref": "#/components/schemas/EmailHeaderResponse"},
                    ),
                    "400": _error_response("No email headers provided."),
                },
            }
        },
    }


def _core_schemas():
    return {
        "Error": {
            "type": "object",
            "properties": {
                "error": {"type": "string"},
                "request_id": {"type": "string"},
            },
            "required": ["error"],
        },
        "MessageResponse": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
        },
        "HealthStatus": {
            "type": "object",
            "properties": {"status": {"type": "string", "example": "ok"}},
        },
        "ReadinessStatus": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "example": "ready"},
                "checks": {
                    "type": "object",
                    "description": "Per-dependency health map.",
                    "additionalProperties": {"type": "boolean"},
                },
            },
        },
        "PredictRequest": {
            "type": "object",
            "required": ["text"],
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Message body or URL to classify.",
                },
                "type": {
                    "type": "string",
                    "enum": ["message", "url"],
                    "default": "message",
                    "description": (
                        "Route to the URL classifier when set to 'url'; "
                        "otherwise the text classifier is used."
                    ),
                },
            },
        },
        "UrlRisk": {
            "type": "object",
            "description": "Thin top-level summary of domain_analysis.",
            "properties": {
                "is_url_present": {"type": "boolean"},
                "score": {"type": "number"},
                "level": {
                    "type": "string",
                    "enum": ["SAFE", "WARNING", "BLOCK"],
                },
            },
        },
        "PredictionResponse": {
            "type": "object",
            "description": (
                "Standardised prediction envelope. `result` and `prediction` "
                "always carry the same label; optional blocks (translated_text, "
                "domain_analysis, url_risk, explanation, severity) appear only "
                "when relevant."
            ),
            "properties": {
                "input": {"type": "string"},
                "result": {"type": "string", "example": "spam"},
                "prediction": {"type": "string", "example": "spam"},
                "confidence": {
                    "type": "number",
                    "description": "confidence_score / 100, rounded to 4 dp.",
                },
                "confidence_score": {
                    "type": "number",
                    "description": "Percentage confidence (0-100).",
                },
                "decision_score": {
                    "type": "number",
                    "nullable": True,
                    "description": "Absolute model decision-function margin.",
                },
                "confidence_level": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                },
                "detected_language": {"type": "string", "example": "en"},
                "translated": {"type": "boolean"},
                "translated_text": {"type": "string"},
                "domain_analysis": {
                    "type": "object",
                    "description": (
                        "Full per-domain risk breakdown from domain_checker."
                    ),
                    "additionalProperties": True,
                },
                "url_risk": {"$ref": "#/components/schemas/UrlRisk"},
                "explanation": {
                    "type": "object",
                    "description": "Explainable-AI reasons, matched keywords, patterns.",
                    "additionalProperties": True,
                },
                "severity": {
                    "description": "Computed spam severity summary.",
                    "additionalProperties": True,
                },
                "model_version": {
                    "type": "integer",
                    "description": (
                        "Version of the model set that produced this prediction "
                        "(issue #1007); increments on each /reload-model."
                    ),
                },
                "model_checksum": {
                    "type": "string",
                    "description": "Short SHA-256 of the model that produced this prediction.",
                },
            },
            "required": [
                "input",
                "result",
                "prediction",
                "confidence",
                "confidence_score",
                "confidence_level",
                "detected_language",
                "translated",
            ],
        },
        "FeedbackRequest": {
            "type": "object",
            "required": ["text", "correct_label"],
            "properties": {
                "text": {"type": "string"},
                "predicted_label": {
                    "type": "string",
                    "description": "Label the model originally produced.",
                },
                "correct_label": {
                    "type": "string",
                    "description": (
                        "Corrected label; must be one of the model's known "
                        "classes (e.g. ham, spam, smishing)."
                    ),
                },
            },
        },
        "FeedbackStats": {
            "type": "object",
            "properties": {
                "total": {"type": "integer"},
                "corrections": {"type": "integer"},
                "correction_rate": {"type": "number"},
                "by_predicted_label": {
                    "type": "object",
                    "additionalProperties": True,
                },
                "recent": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text_preview": {"type": "string"},
                            "predicted_label": {"type": "string"},
                            "correct_label": {"type": "string"},
                            "submitted_at": {"type": "string"},
                        },
                    },
                },
            },
        },
        "SpamInsights": {
            "type": "object",
            "properties": {
                "top_keywords": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "keyword": {"type": "string"},
                            "count": {"type": "integer"},
                        },
                    },
                },
                "trending_phrases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "phrase": {"type": "string"},
                            "count": {"type": "integer"},
                        },
                    },
                },
                "recent_suspicious_terms": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "category_indicators": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "FeatureImportance": {
            "type": "object",
            "properties": {
                "top_features": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "feature": {"type": "string"},
                            "importance": {"type": "number"},
                        },
                    },
                },
                "model_version": {
                    "type": "integer",
                    "description": "Version of the model these importances belong to (issue #1007).",
                },
                "model_checksum": {
                    "type": "string",
                    "description": "Short SHA-256 of that model.",
                },
            },
        },
        "EmailHeaderRequest": {
            "type": "object",
            "properties": {
                "headers": {
                    "type": "string",
                    "description": "Raw email headers as a single string.",
                }
            },
        },
        "EmailHeaderResponse": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "trust_level": {"type": "string"},
                "risk_score": {"type": "integer"},
                "findings": {"type": "array", "items": {"type": "string"}},
                "status": {"type": "string"},
                "analysis": {"type": "object", "additionalProperties": True},
            },
        },
    }


# ============================================================================
# EXTENDED ROUTES (PR 2/2): remaining registered rules so the drift-guard
# coverage test passes -- gmail/outlook/imap, bulk-predict, analytics,
# wordcloud, roles, /openapi.json and /docs.
# ============================================================================


def _extended_paths():
    return {
        "/": {
            "get": {
                "summary": "Root banner",
                "operationId": "getRoot",
                "tags": ["System"],
                "security": [],
                "responses": {
                    "200": {
                        "description": "Plain-text banner.",
                        "content": {"text/plain": {"schema": {"type": "string"}}},
                    }
                },
            }
        },
        "/api/roles": {
            "get": {
                "summary": "Available roles and permissions",
                "operationId": "getRoles",
                "tags": ["System"],
                "security": [],
                "responses": {
                    "200": _json_response(
                        "Role/permission matrix.",
                        {"type": "object", "additionalProperties": True},
                    )
                },
            }
        },
        "/api/rate-limit-status": {
            "get": {
                "summary": "Configured rate-limit windows",
                "operationId": "getRateLimitStatus",
                "tags": ["System"],
                "security": [],
                "responses": {
                    "200": _json_response(
                        "Rate-limit configuration.",
                        {"type": "object", "additionalProperties": True},
                    )
                },
            }
        },
        "/audit": {
            "get": {
                "summary": "Query the tamper-evident audit trail (admin only)",
                "operationId": "getAuditRecords",
                "tags": ["System"],
                "description": (
                    "Returns persisted audit records, newest first. Requires "
                    "the internal secret plus an admin caller identified by the "
                    "X-User-Username and X-User-Role headers the trusted backend "
                    "forwards. Supports exact-match filters, an inclusive "
                    "ISO-8601 time window and limit/offset pagination."
                ),
                "parameters": [
                    _query_param("actor", "Filter by the acting username."),
                    _query_param("action", "Filter by audited action name."),
                    _query_param("resource", "Filter by resource type."),
                    _query_param(
                        "since",
                        "Inclusive lower bound on the record timestamp "
                        "(ISO-8601 UTC).",
                    ),
                    _query_param(
                        "until",
                        "Inclusive upper bound on the record timestamp "
                        "(ISO-8601 UTC).",
                    ),
                    _query_param(
                        "limit",
                        "Maximum records to return (clamped to 1000).",
                        schema={"type": "integer", "default": 100},
                    ),
                    _query_param(
                        "offset",
                        "Number of records to skip for pagination.",
                        schema={"type": "integer", "default": 0},
                    ),
                ],
                "responses": {
                    "200": _json_response(
                        "Matching audit records plus chain-integrity status.",
                        {"$ref": "#/components/schemas/AuditQueryResponse"},
                    ),
                    "401": _error_response("Missing X-User-Username header."),
                    "403": _error_response(
                        "Caller is not admin or lacks the internal secret."
                    ),
        "/cache-stats": {
            "get": {
                "summary": "/predict response cache statistics",
                "operationId": "getCacheStats",
                "tags": ["System"],
                "security": [],
                "responses": {
                    "200": _json_response(
                        "Aggregate hit/miss/size counters for the /predict "
                        "response cache (never any cached content).",
                        {"$ref": "#/components/schemas/CacheStats"},
                    )
                },
            }
        },
        "/api/wordcloud": {
            "get": {
                "summary": "Spam word frequencies for the word cloud",
                "operationId": "getWordcloud",
                "tags": ["Insights"],
                "responses": {
                    "200": _json_response(
                        "Word/count pairs from the database or a sample fallback.",
                        {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean"},
                                "source": {"type": "string"},
                                "data": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "word": {"type": "string"},
                                            "count": {"type": "integer"},
                                        },
                                    },
                                },
                            },
                        },
                    )
                },
            }
        },
        "/api/word-of-the-day": {
            "get": {
                "summary": "Spam word of the day with metadata",
                "operationId": "getWordOfTheDay",
                "tags": ["Insights"],
                "responses": {
                    "200": _json_response(
                        "Word plus definition, context and safety tips.",
                        {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean"},
                                "data": {
                                    "type": "object",
                                    "properties": {
                                        "word": {"type": "string"},
                                        "count": {"type": "integer", "nullable": True},
                                        "definition": {"type": "string"},
                                        "context": {"type": "string"},
                                        "tips": {"type": "string"},
                                    },
                                },
                            },
                        },
                    )
                },
            }
        },
        "/gmail/auth-url": {
            "get": {
                "summary": "Gmail OAuth consent URL",
                "operationId": "getGmailAuthUrl",
                "tags": ["Gmail"],
                "parameters": [_redirect_uri_param()],
                "responses": {
                    "200": _json_response(
                        "Consent page URL.",
                        {"$ref": "#/components/schemas/AuthUrlResponse"},
                    )
                },
            }
        },
        "/gmail/callback": {
            "get": {
                "summary": "Exchange a Gmail authorization code for tokens",
                "operationId": "gmailCallback",
                "tags": ["Gmail"],
                "parameters": [
                    _query_param("code", "OAuth authorization code.", required=True),
                    _redirect_uri_param(),
                ],
                "responses": {
                    "200": _json_response(
                        "Gmail connected.",
                        {"$ref": "#/components/schemas/MessageResponse"},
                    ),
                    "400": _error_response("Authorization code missing."),
                    "401": _error_response("Missing X-User-Username header."),
                    "500": _error_response("Token exchange failed."),
                },
            }
        },
        "/gmail/emails": {
            "get": {
                "summary": "Fetch the latest Gmail messages",
                "operationId": "getGmailEmails",
                "tags": ["Gmail"],
                "responses": {
                    "200": _json_response(
                        "Fetched emails.",
                        {"$ref": "#/components/schemas/EmailListResponse"},
                    ),
                    "401": _error_response("Gmail account not connected."),
                    "500": _error_response("Fetch failed."),
                },
            }
        },
        "/outlook/auth-url": {
            "get": {
                "summary": "Outlook OAuth consent URL",
                "operationId": "getOutlookAuthUrl",
                "tags": ["Outlook"],
                "parameters": [_redirect_uri_param()],
                "responses": {
                    "200": _json_response(
                        "Consent page URL.",
                        {"$ref": "#/components/schemas/AuthUrlResponse"},
                    )
                },
            }
        },
        "/outlook/callback": {
            "get": {
                "summary": "Exchange an Outlook authorization code for tokens",
                "operationId": "outlookCallback",
                "tags": ["Outlook"],
                "parameters": [
                    _query_param("code", "OAuth authorization code.", required=True),
                    _redirect_uri_param(),
                ],
                "responses": {
                    "200": _json_response(
                        "Outlook connected.",
                        {"$ref": "#/components/schemas/MessageResponse"},
                    ),
                    "400": _error_response("Authorization code missing."),
                    "401": _error_response("Missing X-User-Username header."),
                    "500": _error_response("Token exchange failed."),
                },
            }
        },
        "/outlook/emails": {
            "get": {
                "summary": "Fetch the latest Outlook messages",
                "operationId": "getOutlookEmails",
                "tags": ["Outlook"],
                "responses": {
                    "200": _json_response(
                        "Fetched emails.",
                        {"$ref": "#/components/schemas/EmailListResponse"},
                    ),
                    "401": _error_response("Outlook account not connected."),
                    "500": _error_response("Fetch failed."),
                },
            }
        },
        "/scan-emails": {
            "post": {
                "summary": "Fetch and classify a provider inbox batch",
                "operationId": "scanEmails",
                "tags": ["Email"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["provider"],
                                "properties": {
                                    "provider": {
                                        "type": "string",
                                        "enum": ["gmail", "outlook"],
                                    }
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": _json_response(
                        "Scan results.",
                        {"type": "object", "additionalProperties": True},
                    ),
                    "400": _error_response("Invalid provider."),
                    "401": _error_response("Provider account not connected."),
                    "500": _error_response("Scan execution failed."),
                },
            }
        },
        "/imap/connect": {
            "post": {
                "summary": "Connect an IMAP inbox for scheduled scanning",
                "operationId": "imapConnect",
                "tags": ["Email"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ImapConnectRequest"
                            }
                        }
                    },
                },
                "responses": {
                    "200": _json_response(
                        "Inbox connected and scheduled.",
                        {
                            "type": "object",
                            "properties": {
                                "message": {"type": "string"},
                                "scan_interval_minutes": {"type": "integer"},
                            },
                        },
                    ),
                    "400": _error_response(
                        "Missing fields, bad interval or no consent."
                    ),
                    "401": _error_response("IMAP authentication failed."),
                    "502": _error_response("Could not reach the IMAP server."),
                },
            }
        },
        "/bulk-predict": {
            "post": {
                "summary": "Batch-classify a CSV/TXT upload",
                "operationId": "bulkPredict",
                "tags": ["Prediction"],
                "requestBody": _file_upload_body(),
                "responses": {
                    "200": _json_response(
                        "Batch results with spam statistics.",
                        {"$ref": "#/components/schemas/BulkPredictResponse"},
                    ),
                    "400": _error_response("No/invalid file."),
                    "413": _error_response("File exceeds the 2MB limit."),
                },
            }
        },
        "/bulk-predict/export": {
            "post": {
                "summary": "Batch-classify and download a CSV report",
                "operationId": "bulkPredictExport",
                "tags": ["Prediction"],
                "requestBody": _file_upload_body(),
                "responses": {
                    "200": {
                        "description": "CSV report download.",
                        "content": {
                            "text/csv": {
                                "schema": {"type": "string", "format": "binary"}
                            }
                        },
                    },
                    "400": _error_response("No/invalid file."),
                    "413": _error_response("File exceeds the 2MB limit."),
                    "500": _error_response("Report generation failed."),
                },
            }
        },
        "/analytics/summary": {
            "get": {
                "summary": "Scan totals and threat percentages",
                "operationId": "getAnalyticsSummary",
                "tags": ["Analytics"],
                "responses": {
                    "200": _json_response(
                        "Aggregate scan counts.",
                        {
                            "type": "object",
                            "properties": {
                                "totalScanned": {"type": "integer"},
                                "threatCount": {"type": "integer"},
                                "threatPercentage": {"type": "number"},
                                "cleanPercentage": {"type": "number"},
                            },
                        },
                    )
                },
            }
        },
        "/analytics/trends": {
            "get": {
                "summary": "Daily scan counts by predicted label",
                "operationId": "getAnalyticsTrends",
                "tags": ["Analytics"],
                "responses": {
                    "200": {
                        "description": "Per-day, per-label counts.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "date": {"type": "string"},
                                            "label": {"type": "string"},
                                            "count": {"type": "integer"},
                                        },
                                    },
                                }
                            }
                        },
                    }
                },
            }
        },
        "/analytics/breakdown": {
            "get": {
                "summary": "Scan counts by input type",
                "operationId": "getAnalyticsBreakdown",
                "tags": ["Analytics"],
                "responses": {
                    "200": {
                        "description": "Per-type counts.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "type": {"type": "string"},
                                            "count": {"type": "integer"},
                                        },
                                    },
                                }
                            }
                        },
                    }
                },
            }
        },
        "/reports/export-pdf": {
            "get": {
                "summary": "PDF report export (not yet implemented)",
                "operationId": "exportReportPdf",
                "tags": ["Analytics"],
                "responses": {
                    "501": _error_response("Coming soon."),
                },
            }
        },
        "/openapi.json": {
            "get": {
                "summary": "This OpenAPI 3.0 document",
                "operationId": "getOpenapiSpec",
                "tags": ["System"],
                "security": [],
                "responses": {
                    "200": _json_response(
                        "The OpenAPI specification.",
                        {"type": "object", "additionalProperties": True},
                    )
                },
            }
        },
        "/docs": {
            "get": {
                "summary": "Swagger UI",
                "operationId": "getDocs",
                "tags": ["System"],
                "security": [],
                "responses": {
                    "200": {
                        "description": "Interactive Swagger UI HTML page.",
                        "content": {"text/html": {"schema": {"type": "string"}}},
                    }
                },
            }
        },
        "/model-info": {
            "get": {
                "summary": "Provenance for the currently served model",
                "operationId": "getModelInfo",
                "tags": ["System"],
                "security": [],
                "responses": {
                    "200": _json_response(
                        "Live model version, per-artifact checksums and the "
                        "optional model-card metadata.",
                        {"$ref": "#/components/schemas/ModelInfo"},
                    )
                },
            }
        },
    }


def _extended_schemas():
    return {
        "CacheStats": {
            "type": "object",
            "description": "Aggregate counters for the /predict response cache.",
            "properties": {
                "enabled": {"type": "boolean"},
                "hits": {"type": "integer"},
                "misses": {"type": "integer"},
                "size": {"type": "integer"},
                "max_size": {"type": "integer"},
                "ttl_seconds": {"type": "number"},
                "evictions": {"type": "integer"},
                "hit_rate": {
                    "type": "number",
                    "description": "hits / (hits + misses), rounded to 4 dp.",
        "ArtifactInfo": {
            "type": "object",
            "description": "Content fingerprint of one model artifact.",
            "properties": {
                "path": {"type": "string"},
                "sha256": {"type": "string"},
                "size_bytes": {"type": "integer"},
                "mtime": {"type": "number"},
            },
        },
        "ModelInfo": {
            "type": "object",
            "description": (
                "Provenance of the served model set (issue #1007). `version` "
                "increments on each /reload-model; `checksums` maps each "
                "artifact role to its SHA-256; `metadata` carries per-artifact "
                "fingerprints plus the optional model-card fields, and is null "
                "when no provenance is available."
            ),
            "properties": {
                "version": {"type": "integer"},
                "checksums": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string"},
                        "vectorizer": {"type": "string"},
                        "label_encoder": {"type": "string"},
                    },
                },
                "metadata": {
                    "type": "object",
                    "nullable": True,
                    "properties": {
                        "model": {"$ref": "#/components/schemas/ArtifactInfo"},
                        "vectorizer": {"$ref": "#/components/schemas/ArtifactInfo"},
                        "label_encoder": {"$ref": "#/components/schemas/ArtifactInfo"},
                        "short_checksum": {"type": "string"},
                        "trained_at": {"type": "string", "nullable": True},
                        "metrics": {
                            "type": "object",
                            "nullable": True,
                            "additionalProperties": True,
                        },
                        "labels": {
                            "type": "array",
                            "nullable": True,
                            "items": {"type": "string"},
                        },
                    },
                },
            },
        },
        "AuditRecord": {
            "type": "object",
            "description": (
                "One persisted audit entry. `prev_hash`/`record_hash` form the "
                "SHA-256 chain that makes the trail tamper-evident."
            ),
            "properties": {
                "id": {"type": "integer"},
                "actor": {"type": "string"},
                "action": {"type": "string"},
                "resource": {"type": "string"},
                "request_id": {"type": "string"},
                "status": {"type": "integer"},
                "timestamp": {"type": "string", "description": "UTC ISO-8601."},
                "prev_hash": {"type": "string"},
                "record_hash": {"type": "string"},
            },
        },
        "AuditQueryResponse": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "count": {
                    "type": "integer",
                    "description": "Number of records in this page.",
                },
                "records": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/AuditRecord"},
                },
                "chain_intact": {
                    "type": "boolean",
                    "description": "Whether the stored hash chain still verifies.",
                },
            },
        },
        "AuthUrlResponse": {
            "type": "object",
            "properties": {"auth_url": {"type": "string"}},
        },
        "EmailListResponse": {
            "type": "object",
            "properties": {
                "emails": {
                    "type": "array",
                    "items": {"type": "object", "additionalProperties": True},
                }
            },
        },
        "ImapConnectRequest": {
            "type": "object",
            "required": ["host", "imap_username", "password", "consent"],
            "properties": {
                "host": {"type": "string"},
                "port": {"type": "integer", "default": 993},
                "imap_username": {"type": "string"},
                "password": {"type": "string", "format": "password"},
                "scan_interval_minutes": {
                    "type": "integer",
                    "description": "Must be one of the store's allowed intervals.",
                },
                "consent": {
                    "type": "boolean",
                    "description": "Explicit consent to store and scan the inbox.",
                },
            },
        },
        "BulkPredictResponse": {
            "type": "object",
            "properties": {
                "total_messages": {"type": "integer"},
                "spam_count": {"type": "integer"},
                "non_spam_count": {"type": "integer"},
                "spam_percentage": {"type": "number"},
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"},
                            "prediction": {"type": "string"},
                            "result": {"type": "string"},
                            "confidence": {"type": "number"},
                            "confidence_score": {"type": "number"},
                            "decision_score": {"type": "number"},
                            "confidence_level": {"type": "string"},
                        },
                    },
                },
            },
        },
    }


# ============================================================================
# Small builders shared by the path definitions.
# ============================================================================


def _json_response(description, schema):
    return {
        "description": description,
        "content": {"application/json": {"schema": schema}},
    }


def _error_response(description):
    return _json_response(description, _ERROR)


def _x_cache_header():
    return {
        "description": (
            "Whether the body was served from the /predict response cache: "
            "HIT (cached) or MISS (freshly computed)."
        ),
        "schema": {"type": "string", "enum": ["HIT", "MISS"]},
    }


def _query_param(name, description, required=False, schema=None):
    return {
        "name": name,
        "in": "query",
        "required": required,
        "schema": schema or {"type": "string"},
        "description": description,
    }


def _redirect_uri_param():
    return _query_param("redirect_uri", "OAuth redirect URI.")


def _file_upload_body():
    return {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["file"],
                    "properties": {
                        "file": {
                            "type": "string",
                            "format": "binary",
                            "description": "CSV (with a text/message column) or TXT file.",
                        }
                    },
                }
            }
        },
    }


# ============================================================================
# Generation from the validation schema registry (issue #1024, PR 2/2).
# ============================================================================


def _apply_registered_schemas(paths):
    """Replace request bodies/params on documented paths from the registry.

    Only the ``application/json`` request-body schema is overwritten, so a path
    that also accepts another media type (e.g. a multipart .eml upload) keeps
    it. Response definitions are left untouched.
    """
    for endpoint, schema in registered_schemas().items():
        operations = paths.get(endpoint)
        if not operations:
            continue
        for method, operation in operations.items():
            if not isinstance(operation, dict):
                continue
            if schema.body is not None and schema.body.fields:
                _set_json_request_body(operation, schema.body)
            if schema.query is not None and schema.query.fields:
                operation["parameters"] = _query_parameters(schema.query)


def _set_json_request_body(operation, body):
    request_body = operation.setdefault("requestBody", {"required": True})
    content = request_body.setdefault("content", {})
    json_entry = content.setdefault("application/json", {})
    json_entry["schema"] = _object_schema(body.fields)


def _object_schema(fields):
    properties = {}
    required = []
    for rule in fields:
        properties[rule.name] = _field_property(rule)
        if _is_required(rule):
            required.append(rule.name)
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _query_parameters(query):
    parameters = []
    for rule in query.fields:
        schema = {}
        if rule.type is not None:
            schema["type"] = rule.type
        if rule.enum is not None:
            schema["enum"] = list(rule.enum)
        if rule.default is not None:
            schema["default"] = rule.default
        parameters.append(
            {
                "name": rule.name,
                "in": "query",
                "required": bool(rule.enforced and rule.required),
                "schema": schema or {"type": "string"},
                "description": rule.description,
            }
        )
    return parameters


def _field_property(rule):
    prop = {}
    if rule.type is not None:
        prop["type"] = rule.type
    if rule.enum is not None:
        prop["enum"] = list(rule.enum)
    if rule.default is not None:
        prop["default"] = rule.default
    if rule.min_length is not None:
        prop["minLength"] = rule.min_length
    if rule.max_length is not None:
        prop["maxLength"] = rule.max_length
    if rule.description:
        prop["description"] = rule.description
    return prop


def _is_required(rule):
    """Whether a body field must be supplied for the request to be valid.

    A field is required when it is enforced and either declared required /
    non-empty, or constrained to an enum with no default (so a valid value must
    be sent explicitly).
    """
    if not rule.enforced:
        return False
    return bool(
        rule.required
        or rule.non_empty
        or (rule.enum is not None and rule.default is None)
    )
