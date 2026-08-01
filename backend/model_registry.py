"""Model registry & provenance metadata for the Flask ML API (issue #1007).

The API serves a triple of artifacts -- the classifier ``model``, its
``vectorizer`` and the ``label_encoder`` -- that ``retrain.py`` overwrites and
``/reload-model`` hot-swaps. Until now nothing recorded *which* bytes were
loaded, so an operator could not tell one deployed model from another or prove
that a reload actually changed anything.

This module fingerprints those artifacts. :func:`build_metadata` reads each
``.pkl`` and captures its SHA-256, size and mtime, and -- when a
``model_card.json`` sits next to the model -- folds in the provenance fields
``retrain.py`` records there (``trained_at``, ``metrics``, ``labels`` and the
``preparation_version`` the artifacts were trained under). The immutable
:class:`ModelMetadata` it returns is stored alongside the serving objects in
``serving_state`` and surfaced at ``GET /model-info``; its
:attr:`ModelMetadata.short_checksum` tags predictions and reload audit logs.

>>> a = ArtifactInfo(path="m.pkl", sha256="aa" * 32, size_bytes=1, mtime=0.0)
>>> b = ArtifactInfo(path="v.pkl", sha256="bb" * 32, size_bytes=1, mtime=0.0)
>>> c = ArtifactInfo(path="l.pkl", sha256="cc" * 32, size_bytes=1, mtime=0.0)
>>> meta = ModelMetadata(model=a, vectorizer=b, label_encoder=c)
>>> meta.short_checksum
'aaaaaaaaaaaa'
>>> meta.checksums["vectorizer"] == "bb" * 32
True
"""

from __future__ import annotations

from   dataclasses              import dataclass
import hashlib
import json
from   pathlib                  import Path

__all__ = ["ArtifactInfo", "ModelMetadata", "build_metadata", "MODEL_CARD_FILENAME"]

# Sidecar looked for next to the model artifact; absence is not an error.
MODEL_CARD_FILENAME = "model_card.json"

# A 12-hex-char prefix is enough to tell deployed models apart in logs and
# prediction payloads without carrying the full 64-char digest everywhere.
SHORT_CHECKSUM_LENGTH = 12

# Hash artifacts incrementally so a large .pkl never has to be held in memory.
_HASH_CHUNK_SIZE = 1 << 20


@dataclass(frozen=True, slots=True)
class ArtifactInfo:
    """Content fingerprint of one on-disk model artifact.

    >>> info = ArtifactInfo(path="m.pkl", sha256="ab" * 32, size_bytes=10, mtime=1.5)
    >>> info.short_sha256
    'abababababab'
    """

    path: str
    sha256: str
    size_bytes: int
    mtime: float

    @property
    def short_sha256(self) -> str:
        return self.sha256[:SHORT_CHECKSUM_LENGTH]

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "mtime": self.mtime,
        }


@dataclass(frozen=True, slots=True)
class ModelMetadata:
    """Provenance snapshot of the served artifact triple plus optional card.

    The three :class:`ArtifactInfo` members are always present; the sidecar
    fields (``trained_at``, ``metrics``, ``labels``) are ``None`` when no
    ``model_card.json`` accompanies the model, and otherwise carry whatever that
    file supplied.
    """

    model: ArtifactInfo
    vectorizer: ArtifactInfo
    label_encoder: ArtifactInfo
    trained_at: str | None = None
    metrics: dict | None = None
    labels: list | None = None
    preparation_version: str | None = None

    def preparation_matches(self, serving_version: str) -> bool:
        """Whether these artifacts were trained under ``serving_version``.

        An unrecorded version (``None``) counts as a match: artifacts predating
        the model card carry no claim about their preparation, and refusing to
        serve them would break existing deployments over missing metadata rather
        than over a known conflict.
        """
        if self.preparation_version is None:
            return True
        return self.preparation_version == serving_version

    @property
    def short_checksum(self) -> str:
        """Abbreviated model hash used to tag predictions and reload audit logs."""
        return self.model.short_sha256

    @property
    def checksums(self) -> dict:
        """Full SHA-256 per artifact, keyed by role."""
        return {
            "model": self.model.sha256,
            "vectorizer": self.vectorizer.sha256,
            "label_encoder": self.label_encoder.sha256,
        }

    def to_dict(self) -> dict:
        return {
            "model": self.model.to_dict(),
            "vectorizer": self.vectorizer.to_dict(),
            "label_encoder": self.label_encoder.to_dict(),
            "short_checksum": self.short_checksum,
            "trained_at": self.trained_at,
            "metrics": self.metrics,
            "labels": self.labels,
            "preparation_version": self.preparation_version,
        }


def build_metadata(
    *,
    model_path: str,
    vectorizer_path: str,
    label_encoder_path: str,
    model_card_path: str | None = None,
) -> ModelMetadata:
    """Fingerprint the three artifacts and fold in the sidecar model card.

    ``model_card_path`` defaults to a ``model_card.json`` next to the model;
    when the card is absent or unreadable the provenance fields stay ``None``.
    The artifact files themselves must exist -- a missing ``.pkl`` is a
    misconfiguration and surfaces as the usual ``OSError``.
    """
    card_path = (
        Path(model_card_path)
        if model_card_path is not None
        else Path(model_path).parent / MODEL_CARD_FILENAME
    )
    card = _read_model_card(card_path)

    return ModelMetadata(
        model=_describe_artifact(model_path),
        vectorizer=_describe_artifact(vectorizer_path),
        label_encoder=_describe_artifact(label_encoder_path),
        trained_at=card.get("trained_at"),
        metrics=card.get("metrics"),
        labels=card.get("labels"),
        preparation_version=card.get("preparation_version"),
    )


def _describe_artifact(path: str) -> ArtifactInfo:
    p = Path(path)
    stat = p.stat()
    return ArtifactInfo(
        path=str(p),
        sha256=_sha256(p),
        size_bytes=stat.st_size,
        mtime=stat.st_mtime,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_model_card(path: Path) -> dict:
    """Return the sidecar card as a dict, or ``{}`` when it is absent/unreadable.

    A malformed or non-object card is treated as absent rather than fatal: model
    provenance is advisory metadata and must never stop the model from serving.
    """
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
