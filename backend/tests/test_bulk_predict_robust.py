"""Robustness + streaming coverage for the bulk-prediction endpoints (#1021).

Covers the resilient buffered path (valid rows returned alongside a typed
``skipped`` list, row-cap enforcement, version stamping) and the opt-in NDJSON
streaming path (per-row lines plus meta/summary framing). A fake serving
snapshot is installed so the tests depend only on the endpoint logic, not on
the real ``.pkl`` artifacts.
"""

import io
import json
from   pathlib                  import Path
import sys

import numpy as np
import pytest

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import api as api_module # noqa: E402
import serving_state # noqa: E402

# A vectorizer that refuses to transform any row carrying this token, so a
# single un-transformable row inside an otherwise-valid batch can be simulated.
_POISON = "POISON"


class _FakeVectorizer:
    def transform(self, messages):
        if any(_POISON in m for m in messages):
            raise ValueError("cannot transform poisoned row")
        return np.array([[float(len(m))] for m in messages])


class _FakeModel:
    def predict(self, X):
        return np.array([1 if row[0] > 10 else 0 for row in X])

    def decision_function(self, X):
        return np.array([float(row[0]) for row in X])


class _FakeLabelEncoder:
    def inverse_transform(self, predictions):
        return np.array(["spam" if p == 1 else "ham" for p in predictions])


@pytest.fixture
def client():
    api_module.app.config["TESTING"] = True
    with api_module.app.test_client() as c:
        yield c


@pytest.fixture
def fake_state():
    return serving_state.init_state(
        model=_FakeModel(),
        vectorizer=_FakeVectorizer(),
        label_encoder=_FakeLabelEncoder(),
        xai_service=None,
        loader=lambda: {},
        metadata=None,
    )


def _upload(client, csv_text, path="/bulk-predict", **kwargs):
    data = {"file": (io.BytesIO(csv_text.encode("utf-8")), "test.csv")}
    return client.post(path, data=data, content_type="multipart/form-data", **kwargs)


class TestRowIsolation:
    def test_mixed_valid_and_invalid_rows(self, client, fake_state, monkeypatch):
        monkeypatch.setenv("BULK_PREDICT_MAX_ROW_LEN", "50")
        csv_text = (
            "text\n"
            "this is a long spam message\n"  # valid -> spam
            "hi\n"  # valid -> ham
            "\n"  # empty -> skipped
            + ("x" * 80 + "\n")  # over-length -> skipped
            + f"{_POISON} row\n"  # un-transformable -> skipped
        )
        res = _upload(client, csv_text)
        assert res.status_code == 200
        body = res.get_json()

        messages = {r["message"] for r in body["results"]}
        assert "this is a long spam message" in messages
        assert "hi" in messages

        reasons = {s["reason"] for s in body["skipped"]}
        assert "BULK_ROW_EMPTY" in reasons
        assert "BULK_ROW_TOO_LONG" in reasons
        assert "BULK_ROW_UNPROCESSABLE" in reasons
        assert body["skipped_count"] == len(body["skipped"]) == 3

    def test_single_bad_row_does_not_500(self, client, fake_state):
        csv_text = "text\ngood message here now\n" + f"{_POISON}\n"
        res = _upload(client, csv_text)
        assert res.status_code == 200
        body = res.get_json()
        assert len(body["results"]) == 1
        assert body["skipped_count"] == 1


class TestRowCap:
    def test_row_cap_returns_typed_error(self, client, fake_state, monkeypatch):
        monkeypatch.setenv("BULK_PREDICT_MAX_ROWS", "2")
        csv_text = "text\na message\nb message\nc message\n"
        res = _upload(client, csv_text)
        assert res.status_code == 413
        body = res.get_json()
        assert body["error_detail"]["code"] == "BULK_TOO_MANY_ROWS"

    def test_under_cap_is_accepted(self, client, fake_state, monkeypatch):
        monkeypatch.setenv("BULK_PREDICT_MAX_ROWS", "10")
        csv_text = "text\na message\nb message\n"
        res = _upload(client, csv_text)
        assert res.status_code == 200


class TestVersionStamping:
    def test_json_response_carries_model_version(self, client, fake_state):
        res = _upload(client, "text\nsome message content\n")
        assert res.status_code == 200
        assert res.get_json()["model_version"] == fake_state.version

    def test_export_carries_model_version(self, client, fake_state):
        res = _upload(
            client, "text\nsome message content\n", path="/bulk-predict/export"
        )
        assert res.status_code == 200
        assert res.headers["X-Model-Version"] == str(fake_state.version)
        body = res.data.decode("utf-8")
        assert "model_version" in body.splitlines()[0]


def _parse_ndjson(raw):
    return [
        json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()
    ]


class TestNdjsonStreaming:
    def test_stream_query_param_shape(self, client, fake_state, monkeypatch):
        monkeypatch.setenv("BULK_PREDICT_MAX_ROW_LEN", "50")
        csv_text = "text\n" "this is a long spam message\n" "hi\n" + f"{_POISON} row\n"
        res = _upload(client, csv_text, path="/bulk-predict?stream=ndjson")
        assert res.status_code == 200
        assert res.headers["Content-Type"].startswith("application/x-ndjson")
        assert res.headers["X-Model-Version"] == str(fake_state.version)

        records = _parse_ndjson(res.data)
        assert records[0]["type"] == "meta"
        assert records[0]["model_version"] == fake_state.version

        results = [r for r in records if r["type"] == "result"]
        skipped = [r for r in records if r["type"] == "skipped"]
        summary = records[-1]
        assert {r["message"] for r in results} == {
            "this is a long spam message",
            "hi",
        }
        assert any(s["reason"] == "BULK_ROW_UNPROCESSABLE" for s in skipped)
        assert summary["type"] == "summary"
        assert summary["total_messages"] == len(results)
        assert summary["skipped_count"] == len(skipped)

    def test_stream_via_accept_header(self, client, fake_state):
        res = _upload(
            client,
            "text\nsome message content\n",
            headers={"Accept": "application/x-ndjson"},
        )
        assert res.status_code == 200
        assert res.headers["Content-Type"].startswith("application/x-ndjson")
        records = _parse_ndjson(res.data)
        assert records[0]["type"] == "meta"

    def test_row_cap_enforced_before_stream(self, client, fake_state, monkeypatch):
        monkeypatch.setenv("BULK_PREDICT_MAX_ROWS", "1")
        csv_text = "text\na message\nb message\n"
        res = _upload(client, csv_text, path="/bulk-predict?stream=ndjson")
        assert res.status_code == 413
        assert res.get_json()["error_detail"]["code"] == "BULK_TOO_MANY_ROWS"

    def test_non_streaming_is_default(self, client, fake_state):
        res = _upload(client, "text\nsome message content\n")
        assert res.headers["Content-Type"].startswith("application/json")
        assert "results" in res.get_json()
