import csv
import os
import re
from collections import Counter

# Custom stop words list
STOP_WORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", 
    "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", 
    "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", 
    "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", 
    "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", 
    "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", 
    "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", 
    "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", 
    "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", 
    "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", 
    "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", 
    "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now",
    "get", "would", "could", "should", "send", "received"
}

# Fallback statistics data
FALLBACK_KEYWORDS = {
    "spam": [
        {"keyword": "free", "count": 45},
        {"keyword": "prize", "count": 35},
        {"keyword": "winner", "count": 30},
        {"keyword": "claim", "count": 28},
        {"keyword": "offer", "count": 25},
        {"keyword": "urgent", "count": 22},
        {"keyword": "guaranteed", "count": 19},
        {"keyword": "cash", "count": 18},
        {"keyword": "bonus", "count": 15},
        {"keyword": "now", "count": 14}
    ],
    "smishing": [
        {"keyword": "otp", "count": 40},
        {"keyword": "verify", "count": 38},
        {"keyword": "bank", "count": 35},
        {"keyword": "account", "count": 32},
        {"keyword": "suspended", "count": 28},
        {"keyword": "login", "count": 25},
        {"keyword": "secure", "count": 22},
        {"keyword": "alert", "count": 20},
        {"keyword": "update", "count": 19},
        {"keyword": "link", "count": 17}
    ],
    "offensive": [
        {"keyword": "hate", "count": 15},
        {"keyword": "trash", "count": 12},
        {"keyword": "stupid", "count": 10},
        {"keyword": "abusive", "count": 8},
        {"keyword": "fake", "count": 7}
    ]
}

FALLBACK_PHRASES = [
    {"phrase": "click here now", "count": 25},
    {"phrase": "claim your prize", "count": 20},
    {"phrase": "urgent account update", "count": 18},
    {"phrase": "verify your identity", "count": 15},
    {"phrase": "congratulations you won", "count": 12},
    {"phrase": "action required immediately", "count": 10},
    {"phrase": "unsecured crypto giveaway", "count": 8},
    {"phrase": "reset your password", "count": 7}
]

FALLBACK_SUSPICIOUS_TERMS = [
    "crypto giveaway",
    "verify wallet",
    "account suspended",
    "urgent action required",
    "claim bonus reward",
    "confirm credit card",
    "unauthorized login attempt",
    "exclusive cashback offer"
]

FALLBACK_CATEGORY_INDICATORS = {
    "spam": ["free", "prize", "winner", "offer", "claim"],
    "smishing": ["otp", "verify", "bank", "account", "login"],
    "offensive": ["abusive", "hate", "trash", "stupid", "fake"]
}

def tokenize(text):
    """Lowercases text and extracts alphabetical words of length >= 3."""
    if not text:
        return []
    return re.findall(r'\b[a-z]{3,}\b', text.lower())

