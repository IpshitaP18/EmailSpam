"""
Gmail Bot Integration for SpamGuard
Automatically scans and filters spam in Gmail using the spam classifier
"""

import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.api_core.client_options import ClientOptions
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
import json
from datetime import datetime

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

class GmailBot:
    STATUS_FILE = os.path.join(os.path.dirname(__file__), 'gmail_status.json')
    SCAN_STATUS_FILE = os.path.join(os.path.dirname(__file__), 'gmail_scan_status.json')
    SCAN_HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'gmail_scan_history.json')

    def __init__(self, credentials_file='credentials.json', config_file='gmail_config.json'):
        """Initialize the Gmail bot"""
        self.credentials_file = credentials_file
        self.config_file = config_file
        self.service = None
        self.spam_classifier = None
        self.config = self.load_config()
        
    def save_status(self, status):
        """Save Gmail connection status to disk"""
        try:
            # Merge with existing status to preserve account and other metadata
            existing = {}
            if os.path.exists(self.STATUS_FILE):
                try:
                    with open(self.STATUS_FILE, 'r', encoding='utf-8') as ef:
                        existing = json.load(ef)
                except Exception:
                    existing = {}

            merged = existing.copy()
            # Only overwrite keys provided in status
            for k, v in (status or {}).items():
                merged[k] = v

            with open(self.STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(merged, f, indent=4)
        except Exception as error:
            print(f'Unable to save Gmail status: {error}')

    def save_scan_status(self, status):
        """Save Gmail scan progress status to disk"""
        try:
            with open(self.SCAN_STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=4)
        except Exception as error:
            print(f'Unable to save Gmail scan status: {error}')

    def load_scan_history(self):
        try:
            if os.path.exists(self.SCAN_HISTORY_FILE):
                with open(self.SCAN_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as error:
            print(f'Unable to load scan history: {error}')
        return []

    def save_scan_history(self, history):
        try:
            with open(self.SCAN_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=4)
        except Exception as error:
            print(f'Unable to save scan history: {error}')

    def authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        
        # token.pickle stores the user's access and refresh tokens
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        # If credentials don't exist or are invalid, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('gmail', 'v1', credentials=creds)
        print("✅ Gmail authentication successful!")

        try:
            profile = self.service.users().getProfile(userId='me').execute()
            self.save_status({
                'connected': True,
                'account': profile.get('emailAddress', 'me'),
                'message': 'Gmail authentication successful.',
                'last_authenticated': datetime.utcnow().isoformat()
            })
        except Exception as error:
            print(f'Warning: could not save Gmail connection profile: {error}')

        return self.service
    
    def load_config(self):
        """Load bot configuration"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        
        # Default configuration
        default_config = {
            'auto_filter': True,
            'move_to_spam': True,
            'add_labels': True,
            'scan_frequency': 'hourly',
            'confidence_threshold': 0.7,
            'whitelist': [],
            'enable_notifications': True
        }
        
        self.save_config(default_config)
        return default_config
    
    def save_config(self, config=None):
        """Save bot configuration"""
        if config is None:
            config = self.config
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)
    
    def get_emails(self, max_results=10, query=''):
        """Get emails from Gmail"""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            return messages
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
    
    def get_email_content(self, message_id):
        """Get email content from message ID"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            
            def _extract_body(payload):
                if payload.get('mimeType') == 'text/plain':
                    data = payload.get('body', {}).get('data', '')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                    return ''
                if payload.get('mimeType', '').startswith('multipart/'):
                    for part in payload.get('parts', []):
                        text = _extract_body(part)
                        if text:
                            return text
                return ''

            body = _extract_body(message['payload'])
            if body == '':
                body = message.get('snippet', '')

            return {
                'id': message_id,
                'subject': subject,
                'sender': sender,
                'body': body,
                'full_content': f"{subject}\n\n{body}"
            }
        except HttpError as error:
            print(f'An error occurred: {error}')
            return None
    
    def classify_email(self, email_content):
        """Classify an email using the spam classifier"""
        # Import classifier from backend
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
        
        from spam_classifier import SpamClassifier
        
        if self.spam_classifier is None:
            self.spam_classifier = SpamClassifier()
            if not self.spam_classifier.load_model():
                self.spam_classifier.train()
        
        return self.spam_classifier.predict(email_content)
    
    def add_label(self, message_id, label_name):
        """Add a label to an email"""
        try:
            # Get or create label
            labels = self.service.users().labels().list(userId='me').execute()
            label_id = None
            
            for label in labels.get('labels', []):
                if label['name'] == label_name:
                    label_id = label['id']
                    break
            
            if not label_id:
                label_body = {
                    'name': label_name,
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show'
                }
                created_label = self.service.users().labels().create(
                    userId='me',
                    body=label_body
                ).execute()
                label_id = created_label['id']
            
            # Apply label
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            
            print(f"✓ Label '{label_name}' added to message {message_id}")
            return True
        except HttpError as error:
            print(f'An error occurred: {error}')
            return False
    
    def move_to_spam(self, message_id):
        """Move email to spam folder"""
        try:
            # Get spam label ID
            labels = self.service.users().labels().list(userId='me').execute()
            spam_label_id = None
            
            for label in labels.get('labels', []):
                if label['name'] == '[Gmail]/Spam':
                    spam_label_id = label['id']
                    break
            
            if spam_label_id:
                self.service.users().messages().modify(
                    userId='me',
                    id=message_id,
                    body={
                        'addLabelIds': [spam_label_id],
                        'removeLabelIds': ['INBOX']
                    }
                ).execute()
                print(f"✓ Message {message_id} moved to spam")
                return True
            else:
                print("Spam label not found")
                return False
        except HttpError as error:
            print(f'An error occurred: {error}')
            return False
    
    def scan_inbox(self, max_emails=20):
        """Scan inbox and classify emails"""
        print(f"\n🔍 Scanning inbox ({max_emails} emails)...")
        
        emails = self.get_emails(max_results=max_emails, query='is:unread')
        
        scan_status = {
            'state': 'scanning',
            'message': 'Scanning Gmail inbox...',
            'processed': 0,
            'total': len(emails),
            'last_email': None,
            'last_scan': datetime.utcnow().isoformat()
        }
        self.save_scan_status(scan_status)
        # update connection heartbeat/status so UI sees bot active
        try:
            self.save_status({
                'connected': True,
                'account': None,
                'message': 'Gmail bot scanning inbox.',
                'last_seen': datetime.utcnow().isoformat()
            })
        except Exception:
            pass
        
        stats = {
            'total': 0,
            'spam': 0,
            'legitimate': 0,
            'moved': 0,
            'labeled': 0
        }
        
        if not emails:
            scan_status.update({
                'state': 'idle',
                'message': 'No unread emails found.',
                'processed': 0
            })
            self.save_scan_status(scan_status)
            return stats

        for message in emails:
            stats['total'] += 1
            email_data = self.get_email_content(message['id'])

            scan_status['processed'] = stats['total']
            scan_status['last_email'] = email_data['subject'][:80] if email_data else 'Unknown'
            scan_status['message'] = f"Processing {scan_status['processed']} of {scan_status['total']}"
            self.save_scan_status(scan_status)
            # emit heartbeat for UI
            try:
                self.save_status({
                    'connected': True,
                    'account': None,
                    'message': f"Scanning... processed {scan_status['processed']} of {scan_status['total']}",
                    'last_seen': datetime.utcnow().isoformat()
                })
            except Exception:
                pass
            
            if email_data:
                # Classify
                result = self.classify_email(email_data['full_content'])
                
                print(f"\n📧 Email: {email_data['subject'][:50]}...")
                print(f"   From: {email_data['sender']}")
                print(f"   Classification: {result['label']} ({result['spam_confidence']*100:.1f}%)")

                # Prepare per-email classification entry (for UI history)
                reasoning = []
                if hasattr(self, 'spam_classifier') and self.spam_classifier is not None:
                    try:
                        reasoning = self.spam_classifier.explain(email_data['full_content'], top_n=5)
                    except Exception:
                        reasoning = []

                entry = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'message_id': message.get('id'),
                    'subject': email_data.get('subject'),
                    'sender': email_data.get('sender'),
                    'label': result.get('label'),
                    'is_spam': bool(result.get('is_spam')),
                    'spam_confidence': float(result.get('spam_confidence') or 0.0),
                    'legitimate_confidence': float(result.get('legitimate_confidence') or 0.0),
                    'reasoning': reasoning,
                    'moved': False,
                    'labeled': False
                }
                if result['is_spam']:
                    stats['spam'] += 1
                    
                    # Move to spam if configured
                    if self.config.get('move_to_spam'):
                        if self.move_to_spam(message['id']):
                            stats['moved'] += 1
                            entry['moved'] = True
                    
                    # Add label if configured
                    if self.config.get('add_labels'):
                        if self.add_label(message['id'], 'SpamGuard-Spam'):
                            stats['labeled'] += 1
                            entry['labeled'] = True
                else:
                    stats['legitimate'] += 1
                    
                    # Add legitimate label if configured
                    if self.config.get('add_labels'):
                        if self.add_label(message['id'], 'SpamGuard-Clean'):
                            stats['labeled'] += 1
                            entry['labeled'] = True

                # Save history entry after actions so moved/labeled flags are accurate
                try:
                    history = self.load_scan_history()
                    history.insert(0, entry)
                    history = history[:200]
                    self.save_scan_history(history)
                except Exception as err:
                    print(f'Warning: failed to record scan history: {err}')

        scan_status.update({
            'state': 'completed',
            'message': f"Last scan complete: {stats['total']} emails processed.",
            'last_scan': datetime.utcnow().isoformat(),
            'processed': stats['total'],
            'last_email': scan_status['last_email']
        })
        self.save_scan_status(scan_status)
        try:
            self.save_status({
                'connected': True,
                'account': None,
                'message': f"Last scan completed: {stats['total']} processed.",
                'last_seen': datetime.utcnow().isoformat()
            })
        except Exception:
            pass
        
        return stats
    
    def get_statistics(self):
        """Get bot statistics"""
        stats = {
            'last_scan': datetime.now().isoformat(),
            'config': self.config
        }
        return stats


if __name__ == '__main__':
    # Example usage
    bot = GmailBot()
    
    # Authenticate
    bot.authenticate()
    
    # Scan inbox
    results = bot.scan_inbox(max_emails=10)
    
    # Print results
    print(f"\n📊 Scan Results:")
    print(f"   Total emails: {results['total']}")
    print(f"   Spam: {results['spam']}")
    print(f"   Legitimate: {results['legitimate']}")
    print(f"   Moved to spam: {results['moved']}")
    print(f"   Labeled: {results['labeled']}")
