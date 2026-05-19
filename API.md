# API Documentation - Email Spam Classifier

## Base URL
```
http://localhost:5000
```

## Authentication
No authentication required for this version.

---

## Endpoints

### 1. Health Check

**Endpoint:** `GET /`

**Description:** Check if the API is running

**Response:**
```json
{
  "status": "running",
  "message": "Email Spam Classifier API"
}
```

**cURL Example:**
```bash
curl http://localhost:5000/
```

---

### 2. Single Email Classification

**Endpoint:** `POST /api/classify`

**Description:** Classify a single email as spam or legitimate

**Request Body:**
```json
{
  "email_text": "Congratulations! You have won a free iPhone! Click here to claim."
}
```

**Response (Spam):**
```json
{
  "is_spam": true,
  "label": "Spam",
  "spam_confidence": 0.92,
  "legitimate_confidence": 0.08
}
```

**Response (Legitimate):**
```json
{
  "is_spam": false,
  "label": "Legitimate",
  "spam_confidence": 0.05,
  "legitimate_confidence": 0.95
}
```

**Parameters:**
- `email_text` (string, required): The email content to classify (minimum 5 characters)

**Status Codes:**
- `200`: Success
- `400`: Bad request (missing or invalid email_text)
- `500`: Server error

**cURL Example:**
```bash
curl -X POST http://localhost:5000/api/classify \
  -H "Content-Type: application/json" \
  -d '{"email_text": "Your email content here"}'
```

**Python Example:**
```python
import requests

url = "http://localhost:5000/api/classify"
payload = {"email_text": "Congratulations! You have won..."}
response = requests.post(url, json=payload)
result = response.json()

print(f"Is Spam: {result['is_spam']}")
print(f"Spam Confidence: {result['spam_confidence']:.2%}")
```

**JavaScript Example:**
```javascript
const response = await fetch('http://localhost:5000/api/classify', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email_text: 'Your email here' })
});

const result = await response.json();
console.log(`Spam Confidence: ${(result.spam_confidence * 100).toFixed(2)}%`);
```

---

### 3. Batch Email Classification

**Endpoint:** `POST /api/batch-classify`

**Description:** Classify multiple emails at once

**Request Body:**
```json
{
  "emails": [
    "Click here to win a free prize!",
    "Hi, let's schedule a meeting tomorrow",
    "Your password verification is required immediately"
  ]
}
```

**Response:**
```json
{
  "results": [
    {
      "is_spam": true,
      "label": "Spam",
      "spam_confidence": 0.88,
      "legitimate_confidence": 0.12
    },
    {
      "is_spam": false,
      "label": "Legitimate",
      "spam_confidence": 0.03,
      "legitimate_confidence": 0.97
    },
    {
      "is_spam": true,
      "label": "Spam",
      "spam_confidence": 0.91,
      "legitimate_confidence": 0.09
    }
  ],
  "total": 3
}
```

**Parameters:**
- `emails` (array of strings, required): List of emails to classify
- Each email must be at least 5 characters long

**Status Codes:**
- `200`: Success
- `400`: Bad request (missing or invalid emails)
- `500`: Server error

**Constraints:**
- Maximum 100 emails per batch
- Each email must be 5-10000 characters

**cURL Example:**
```bash
curl -X POST http://localhost:5000/api/batch-classify \
  -H "Content-Type: application/json" \
  -d '{
    "emails": [
      "Email 1 content",
      "Email 2 content",
      "Email 3 content"
    ]
  }'
```

**Python Example:**
```python
import requests

url = "http://localhost:5000/api/batch-classify"
payload = {
    "emails": [
        "Click to win a prize!",
        "Let's meet tomorrow"
    ]
}

response = requests.post(url, json=payload)
data = response.json()

for i, result in enumerate(data['results']):
    print(f"Email {i+1}: {result['label']} ({result['spam_confidence']:.2%} spam)")
```

---

### 4. Model Information

**Endpoint:** `GET /api/model-info`

**Description:** Get information about the trained model

**Response:**
```json
{
  "model_type": "Naive Bayes with TF-IDF",
  "version": "1.0",
  "description": "Email spam classifier using machine learning",
  "accuracy": "High accuracy on standard spam datasets"
}
```

**cURL Example:**
```bash
curl http://localhost:5000/api/model-info
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Missing email_text field"
}
```

### 500 Server Error
```json
{
  "error": "Internal server error message"
}
```

---

## Response Format

All responses are in JSON format with proper HTTP status codes.

### Success Response Structure:
```json
{
  "is_spam": boolean,
  "label": "Spam" | "Legitimate",
  "spam_confidence": float (0.0-1.0),
  "legitimate_confidence": float (0.0-1.0)
}
```

### Error Response Structure:
```json
{
  "error": "Error message describing what went wrong"
}
```

---

## Rate Limiting

Currently no rate limiting is implemented. This is recommended for production:

**Suggested limits:**
- 100 requests per minute per IP
- 1000 classifications per hour per IP
- Batch size limit: 100 emails

---

## CORS Headers

CORS is enabled for development. The API accepts requests from all origins.

For production, modify in `backend/app.py`:
```python
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://yourdomain.com"],
        "methods": ["GET", "POST"]
    }
})
```

---

## Integration Examples

### Using the API in Python

```python
import requests

class SpamClassifierClient:
    def __init__(self, api_url="http://localhost:5000"):
        self.api_url = api_url
    
    def classify(self, email_text):
        """Classify a single email"""
        response = requests.post(
            f"{self.api_url}/api/classify",
            json={"email_text": email_text}
        )
        return response.json()
    
    def classify_batch(self, emails):
        """Classify multiple emails"""
        response = requests.post(
            f"{self.api_url}/api/batch-classify",
            json={"emails": emails}
        )
        return response.json()

# Usage
client = SpamClassifierClient()
result = client.classify("Click here to win!")
print(result['label'])
```

### Using the API in JavaScript

```javascript
class SpamClassifier {
    constructor(apiUrl = "http://localhost:5000") {
        this.apiUrl = apiUrl;
    }
    
    async classify(emailText) {
        const response = await fetch(`${this.apiUrl}/api/classify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email_text: emailText })
        });
        return response.json();
    }
    
    async classifyBatch(emails) {
        const response = await fetch(`${this.apiUrl}/api/batch-classify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ emails })
        });
        return response.json();
    }
}

// Usage
const classifier = new SpamClassifier();
const result = await classifier.classify("Your email here");
console.log(result.label);
```

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Average Response Time | < 100ms |
| Maximum Batch Size | 100 emails |
| Max Email Length | 10,000 characters |
| Model Load Time | ~500ms on startup |
| Memory Usage | ~100-150MB |

---

## Troubleshooting

### API returns 500 error
- Check if Flask server is running
- Review server logs for errors
- Ensure email_text is a string

### CORS errors in browser
- Ensure backend is running with CORS enabled
- Check browser console for specific errors
- Try from a different browser

### Slow response times
- Check system resources (CPU, RAM)
- Verify email content size (< 10,000 chars)
- Reduce batch size if classifying many emails

---

## Version History

**v1.0.0** (Current)
- Initial release
- Single and batch classification
- Naive Bayes model with TF-IDF
- Basic API endpoints

**Planned v2.0.0**
- Deep learning models (LSTM, BERT)
- User feedback integration
- Model versioning
- Enhanced analytics

---

## License & Support

For more information, see README.md and SETUP.md files.

---

**API Documentation Last Updated: 2024**