def load_data():
    """Loads text classifications from feedback store and dataset."""
    messages = []
    
    # Try feedback_store.csv in backend directory
    base_dir = os.path.dirname(__file__)
    feedback_path = os.path.join(base_dir, "output", "feedback_store.csv")
    if os.path.isfile(feedback_path):
        try:
            with open(feedback_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    text = row.get("text")
                    # Prefer corrected label if user supplied it, otherwise fallback to predicted
                    category = row.get("correct_label") or row.get("predicted_label")
                    if text and category:
                        messages.append({
                            "text": text.strip(),
                            "category": category.strip().lower()
                        })
        except Exception:
            pass
            
    # Try dataset.csv in backend directory or workspace root
    dataset_paths = [
        os.path.join(base_dir, "dataset.csv"),
        os.path.join(os.path.dirname(base_dir), "dataset.csv")
    ]
    for path in dataset_paths:
        if os.path.isfile(path):
            try:
                with open(path, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        text = row.get("text") or row.get("message")
                        category = row.get("label")
                        if text and category:
                            messages.append({
                                "text": text.strip(),
                                "category": category.strip().lower()
                            })
                break  # Stop after loading the first found dataset
            except Exception:
                pass
                
    return messages

def get_spam_insights(limit=10, category=None):
    """Analyzes message data and returns top keywords, phrases, recent terms, and indicators."""
    messages = load_data()
    
    # If no data exists, output fallback indicators
    if len(messages) < 5:
        if category:
            cat_lower = category.lower()
            if cat_lower in FALLBACK_KEYWORDS:
                top_k = FALLBACK_KEYWORDS[cat_lower][:limit]
            else:
                top_k = []
            
            # Simple category filtering for phrases / terms
            indicators = FALLBACK_CATEGORY_INDICATORS.get(cat_lower, [])
            top_p = [p for p in FALLBACK_PHRASES if any(w in p["phrase"] for w in indicators)][:limit]
            if not top_p:
                top_p = FALLBACK_PHRASES[:limit]
                
            recent = [t for t in FALLBACK_SUSPICIOUS_TERMS if any(w in t for w in indicators)][:limit]
            if not recent:
                recent = FALLBACK_SUSPICIOUS_TERMS[:limit]
        else:
            # Combine keywords across categories
            combined_k = {}
            for cat, kws in FALLBACK_KEYWORDS.items():
                for kw in kws:
                    combined_k[kw["keyword"]] = combined_k.get(kw["keyword"], 0) + kw["count"]
            top_k = [{"keyword": k, "count": v} for k, v in sorted(combined_k.items(), key=lambda x: x[1], reverse=True)][:limit]
            top_p = FALLBACK_PHRASES[:limit]
            recent = FALLBACK_SUSPICIOUS_TERMS[:limit]
            
        return {
            "top_keywords": top_k,
            "trending_phrases": top_p,
            "recent_suspicious_terms": recent,
            "category_indicators": FALLBACK_CATEGORY_INDICATORS
        }

    # If real data is loaded, run calculations
    if category:
        filtered_msgs = [m for m in messages if m["category"] == category.lower()]
    else:
        # Exclude ham and safe messages to focus on spam patterns
        filtered_msgs = [m for m in messages if m["category"] not in ("ham", "safe")]
        
    # 1. Keywords Frequency
    keywords_counter = Counter()
    for m in filtered_msgs:
        words = tokenize(m["text"])
        words_filtered = [w for w in words if w not in STOP_WORDS]
        keywords_counter.update(words_filtered)
        
    top_keywords = [{"keyword": k, "count": c} for k, c in keywords_counter.most_common(limit)]
    
    # 2. Trending phrases (N-grams)
    phrases_counter = Counter()
    for m in filtered_msgs:
        words = tokenize(m["text"])
        
        # Bigrams (2 words)
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i+1]}"
            if words[i] not in STOP_WORDS or words[i+1] not in STOP_WORDS:
                phrases_counter[phrase] += 1
                
        # Trigrams (3 words)
        for i in range(len(words) - 2):
            phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
            if words[i] not in STOP_WORDS or words[i+1] not in STOP_WORDS or words[i+2] not in STOP_WORDS:
                phrases_counter[phrase] += 1
                
    trending_phrases = [{"phrase": p, "count": c} for p, c in phrases_counter.most_common(limit)]
    
    # 3. Recently Flagged terms (focusing on the last 20 messages)
    recent_msgs = filtered_msgs[-20:]
    recent_counter = Counter()
    for m in recent_msgs:
        words = tokenize(m["text"])
        words_filtered = [w for w in words if w not in STOP_WORDS]
        for w in words_filtered:
            recent_counter[w] += 1
        for i in range(len(words_filtered) - 1):
            recent_counter[f"{words_filtered[i]} {words_filtered[i+1]}"] += 1
            
    recent_suspicious_terms = [item[0] for item in recent_counter.most_common(limit)]
    if len(recent_suspicious_terms) < 3:
        # Pad with fallbacks if needed
        recent_suspicious_terms = list(dict.fromkeys(recent_suspicious_terms + FALLBACK_SUSPICIOUS_TERMS))[:limit]
        
    # 4. Category Indicators
    category_indicators = {}
    for cat in ("spam", "smishing", "offensive"):
        cat_msgs = [m for m in messages if m["category"] == cat]
        cat_counter = Counter()
        for m in cat_msgs:
            words = tokenize(m["text"])
            words_filtered = [w for w in words if w not in STOP_WORDS]
            cat_counter.update(words_filtered)
        cat_inds = [item[0] for item in cat_counter.most_common(5)]
        if not cat_inds:
            cat_inds = FALLBACK_CATEGORY_INDICATORS.get(cat, [])
        category_indicators[cat] = cat_inds
        
    return {
        "top_keywords": top_keywords,
        "trending_phrases": trending_phrases,
        "recent_suspicious_terms": recent_suspicious_terms,
        "category_indicators": category_indicators
    }
