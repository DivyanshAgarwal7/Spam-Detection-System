"""Preparation contract recorded in, and read back from, model provenance (#1037).

Covers both ends of the sidecar: what ``retrain.py`` writes after a successful
save, and what ``model_registry`` reports for the artifacts being served.
"""

import json
from   types                    import SimpleNamespace

import model_registry
import retrain
from   text_preparation         import PREPARATION_VERSION


def _artifact(name):
    return model_registry.ArtifactInfo(
        path=name, sha256="ab" * 32, size_bytes=1, mtime=0.0
    )


def _metadata(**overrides):
    fields = {
        "model": _artifact("m.pkl"),
        "vectorizer": _artifact("v.pkl"),
        "label_encoder": _artifact("l.pkl"),
    }
    fields.update(overrides)
    return model_registry.ModelMetadata(**fields)


class TestPreparationMatching:
    def test_same_version_matches(self):
        assert _metadata(preparation_version="1").preparation_matches("1")

    def test_different_version_does_not_match(self):
        assert not _metadata(preparation_version="1").preparation_matches("2")

    def test_unrecorded_version_is_treated_as_compatible(self):
        # Artifacts predating the card make no claim; they must stay servable.
        assert _metadata().preparation_matches("2")

    def test_version_is_reported_in_the_payload(self):
        assert (
            _metadata(preparation_version="1").to_dict()["preparation_version"] == "1"
        )


class TestCardIsReadBack:
    def test_registry_surfaces_the_recorded_version(self, tmp_path):
        for name in ("m.pkl", "v.pkl", "l.pkl"):
            (tmp_path / name).write_bytes(b"x")
        (tmp_path / model_registry.MODEL_CARD_FILENAME).write_text(
            json.dumps({"preparation_version": "7"})
        )

        metadata = model_registry.build_metadata(
            model_path=str(tmp_path / "m.pkl"),
            vectorizer_path=str(tmp_path / "v.pkl"),
            label_encoder_path=str(tmp_path / "l.pkl"),
        )

        assert metadata.preparation_version == "7"


class TestCardEmission:
    def test_training_records_the_contract_in_force(self, tmp_path):
        result = SimpleNamespace(
            holdout=SimpleNamespace(accuracy=0.9375),
            label_encoder=SimpleNamespace(classes_=["ham", "spam"]),
            n_rows=120,
        )

        path = retrain.write_model_card(
            result, card_path=str(tmp_path / model_registry.MODEL_CARD_FILENAME)
        )
        card = json.loads(open(path, encoding="utf-8").read())

        assert card["preparation_version"] == PREPARATION_VERSION
        assert card["metrics"]["holdout_accuracy"] == 0.9375
        assert card["metrics"]["training_rows"] == 120
        assert card["labels"] == ["ham", "spam"]
        assert card["trained_at"]

    def test_card_is_readable_by_the_registry(self, tmp_path):
        result = SimpleNamespace(
            holdout=SimpleNamespace(accuracy=1.0),
            label_encoder=SimpleNamespace(classes_=["ham"]),
            n_rows=10,
        )
        for name in ("m.pkl", "v.pkl", "l.pkl"):
            (tmp_path / name).write_bytes(b"x")

        retrain.write_model_card(result, model_path=str(tmp_path / "m.pkl"))
        metadata = model_registry.build_metadata(
            model_path=str(tmp_path / "m.pkl"),
            vectorizer_path=str(tmp_path / "v.pkl"),
            label_encoder_path=str(tmp_path / "l.pkl"),
        )

        assert metadata.preparation_version == PREPARATION_VERSION
        assert metadata.preparation_matches(PREPARATION_VERSION)
