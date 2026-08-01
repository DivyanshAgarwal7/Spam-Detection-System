"""The single text-preparation contract shared by training and inference.

``retrain.py`` fits the TF-IDF vocabulary on text that has been run through
:data:`~utils.text_normalizer.normalizer`, so anything that reaches
``vectorizer.transform`` at serving time must be prepared the same way or the
model is scoring a different alphabet than the one it learned. Homoglyph
substitutions, zero-width joiners and spaced-out words -- exactly the evasions
the normalizer exists to undo -- otherwise survive into the vectorizer and fall
out of vocabulary.

Every producer of model input calls :func:`prepare_text`; nothing calls the
normalizer directly. Routing both regimes through one function is what makes the
parity checkable rather than a convention that drifts.

>>> prepare_text("Free\\u200b Prize")
'Free Prize'
>>> prepare_text("\\u0441laim now")
'claim now'
>>> prepare_text("f r e e money")
'free money'
>>> prepare_text("")
''
>>> prepare_text(None) is None
True
"""

from   utils.text_normalizer    import normalizer

__all__ = ["prepare_text"]


def prepare_text(text):
    """Return ``text`` in the canonical form the model was trained on.

    Non-string input is handed back untouched: callers upstream of validation
    (bulk rows, mailbox payloads) can pass ``None`` or a stray numeric cell, and
    a preparation step is the wrong place to decide that is an error.
    """
    return normalizer.normalize(text)
