"""Thread-safe holder for the ML objects the request handlers serve.

``api.py`` loads the initial ``model`` / ``vectorizer`` / ``label_encoder`` /
``xai_service`` at startup and installs them here; the ``/reload-model``
endpoint (``routes/reload.py``) calls :meth:`ServingState.reload` to atomically
hot-swap them after ``retrain.py`` overwrites the ``.pkl`` files. Both modules
reference this one instance, so a reload refreshes the *exact* objects
``/predict`` and ``/importance`` read -- and because the state lives in a
neutral module, neither ``api.py`` nor the reload route has to import the other
(no circular import).

The swap is guarded by a lock and readers take a coherent :class:`ServingSnapshot`
under that same lock, so a concurrent reload can never expose a half-updated set
(e.g. a new model paired with the old vectorizer).

Each snapshot also carries the :class:`~model_registry.ModelMetadata` describing
the artifacts currently loaded, refreshed on every reload so ``/model-info`` and
the per-prediction provenance fields report the live model.

The URL classifier pair travels in the snapshot as well. It is a separate model
from the text classifier, but it used to live in module globals that a reload
never touched, which meant a hot swap updated some prediction paths and not
others.

>>> state = ServingState(
...     model="m1", vectorizer="v1", label_encoder="l1", xai_service="x1",
...     metadata="meta1",
...     loader=lambda: {"model": "m2", "vectorizer": "v2",
...                     "label_encoder": "l2", "xai_service": "x2",
...                     "metadata": "meta2"},
... )
>>> state.snapshot().version
1
>>> state.snapshot().metadata
'meta1'
>>> state.reload().version
2
>>> state.snapshot().model
'm2'
>>> state.snapshot().metadata
'meta2'
"""

from __future__ import annotations

from   dataclasses              import dataclass
import threading
from   typing                   import Any, Callable

__all__ = ["ServingSnapshot", "ServingState", "STATE", "init_state"]


@dataclass(frozen=True, slots=True)
class ServingSnapshot:
    """An internally consistent view of the serving objects at one version."""

    model: Any
    vectorizer: Any
    label_encoder: Any
    xai_service: Any
    version: int
    # Provenance for the loaded artifacts (model_registry.ModelMetadata). Defaults
    # to None so callers/tests that build a snapshot without provenance still work.
    metadata: Any = None
    # The URL classifier pair. Optional for the same reason as ``metadata``:
    # lightweight fakes in the test suite construct snapshots without them.
    url_model: Any = None
    url_vectorizer: Any = None


# A loader returns the freshly loaded objects (from disk) as a mapping with the
# keys "model", "vectorizer", "label_encoder", "xai_service" and, optionally,
# "metadata" (the recomputed model_registry.ModelMetadata for the fresh set).
Loader = Callable[[], dict]


class ServingState:
    """Concurrency-safe container that supports atomic, versioned hot-swaps."""

    def __init__(
        self,
        *,
        model: Any,
        vectorizer: Any,
        label_encoder: Any,
        xai_service: Any,
        loader: Loader,
        metadata: Any = None,
        url_model: Any = None,
        url_vectorizer: Any = None,
    ) -> None:
        self._lock = threading.RLock()
        self._model = model
        self._vectorizer = vectorizer
        self._label_encoder = label_encoder
        self._xai_service = xai_service
        self._loader = loader
        self._metadata = metadata
        self._url_model = url_model
        self._url_vectorizer = url_vectorizer
        self._version = 1

    def snapshot(self) -> ServingSnapshot:
        with self._lock:
            return ServingSnapshot(
                self._model,
                self._vectorizer,
                self._label_encoder,
                self._xai_service,
                self._version,
                self._metadata,
                self._url_model,
                self._url_vectorizer,
            )

    def reload(self) -> ServingSnapshot:
        """Load a fresh object set from disk and atomically swap it in.

        Loading happens *outside* the lock because disk I/O and unpickling are
        slow and must not block in-flight predictions; only the reference swap
        holds the lock. If loading raises, the live objects are left untouched
        and the exception propagates to the caller.
        """
        fresh = self._loader()
        with self._lock:
            self._model = fresh["model"]
            self._vectorizer = fresh["vectorizer"]
            self._label_encoder = fresh["label_encoder"]
            self._xai_service = fresh["xai_service"]
            # Loaders may omit "metadata" and the URL pair (e.g. lightweight test
            # fakes); fall back to None rather than requiring every loader to
            # supply them.
            self._metadata = fresh.get("metadata")
            self._url_model = fresh.get("url_model")
            self._url_vectorizer = fresh.get("url_vectorizer")
            self._version += 1
            return ServingSnapshot(
                self._model,
                self._vectorizer,
                self._label_encoder,
                self._xai_service,
                self._version,
                self._metadata,
                self._url_model,
                self._url_vectorizer,
            )

    @property
    def version(self) -> int:
        with self._lock:
            return self._version


# Populated by api.py at startup via init_state(). Handlers reference
# ``serving_state.STATE`` at call time (not by value at import), so re-pointing
# this global -- as the test suite does with fakes -- is picked up everywhere.
STATE: ServingState | None = None


def init_state(
    *,
    model: Any,
    vectorizer: Any,
    label_encoder: Any,
    xai_service: Any,
    loader: Loader,
    metadata: Any = None,
    url_model: Any = None,
    url_vectorizer: Any = None,
) -> ServingState:
    """Install the process-wide serving state and return it."""
    global STATE
    STATE = ServingState(
        model=model,
        vectorizer=vectorizer,
        label_encoder=label_encoder,
        xai_service=xai_service,
        loader=loader,
        metadata=metadata,
        url_model=url_model,
        url_vectorizer=url_vectorizer,
    )
    return STATE
