"""Behaviour of the centralized request-schema validator (issue #1024).

Drives the framework through a throwaway Flask app so it needs no ML models:
a valid payload passes, an invalid one is rejected with a typed envelope that
enumerates *every* offending field, and the presence / type / enum / length
constraints and lenient query coercion each behave as declared.
"""

from   pathlib                  import Path
import sys

from   flask                    import Flask, g, jsonify
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from   errors                   import ErrorCode # noqa: E402
import validation # noqa: E402
from   validation               import (BodySpec, Constraint, FieldRule,
                                        QuerySpec, RequestSchema,
                                        register_schema, validate_schema)

# A strict-object body schema exercising presence (with a custom code), type,
# enum, and min/max length in one place.
_THINGS = RequestSchema(
    endpoint="/things",
    methods=("POST",),
    body=BodySpec(
        mode="strict_object",
        fields=(
            FieldRule(
                name="name",
                type="string",
                required=True,
                min_length=2,
                max_length=5,
                codes={
                    Constraint.PRESENCE: (ErrorCode.BAD_REQUEST, "name required"),
                },
            ),
            FieldRule(name="kind", type="string", enum=("a", "b")),
            FieldRule(name="count", type="integer"),
        ),
    ),
)

# An aggregate schema: any violation collapses to one legacy envelope while the
# individual problems are still listed.
_AGG = RequestSchema(
    endpoint="/agg",
    methods=("POST",),
    aggregate_code=ErrorCode.INVALID_FEEDBACK,
    aggregate_message="Invalid feedback data",
    body=BodySpec(
        mode="lenient",
        fields=(
            FieldRule(name="text", type="string", coerce_str=True, non_empty=True),
            FieldRule(
                name="label", type="string", coerce_str=True, enum=("ham", "spam")
            ),
        ),
    ),
)

# Query params: lenient integer coercion plus an enum.
_QUERY = RequestSchema(
    endpoint="/q",
    methods=("GET",),
    query=QuerySpec(
        fields=(
            FieldRule(name="limit", type="integer", default=10),
            FieldRule(name="mode", type="string", enum=("x", "y")),
        )
    ),
)


@pytest.fixture
def client():
    for schema in (_THINGS, _AGG, _QUERY):
        register_schema(schema)

    app = Flask(__name__)

    @app.route("/things", methods=["POST"])
    @validate_schema("/things")
    def things():
        return jsonify({"ok": True, "body": g.schema_body})

    @app.route("/agg", methods=["POST"])
    @validate_schema("/agg")
    def agg():
        return jsonify({"ok": True})

    @app.route("/q", methods=["GET"])
    @validate_schema("/q")
    def q():
        return jsonify({"ok": True, "query": g.schema_query})

    with app.test_client() as c:
        yield c


def _detail(res):
    return res.get_json()["error_detail"]


def test_type_ok_pure():
    assert validation._type_ok("string", "hi") is True
    assert validation._type_ok("integer", 3) is True
    # JSON booleans must not satisfy integer/number.
    assert validation._type_ok("integer", True) is False
    assert validation._type_ok("number", True) is False
    assert validation._type_ok("array", [1]) is True


def test_valid_payload_passes(client):
    res = client.post("/things", json={"name": "abc", "kind": "a", "count": 3})
    assert res.status_code == 200
    assert res.get_json()["body"]["name"] == "abc"


def test_all_offending_fields_reported_at_once(client):
    res = client.post("/things", json={"name": "x", "kind": "z", "count": "nan"})
    assert res.status_code == 400
    body = res.get_json()
    # Multiple problems collapse to the aggregate code, but every field appears.
    assert _detail(body)["code"] == ErrorCode.SCHEMA_VALIDATION_FAILED.value
    offending = {v["field"]: v["constraint"] for v in body["violations"]}
    assert offending == {
        "name": Constraint.MIN_LENGTH.value,
        "kind": Constraint.ENUM.value,
        "count": Constraint.TYPE.value,
    }


def test_presence_uses_custom_code(client):
    res = client.post("/things", json={"kind": "a"})
    assert res.status_code == 400
    body = res.get_json()
    # A single violation surfaces its own (overridden) code and message.
    assert body["error"] == "name required"
    assert _detail(body)["code"] == ErrorCode.BAD_REQUEST.value
    assert len(body["violations"]) == 1
    assert body["violations"][0]["constraint"] == Constraint.PRESENCE.value


def test_type_violation(client):
    res = client.post("/things", json={"name": "abcd", "count": "3"})
    assert res.status_code == 400
    body = res.get_json()
    assert body["violations"][0]["field"] == "count"
    assert body["violations"][0]["constraint"] == Constraint.TYPE.value


def test_enum_violation(client):
    res = client.post("/things", json={"name": "abcd", "kind": "z"})
    assert res.status_code == 400
    body = res.get_json()
    assert _detail(body)["code"] == ErrorCode.SCHEMA_VALIDATION_FAILED.value
    assert body["violations"][0]["constraint"] == Constraint.ENUM.value


def test_max_length_violation(client):
    res = client.post("/things", json={"name": "toolong"})
    assert res.status_code == 400
    assert res.get_json()["violations"][0]["constraint"] == Constraint.MAX_LENGTH.value


def test_non_object_body_rejected(client):
    res = client.post("/things", data="[1, 2]", content_type="application/json")
    assert res.status_code == 400
    body = res.get_json()
    assert _detail(body)["code"] == ErrorCode.INVALID_JSON_BODY.value
    assert "JSON object" in body["error"]
    assert "valid JSON object" not in body["error"]


def test_malformed_json_body_rejected(client):
    res = client.post("/things", data="not json", content_type="application/json")
    assert res.status_code == 400
    body = res.get_json()
    assert _detail(body)["code"] == ErrorCode.INVALID_JSON_BODY.value
    assert "valid JSON object" in body["error"]


def test_aggregate_code_with_all_violations_listed(client):
    res = client.post("/agg", json={})
    assert res.status_code == 400
    body = res.get_json()
    assert body["error"] == "Invalid feedback data"
    assert _detail(body)["code"] == ErrorCode.INVALID_FEEDBACK.value
    fields = {v["field"] for v in body["violations"]}
    assert fields == {"text", "label"}


def test_aggregate_valid_payload_passes(client):
    res = client.post("/agg", json={"text": "hi", "label": "ham"})
    assert res.status_code == 200


def test_query_defaults_applied(client):
    res = client.get("/q")
    assert res.status_code == 200
    query = res.get_json()["query"]
    assert query["limit"] == 10
    assert query["mode"] is None


def test_query_integer_coerced(client):
    res = client.get("/q?limit=3")
    assert res.status_code == 200
    assert res.get_json()["query"]["limit"] == 3


def test_query_bad_integer_falls_back_leniently(client):
    # Junk integers mirror Flask's type= behaviour: fall back, do not reject.
    res = client.get("/q?limit=abc")
    assert res.status_code == 200
    assert res.get_json()["query"]["limit"] == 10


def test_query_enum_rejected(client):
    res = client.get("/q?mode=z")
    assert res.status_code == 400
    body = res.get_json()
    assert _detail(body)["code"] == ErrorCode.SCHEMA_VALIDATION_FAILED.value
    assert body["violations"][0]["constraint"] == Constraint.ENUM.value
