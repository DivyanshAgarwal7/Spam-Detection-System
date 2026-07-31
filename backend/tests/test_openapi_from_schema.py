"""The OpenAPI request contract is generated from the validation registry.

Issue #1024, PR 2/2: request bodies and query parameters served at
``/openapi.json`` must come from the same :mod:`validation` schemas that
enforce requests, so the two cannot drift. These checks compare the generated
spec back against the registry and pin the concrete shapes that matter.
"""

from   pathlib                  import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from   openapi_spec             import build_spec # noqa: E402
import validation # noqa: E402


def _json_body_schema(operation):
    return operation["requestBody"]["content"]["application/json"]["schema"]


def _expected_required(fields):
    return [
        rule.name
        for rule in fields
        if rule.enforced
        and (
            rule.required
            or rule.non_empty
            or (rule.enum is not None and rule.default is None)
        )
    ]


def test_body_schemas_match_registry():
    spec_paths = build_spec()["paths"]
    for endpoint, schema in validation.registered_schemas().items():
        if schema.body is None or not schema.body.fields:
            continue
        operations = spec_paths[endpoint]
        method = schema.methods[0].lower()
        body_schema = _json_body_schema(operations[method])

        assert set(body_schema["properties"]) == {
            rule.name for rule in schema.body.fields
        }
        assert body_schema.get("required", []) == _expected_required(schema.body.fields)


def test_query_params_match_registry():
    spec_paths = build_spec()["paths"]
    for endpoint, schema in validation.registered_schemas().items():
        if schema.query is None or not schema.query.fields:
            continue
        method = schema.methods[0].lower()
        params = spec_paths[endpoint][method]["parameters"]
        assert {p["name"] for p in params} == {
            rule.name for rule in schema.query.fields
        }


def test_predict_request_body_details():
    op = build_spec()["paths"]["/predict"]["post"]
    schema = _json_body_schema(op)
    assert schema["required"] == ["text"]
    # 'type' is documented (enum + default) but not required, matching the
    # classifier's lenient handling of the field.
    assert schema["properties"]["type"]["enum"] == ["message", "url"]
    assert schema["properties"]["type"]["default"] == "message"
    assert "maxLength" in schema["properties"]["text"]


def test_feedback_correct_label_enum_comes_from_registry():
    op = build_spec()["paths"]["/feedback"]["post"]
    schema = _json_body_schema(op)
    assert set(schema["required"]) == {"text", "correct_label"}

    registry = validation.registered_schemas()["/feedback"]
    correct_label = next(
        rule for rule in registry.body.fields if rule.name == "correct_label"
    )
    assert schema["properties"]["correct_label"]["enum"] == list(correct_label.enum)


def test_spam_insights_limit_param_generated():
    op = build_spec()["paths"]["/spam-insights"]["get"]
    limit = next(p for p in op["parameters"] if p["name"] == "limit")
    assert limit["schema"]["type"] == "integer"
    assert limit["schema"]["default"] == 10
    assert limit["required"] is False


def test_analyze_email_header_keeps_multipart_upload():
    # Generating the JSON body from the schema must not drop the .eml upload
    # media type the endpoint also accepts.
    op = build_spec()["paths"]["/analyze-email-header"]["post"]
    content = op["requestBody"]["content"]
    assert "application/json" in content
    assert "multipart/form-data" in content


def test_all_refs_still_resolve():
    spec = build_spec()
    defined = set(spec["components"]["schemas"])

    def _refs(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "$ref" and isinstance(value, str):
                    yield value
                else:
                    yield from _refs(value)
        elif isinstance(node, list):
            for item in node:
                yield from _refs(item)

    for ref in _refs(spec["paths"]):
        assert ref.split("/")[-1] in defined, ref
