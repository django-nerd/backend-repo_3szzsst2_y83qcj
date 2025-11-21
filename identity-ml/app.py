from flask import Flask, request, jsonify
app = Flask(__name__)

@app.get('/health')
def health():
    return jsonify(success=True, statusCode=200, data={"service":"identity-ml","status":"ok"})

@app.post('/predict')
def predict():
    body = request.get_json(silent=True) or {}
    # Dummy logic: approve if any payload present
    approved = bool(body)
    score = 0.9 if approved else 0.1
    return jsonify(success=True, statusCode=200, approved=approved, score=score)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
