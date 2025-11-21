from flask import Flask, request, jsonify
app = Flask(__name__)

@app.get('/health')
def health():
    return jsonify(success=True, statusCode=200, data={"service":"grievance-ml","status":"ok"})

@app.post('/categorize')
def categorize():
    body = request.get_json(silent=True) or {}
    text = f"{body.get('title','')} {body.get('description','')}".lower()
    if 'fraud' in text or 'scam' in text:
        cat = 'fraud'
    elif 'payment' in text or 'refund' in text:
        cat = 'payments'
    else:
        cat = 'general'
    return jsonify(success=True, statusCode=200, category=cat, confidence=0.8)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
