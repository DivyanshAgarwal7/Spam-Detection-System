import csv
import io
import os
from flask import Blueprint, request, jsonify, current_app, send_file

bulk_predict_bp = Blueprint("bulk_predict", __name__)

def parse_and_predict_file(file):
    # Check file extension
    filename = file.filename.lower() if file.filename else ""
    if not (filename.endswith(".csv") or filename.endswith(".txt")):
        return None, "Unsupported file type. Only CSV and TXT files are supported."
        
    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > 2 * 1024 * 1024:  # 2MB limit
        return None, "File size exceeds the limit of 2MB."
    if file_size == 0:
        return None, "Empty file uploaded."
        
    try:
        content = file.read().decode("utf-8")
    except UnicodeDecodeError:
        return None, "Corrupted or invalid text encoding."
        
    messages = []
    
    if filename.endswith(".csv"):
        f = io.StringIO(content)
        try:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            if not fieldnames:
                return None, "Invalid CSV file structure or missing headers."
            
            # Find matching column (case-insensitive and stripped)
            col_name = None
            for h in fieldnames:
                if h and h.strip().lower() in ("text", "message"):
                    col_name = h
                    break
            
            if not col_name:
                return None, "CSV file must contain either a 'text' or 'message' column."
                
            for row in reader:
                val = row.get(col_name)
                if val is not None and val.strip():
                    messages.append(val.strip())
        except Exception as e:
            return None, f"Failed to parse CSV: {str(e)}"
            
    else:  # TXT file
        lines = content.splitlines()
        messages = [line.strip() for line in lines if line.strip()]
        
    if not messages:
        return None, "No valid messages found in the file."
        
    try:
        # Get model, vectorizer, and label_encoder from current_app
        vectorizer = getattr(current_app, "vectorizer", None)
        model = getattr(current_app, "model", None)
        label_encoder = getattr(current_app, "label_encoder", None)
        
        if not vectorizer or not model or not label_encoder:
            return None, "ML Model dependencies are not loaded."
        
        # Batch predict
        text_vectors = vectorizer.transform(messages)
        predictions = model.predict(text_vectors)
        final_outputs = label_encoder.inverse_transform(predictions)
        
        results = []
        for msg, pred in zip(messages, final_outputs):
            results.append({
                "message": msg,
                "prediction": str(pred)
            })
        return results, None
    except Exception as e:
        return None, f"Model prediction error: {str(e)}"

@bulk_predict_bp.route("/bulk-predict", methods=["POST"])
def bulk_predict():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No file uploaded"}), 400
        
    results, error = parse_and_predict_file(file)
    if error:
        status_code = 413 if "exceeds the limit" in error.lower() else 400
        return jsonify({"error": error}), status_code
        
    total = len(results)
    spam_count = sum(1 for r in results if r["prediction"].lower() not in ("ham", "safe"))
    non_spam_count = total - spam_count
    spam_pct = round((spam_count / total) * 100, 2) if total > 0 else 0.0
    
    return jsonify({
        "total_messages": total,
        "spam_count": spam_count,
        "non_spam_count": non_spam_count,
        "spam_percentage": spam_pct,
        "results": results
    })

@bulk_predict_bp.route("/bulk-predict/export", methods=["POST"])
def bulk_predict_export():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No file uploaded"}), 400
        
    results, error = parse_and_predict_file(file)
    if error:
        status_code = 413 if "exceeds the limit" in error.lower() else 400
        return jsonify({"error": error}), status_code
        
    try:
        output_io = io.StringIO()
        writer = csv.writer(output_io)
        writer.writerow(["message", "prediction"])
        for r in results:
            writer.writerow([r["message"], r["prediction"]])
            
        output_io.seek(0)
        mem = io.BytesIO(output_io.getvalue().encode("utf-8"))
        
        return send_file(
            mem,
            mimetype="text/csv",
            as_attachment=True,
            download_name="bulk_spam_predictions.csv"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate CSV report: {str(e)}"}), 500
