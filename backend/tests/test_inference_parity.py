"""Cross-path parity for the text-preparation contract (issue #1037).

Bulk scoring and mailbox scanning must hand the vectorizer the same canonical
string ``/predict`` does, otherwise the same message is classified differently
depending on how it arrived. These tests capture what actually reaches
``transform`` using recording doubles, so they assert the contract without
loading real model artifacts.
"""

from   types                    import SimpleNamespace

import numpy as np
import pytest

import bulk_predict
from   text_preparation         import prepare_text

# Subject/body pairs whose obfuscated and plain spellings must reduce alike.
OBFUSCATED = "F r e e\u200b \u0440rize"
PLAIN = "Free prize"


class RecordingVectorizer:
    """Captures the texts handed to ``transform`` and returns a dummy matrix."""

    def __init__(self):
        self.seen = []

    def transform(self, texts):
        self.seen = list(texts)
        return np.zeros((len(self.seen), 1))


class ConstantModel:
    def predict(self, vectors):
        return np.zeros(vectors.shape[0], dtype=int)

    def decision_function(self, vectors):
        return np.zeros((vectors.shape[0], 1))


class PassthroughEncoder:
    def inverse_transform(self, predictions):
        return ["ham"] * len(predictions)


@pytest.fixture
def snapshot():
    return SimpleNamespace(
        vectorizer=RecordingVectorizer(),
        model=ConstantModel(),
        label_encoder=PassthroughEncoder(),
        version=1,
    )


class TestBulkPrediction:
    def test_rows_are_scored_in_prepared_form(self, snapshot):
        bulk_predict._predict_batch([OBFUSCATED], snapshot)

        assert snapshot.vectorizer.seen == [prepare_text(OBFUSCATED)]

    def test_obfuscated_and_plain_rows_score_identically(self, snapshot):
        bulk_predict._predict_batch([OBFUSCATED, PLAIN], snapshot)

        seen = snapshot.vectorizer.seen
        assert seen[0] == seen[1]

    def test_returned_row_echoes_the_original_text(self, snapshot):
        results = bulk_predict._predict_batch([OBFUSCATED], snapshot)

        # The caller uploaded this row and must recognise it in the response,
        # even though a different string was scored.
        assert results[0]["message"] == OBFUSCATED


class TestMailboxScanning:
    def test_scanned_emails_are_prepared_before_scoring(self, snapshot, monkeypatch):
        from email_connectors import email_scanner

        monkeypatch.setattr(
            email_scanner,
            "current_app",
            SimpleNamespace(
                vectorizer=snapshot.vectorizer,
                model=snapshot.model,
                label_encoder=snapshot.label_encoder,
            ),
        )
        monkeypatch.setattr(email_scanner, "analyze_headers", None)

        email_scanner.scan_emails_with_model(
            [{"subject": "F r e e", "body": "\u0440rize inside"}]
        )

        assert snapshot.vectorizer.seen == [prepare_text("F r e e. \u0440rize inside")]
