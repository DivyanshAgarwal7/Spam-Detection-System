"""Provenance flow across reload/predict (issue #1007, part 2).

Points the process-wide serving state at lightweight fakes (mirroring
test_reload_model) so the version/checksum plumbing can be exercised without the
real ML artifacts: /model-info tracks reloads, and a prediction carries the
version and short checksum of the model set that served it.
"""

from   itertools                import count
import os
from   pathlib                  import Path
import sys

import pytest

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"

os.environ.setdefault("MODEL_PATH", str(BASE_DIR / "linear_svm_model.pkl"))
os.environ.setdefault("VECTORIZER_PATH", str(BACKEND_DIR / "tfidf_vectorizer.pkl"))
os.environ.setdefault("LABEL_ENCODER_PATH", str(BASE_DIR / "label_encoder.pkl"))
os.environ.setdefault("URL_MODEL_PATH", str(BACKEND_DIR / "url_detector.pkl"))
os.environ.setdefault("URL_VECTORIZER_PATH", str(BACKEND_DIR / "url_vectorizer.pkl"))

sys.path.insert(0, str(BACKEND_DIR))

from   conftest                 import TEST_INTERNAL_SECRET # noqa: E402
import serving_state # noqa: E402

VALID_SECRET = {"X-Internal-Secret": TEST_INTERNAL_SECRET}


class _FakeModel:
    def __init__(self, token):
        self.token = token

    def predict(self, _vectorized):
        return [f"label-{self.token}"]


class _FakeVectorizer:
    def __init__(self, token):
        self.token = token

    def transform(self, texts):
        return list(texts)


class _FakeLabelEncoder:
    def __init__(self, token):
        self.token = token

    def inverse_transform(self, predictions):
        # The model already emits the final label; echo it back unchanged.
        return list(predictions)

    @property
    def classes_(self):
        return ["ham", f"label-{self.token}"]


class _FakeXAI:
    def __init__(self, token):
        self.token = token


class _FakeMetadata:
    """Stand-in ModelMetadata exposing the surface /model-info and /predict use."""

    def __init__(self, token):
        self.token = token
        self.short_checksum = f"cksum{token:012d}"

    @property
    def checksums(self):
        return {
            "model": f"model-{self.token}",
            "vectorizer": f"vec-{self.token}",
            "label_encoder": f"le-{self.token}",
        }

    def to_dict(self):
        return {"short_checksum": self.short_checksum, "checksums": self.checksums}


def _family(token):
    return {
        "model": _FakeModel(token),
        "vectorizer": _FakeVectorizer(token),
        "label_encoder": _FakeLabelEncoder(token),
        "xai_service": _FakeXAI(token),
        "metadata": _FakeMetadata(token),
    }


def _make_loader():
    tokens = count(2)  # initial install is token 1; first reload -> token 2

    def loader():
        return _family(next(tokens))

    return loader


@pytest.fixture
def client():
    try:
        import api as api_module  # noqa: E402
    except Exception as exc:  # pragma: no cover - env without ML deps/models
        pytest.skip(f"api import unavailable: {exc}")
    api_module.app.config["TESTING"] = True
    with api_module.app.test_client() as c:
        yield c


@pytest.fixture
def fake_state():
    original = serving_state.STATE
    serving_state.init_state(loader=_make_loader(), **_family(1))
    yield serving_state.STATE
    serving_state.STATE = original


def test_model_info_version_increments_after_reload(client, fake_state):
    before = client.get("/model-info").get_json()
    assert before["version"] == 1
    assert before["checksums"] == _FakeMetadata(1).checksums

    reload_res = client.post("/reload-model", headers=VALID_SECRET)
    assert reload_res.get_json()["version"] == 2

    after = client.get("/model-info").get_json()
    assert after["version"] == 2
    assert after["checksums"] != before["checksums"]


def test_prediction_carries_current_model_version(client, fake_state):
    client.post("/reload-model", headers=VALID_SECRET)  # bump to v2

    res = client.post("/predict", json={"text": "hello there"}, headers=VALID_SECRET)
    assert res.status_code == 200

    body = res.get_json()
    assert body["model_version"] == 2
    assert body["model_checksum"] == f"cksum{2:012d}"
