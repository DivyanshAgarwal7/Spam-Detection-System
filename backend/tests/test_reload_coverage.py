"""Every prediction path follows a hot reload (issue #1037).

A reload that refreshes only some of the served objects leaves paths disagreeing
with each other, which is the same class of defect as train-serve skew. These
tests exercise the state holder directly with fakes -- no artifacts on disk -- and
assert that the URL pair and mailbox scanning both move with the swap.
"""


import serving_state


def _state(loader):
    return serving_state.ServingState(
        model="model-v1",
        vectorizer="vectorizer-v1",
        label_encoder="encoder-v1",
        xai_service="xai-v1",
        loader=loader,
        url_model="url-model-v1",
        url_vectorizer="url-vectorizer-v1",
    )


class TestUrlPairIsHotSwapped:
    def test_initial_snapshot_carries_the_url_pair(self):
        snapshot = _state(lambda: {}).snapshot()

        assert snapshot.url_model == "url-model-v1"
        assert snapshot.url_vectorizer == "url-vectorizer-v1"

    def test_reload_replaces_the_url_pair(self):
        state = _state(
            lambda: {
                "model": "model-v2",
                "vectorizer": "vectorizer-v2",
                "label_encoder": "encoder-v2",
                "xai_service": "xai-v2",
                "url_model": "url-model-v2",
                "url_vectorizer": "url-vectorizer-v2",
            }
        )

        snapshot = state.reload()

        assert snapshot.url_model == "url-model-v2"
        assert snapshot.url_vectorizer == "url-vectorizer-v2"
        assert snapshot.version == 2

    def test_loader_may_omit_the_url_pair(self):
        """Existing lightweight loaders must keep working after the extension."""
        state = _state(
            lambda: {
                "model": "model-v2",
                "vectorizer": "vectorizer-v2",
                "label_encoder": "encoder-v2",
                "xai_service": "xai-v2",
            }
        )

        snapshot = state.reload()

        assert snapshot.url_model is None
        assert snapshot.model == "model-v2"


class TestMailboxScanFollowsReload:
    def test_scanning_reads_the_post_reload_objects(self, monkeypatch):
        from email_connectors import email_scanner

        captured = []

        class Vectorizer:
            def __init__(self, tag):
                self.tag = tag

            def transform(self, texts):
                captured.append(self.tag)
                raise RuntimeError("stop after capturing the serving objects")

        state = serving_state.ServingState(
            model="model-v1",
            vectorizer=Vectorizer("v1"),
            label_encoder="encoder-v1",
            xai_service="xai-v1",
            loader=lambda: {
                "model": "model-v2",
                "vectorizer": Vectorizer("v2"),
                "label_encoder": "encoder-v2",
                "xai_service": "xai-v2",
            },
        )
        monkeypatch.setattr(email_scanner.serving_state, "STATE", state)
        monkeypatch.setattr(email_scanner, "analyze_headers", None)

        email = [{"subject": "hello", "body": "world"}]
        for _ in range(1):
            try:
                email_scanner.scan_emails_with_model(email)
            except RuntimeError:
                pass

        state.reload()
        try:
            email_scanner.scan_emails_with_model(email)
        except RuntimeError:
            pass

        # The second scan must have used the reloaded vectorizer, not the one the
        # process started with.
        assert captured == ["v1", "v2"]


class TestSnapshotStaysInternallyConsistent:
    def test_reader_is_unaffected_by_a_later_reload(self):
        state = _state(
            lambda: {
                "model": "model-v2",
                "vectorizer": "vectorizer-v2",
                "label_encoder": "encoder-v2",
                "xai_service": "xai-v2",
                "url_model": "url-model-v2",
                "url_vectorizer": "url-vectorizer-v2",
            }
        )
        held = state.snapshot()

        state.reload()

        assert held.url_model == "url-model-v1"
        assert held.model == "model-v1"
