from flask import Flask, request, jsonify
from flask_cors import CORS
from spam_classifier import SpamClassifier
import os
import sys
import json
import threading

app = Flask(__name__)
CORS(app)

GMAIL_STATUS_FILE = os.path.join(os.path.dirname(__file__), 'gmail_status.json')
GMAIL_SCAN_STATUS_FILE = os.path.join(os.path.dirname(__file__), 'gmail_scan_status.json')
GMAIL_HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'gmail_scan_history.json')

# Global classifier
classifier = SpamClassifier()
model_ready = False

def load_model_async():
    """Load model in background thread"""
    global model_ready
    print("Loading model in background...", flush=True)
    try:
        if not classifier.load_model():
            print("Training new model...", flush=True)
            classifier.train()
            print("Model training complete!", flush=True)
        else:
            print("Model loaded successfully!", flush=True)
        model_ready = True
    except Exception as e:
        print(f"Error loading model: {e}", flush=True)
        model_ready = False

# Start loading model in background
model_thread = threading.Thread(target=load_model_async, daemon=True)
model_thread.start()

@app.route('/', methods=['GET'])
def index():
    """Health check endpoint"""
    return jsonify({'status': 'running', 'message': 'Email Spam Classifier API'})

@app.route('/api/classify', methods=['POST'])
def classify_email():
    """Classify an email as spam or legitimate"""
    try:
        if not model_ready:
            return jsonify({'error': 'Model is still loading. Please try again in a moment.'}), 503
            
        data = request.get_json()
        
        if not data or 'email_text' not in data:
            return jsonify({'error': 'Missing email_text field'}), 400
        
        email_text = data.get('email_text', '').strip()
        
        if len(email_text) < 5:
            return jsonify({'error': 'Email text must be at least 5 characters long'}), 400
        
        # Classify the email
        result = classifier.predict(email_text)
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/batch-classify', methods=['POST'])
def batch_classify():
    """Classify multiple emails at once"""
    try:
        if not model_ready:
            return jsonify({'error': 'Model is still loading. Please try again in a moment.'}), 503
            
        data = request.get_json()
        
        if not data or 'emails' not in data:
            return jsonify({'error': 'Missing emails field'}), 400
        
        emails = data.get('emails', [])
        
        if not isinstance(emails, list):
            return jsonify({'error': 'emails must be a list'}), 400
        
        if len(emails) == 0:
            return jsonify({'error': 'At least one email is required'}), 400
        
        results = []
        for email_text in emails:
            if isinstance(email_text, str) and len(email_text.strip()) >= 5:
                result = classifier.predict(email_text)
                results.append(result)
        
        return jsonify({'results': results, 'total': len(results)}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/model-info', methods=['GET'])
def model_info():
    """Get information about the model"""
    return jsonify({
        'model_type': 'Naive Bayes with TF-IDF',
        'version': '1.0',
        'description': 'Email spam classifier using machine learning',
        'accuracy': 'High accuracy on standard spam datasets',
        'model_ready': model_ready
    }), 200

def _load_json_file(path, default=None):
    default = {} if default is None else default
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

@app.route('/api/gmail-status', methods=['GET'])
def gmail_status():
    """Return Gmail integration connection and scan status."""
    status = {
        'connected': False,
        'message': 'No Gmail connection detected.',
        'account': None,
        'scan_status': {
            'state': 'idle',
            'message': 'No scan activity detected.',
            'processed': 0,
            'total': 0,
            'last_email': None,
            'last_scan': None
        }
    }

    if os.path.exists(GMAIL_STATUS_FILE):
        data = _load_json_file(GMAIL_STATUS_FILE, {})
        status.update({
            'connected': bool(data.get('connected', False)),
            'account': data.get('account'),
            'message': data.get('message', status['message'])
        })
    elif os.path.exists('token.pickle'):
        status['connected'] = True
        status['message'] = 'Gmail token found. Connection is likely active.'

    scan_data = _load_json_file(GMAIL_SCAN_STATUS_FILE, {})
    if scan_data:
        status['scan_status'].update(scan_data)

    # Include recent scan history (last 10 entries)
    try:
        history = _load_json_file(GMAIL_HISTORY_FILE, [])
        if isinstance(history, list):
            status['recent_scans'] = history[:10]
        else:
            status['recent_scans'] = []
    except Exception:
        status['recent_scans'] = []

    return jsonify(status), 200


@app.route('/api/gmail-history', methods=['GET'])
def gmail_history():
    """Return raw Gmail scan history file (supports ?limit=N)"""
    limit = request.args.get('limit', None)
    try:
        history = _load_json_file(GMAIL_HISTORY_FILE, [])
        if not isinstance(history, list):
            history = []
        if limit is not None:
            try:
                n = int(limit)
                history = history[:n]
            except Exception:
                pass
        return jsonify({'history': history}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask application...", flush=True)
    # Ensure scan history file exists so frontend can read recent scans immediately
    try:
        if not os.path.exists(GMAIL_HISTORY_FILE):
            with open(GMAIL_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f)
    except Exception:
        pass
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
