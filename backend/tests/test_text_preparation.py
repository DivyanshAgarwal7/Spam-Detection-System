"""Parity coverage for the shared text-preparation contract (issue #1037).

The value of the contract is that training and serving cannot disagree, so these
tests assert the property that matters -- obfuscated input reduces to the same
canonical string as its plain equivalent -- rather than pinning the normalizer's
internal steps, which belong to its own tests.
"""

import text_preparation
from   text_preparation         import prepare_text


class TestCanonicalForm:
    def test_zero_width_characters_are_stripped(self):
        assert prepare_text("Free\u200b Prize\u200d") == prepare_text("Free Prize")

    def test_cyrillic_homoglyphs_fold_to_latin(self):
        # "claim" spelled with Cyrillic es, a and i.
        assert prepare_text("\u0441l\u0430\u0456m") == prepare_text("claim")

    def test_spaced_out_words_are_rejoined(self):
        assert prepare_text("f r e e money") == prepare_text("free money")

    def test_repeated_whitespace_collapses(self):
        assert prepare_text("win   a    prize") == prepare_text("win a prize")

    def test_already_canonical_text_is_unchanged(self):
        assert prepare_text("claim your free prize") == "claim your free prize"

    def test_preparation_is_idempotent(self):
        once = prepare_text("F r e e\u200b m\u043en\u0435y")
        assert prepare_text(once) == once


class TestNonStringInput:
    def test_none_passes_through(self):
        assert prepare_text(None) is None

    def test_empty_string_passes_through(self):
        assert prepare_text("") == ""

    def test_non_string_passes_through(self):
        assert prepare_text(42) == 42


class TestTrainServeParity:
    def test_training_and_inference_share_one_entry_point(self):
        """Both regimes must import the same callable, not two copies of it."""
        import retrain

        assert retrain.prepare_text is text_preparation.prepare_text
