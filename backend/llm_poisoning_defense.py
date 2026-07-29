#!/usr/bin/env python3
"""
LLM / Training-Data Poisoning Defense
Detects poisoning indicators in proposed training samples (label flipping,
adversarially-crafted text, extreme class imbalance) and flags adversarial
text at request time. Driven by backend/routes/poisoningRoutes.js via
``python llm_poisoning_defense.py --command <cmd> --params <JSON>``.
"""

import re
import sys
import json
import math
import argparse
import hashlib
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / 'models'
MODEL_DIR.mkdir(exist_ok=True)
STATE_FILE = MODEL_DIR / 'poisoning_defense_state.json'

SUSPICIOUS_THRESHOLD = 0.3

SUSPICIOUS_PATTERNS = {
    'repeated_chars': re.compile(r'(.)\1{4,}'),
    'excessive_punctuation': re.compile(r'[!?.,]{4,}'),
    'all_caps_run': re.compile(r'[A-Z]{5,}'),
    'homoglyph': re.compile(r'[^\x00-\x7F]'),
    'weird_spacing': re.compile(r'\s{3,}'),
    'zero_width': re.compile(r'[\u200b-\u200f\ufeff]'),
}


def _shannon_entropy(text):
    """Shannon entropy over lowercase alphabetic characters only."""
    freq = {}
    total = 0
    for ch in text.lower():
        if ch.isalpha():
            freq[ch] = freq.get(ch, 0) + 1
            total += 1
    if not total:
        return 0.0
    entropy = 0.0
    for count in freq.values():
        p = count / total
        entropy -= p * math.log2(p)
    return entropy


def analyze_text(text):
    """Single-text adversarial/poisoning analysis. Mirrors the shape of the
    Node-side poisoningGuard.detectPoisoningPatterns so both layers agree on
    isSuspicious/score/patterns/details."""
    score = 0.0
    matched = []
    details = {}

    for name, pattern in SUSPICIOUS_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            count = len(matches)
            pattern_score = min(count * 0.05, 0.3)
            score += pattern_score
            matched.append(name)
            details[name] = {"count": count, "score": round(pattern_score, 4)}

    if len(text) > 1000:
        score += 0.2
        matched.append('excessive_length')

    entropy = _shannon_entropy(text)
    if entropy > 4.5:
        score += 0.3
        matched.append('high_entropy')
        details['entropy'] = round(entropy, 4)

    normalized = min(score, 1.0)
    return {
        "isSuspicious": normalized > SUSPICIOUS_THRESHOLD,
        "score": round(normalized, 4),
        "patterns": matched,
        "details": details,
    }


def _normalize_for_dedupe(text):
    return re.sub(r'\s+', ' ', text.strip().lower())


def _fingerprint(text):
    return hashlib.sha256(_normalize_for_dedupe(text).encode('utf-8')).hexdigest()


def analyze_batch(texts, labels):
    """Flags training-data poisoning indicators across a batch of samples:
    per-sample adversarial patterns, exact-duplicate texts submitted under
    conflicting labels (classic label-flipping poisoning), and extreme class
    imbalance. Duplicate detection is exact-match (hash-based) rather than
    fuzzy, so it stays O(n) even for the largest batches this API accepts.
    """
    if len(texts) != len(labels):
        raise ValueError("texts and labels must be the same length")

    n = len(texts)
    flagged = []
    seen = {}
    duplicate_conflicts = []
    label_counts = {}

    for i in range(n):
        text = texts[i]
        label = labels[i]
        label_counts[label] = label_counts.get(label, 0) + 1

        analysis = analyze_text(text)
        if analysis["isSuspicious"]:
            flagged.append({"index": i, **analysis})

        fp = _fingerprint(text)
        if fp in seen:
            first_index, first_label = seen[fp]
            if first_label != label:
                duplicate_conflicts.append({
                    "indices": [first_index, i],
                    "labels": [first_label, label],
                })
        else:
            seen[fp] = (i, label)

    imbalance_ratio = None
    is_imbalanced = False
    if len(label_counts) >= 2:
        counts = sorted(label_counts.values())
        imbalance_ratio = round(counts[-1] / max(counts[0], 1), 4)
        is_imbalanced = imbalance_ratio >= 20

    poisoning_score = min(
        (len(flagged) / n if n else 0) * 0.6
        + (len(duplicate_conflicts) / n if n else 0) * 0.8
        + (0.2 if is_imbalanced else 0),
        1.0,
    )

    return {
        "samplesAnalyzed": n,
        "isSuspicious": poisoning_score > SUSPICIOUS_THRESHOLD or bool(duplicate_conflicts),
        "score": round(poisoning_score, 4),
        "flaggedSamples": flagged,
        "duplicateConflicts": duplicate_conflicts,
        "labelDistribution": label_counts,
        "labelImbalanceRatio": imbalance_ratio,
    }


