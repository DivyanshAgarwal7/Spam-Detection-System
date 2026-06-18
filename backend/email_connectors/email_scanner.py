from flask import current_app

try:
    # Import standard headers analyzer if available
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from email_header_analyzer import analyze_headers
except ImportError:
    analyze_headers = None

def scan_emails_with_model(emails):
    """Classifies a list of fetched emails using the active machine learning model.
    
    Optionally appends header analysis results (risk_score, trust_level) if headers exist.
    """
    vectorizer = getattr(current_app, "vectorizer", None)
    model = getattr(current_app, "model", None)
    label_encoder = getattr(current_app, "label_encoder", None)
    
    if not model or not vectorizer or not label_encoder:
        raise ValueError("ML model dependencies are not loaded in the Flask application.")
        
    scanned_emails = []
    spam_count = 0
    safe_count = 0
    
    # Extract email subjects and bodies for batch vectorization
    texts = [f"{e['subject']}. {e['body']}" for e in emails]
    
    if texts:
        text_vectors = vectorizer.transform(texts)
        predictions = model.predict(text_vectors)
        final_outputs = label_encoder.inverse_transform(predictions)
    else:
        final_outputs = []
        
    for e, pred in zip(emails, final_outputs):
        pred_str = str(pred)
        # Classify as spam if not explicitly 'ham' or 'safe'
        is_spam = pred_str.lower() not in ("ham", "safe")
        
        if is_spam:
            spam_count += 1
        else:
            safe_count += 1
            
        email_result = {
            "id": e.get("id"),
            "subject": e.get("subject", "No Subject"),
            "sender": e.get("sender", "Unknown Sender"),
            "date": e.get("date", "Unknown Date"),
            "prediction": pred_str
        }
        
        # Phishing integration preparation (optional header analysis)
        if analyze_headers and e.get("raw_headers"):
            try:
                header_analysis = analyze_headers(e["raw_headers"])
                email_result["risk_score"] = header_analysis.get("risk_score")
                email_result["trust_level"] = header_analysis.get("trust_level")
            except Exception:
                pass
                
        scanned_emails.append(email_result)
        
    return {
        "total_scanned": len(emails),
        "spam_count": spam_count,
        "safe_count": safe_count,
        "emails": scanned_emails
    }