def _load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            pass
    return {"trained": False, "lastTrainedAt": None, "samplesSeen": 0, "trainingRuns": 0}


def _save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding='utf-8')


def _command_validate(params):
    texts = params.get("texts")
    labels = params.get("labels")
    if not isinstance(texts, list) or not isinstance(labels, list) or not texts:
        raise ValueError("Parameters 'texts' and 'labels' are required non-empty arrays")
    return analyze_batch(texts, labels)


def _command_detect_adversarial(params):
    text = params.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Parameter 'text' is required and must be a non-empty string")
    return analyze_text(text)


def _command_train(params):
    texts = params.get("texts")
    labels = params.get("labels")
    if not isinstance(texts, list) or not isinstance(labels, list) or not texts:
        raise ValueError("Parameters 'texts' and 'labels' are required non-empty arrays")

    validation = analyze_batch(texts, labels)
    if validation["isSuspicious"]:
        raise ValueError(
            "Refusing to train on a batch that fails poisoning validation "
            f"(score={validation['score']}, flagged={len(validation['flaggedSamples'])}, "
            f"duplicateConflicts={len(validation['duplicateConflicts'])})"
        )

    state = _load_state()
    state["trained"] = True
    state["lastTrainedAt"] = datetime.now(timezone.utc).isoformat()
    state["samplesSeen"] = state.get("samplesSeen", 0) + len(texts)
    state["trainingRuns"] = state.get("trainingRuns", 0) + 1
    state["threshold"] = SUSPICIOUS_THRESHOLD
    _save_state(state)

    return {
        "trained": True,
        "samples": len(texts),
        "totalSamplesSeen": state["samplesSeen"],
        "trainingRuns": state["trainingRuns"],
    }


def _command_status(_params):
    state = _load_state()
    return {
        "ready": True,
        "threshold": SUSPICIOUS_THRESHOLD,
        "patternCount": len(SUSPICIOUS_PATTERNS),
        "modelDir": str(MODEL_DIR),
        **state,
    }


COMMANDS = {
    "validate": _command_validate,
    "detect_adversarial": _command_detect_adversarial,
    "train": _command_train,
    "status": _command_status,
}


def _emit(payload):
    """Write a single JSON object to stdout for the calling Express process.
    Diagnostics must never be printed with plain print() - only here, and
    only ever this once per invocation - so Express can JSON.parse stdout
    directly."""
    sys.stdout.write(json.dumps(payload, default=str))
    sys.stdout.flush()


def run_cli(argv=None):
    parser = argparse.ArgumentParser(description="LLM Poisoning Defense CLI")
    parser.add_argument("--command", choices=list(COMMANDS.keys()), required=True)
    parser.add_argument("--params", default="{}", help="JSON-encoded parameters for the command.")
    args = parser.parse_args(argv)

    try:
        params = json.loads(args.params)
    except json.JSONDecodeError as error:
        _emit({"success": False, "command": args.command, "error": f"Invalid --params JSON: {error}"})
        return 1
    if not isinstance(params, dict):
        _emit({"success": False, "command": args.command, "error": "--params must be a JSON object"})
        return 1

    try:
        result = COMMANDS[args.command](params)
    except Exception as error:  # surfaced to Express via stderr + non-zero exit
        print(f"{args.command} failed: {error}", file=sys.stderr)
        _emit({"success": False, "command": args.command, "error": str(error)})
        return 1

    _emit({"success": True, "command": args.command, **result})
    return 0


if __name__ == "__main__":
    sys.exit(run_cli())
