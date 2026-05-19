import csv
import numpy as np
from sklearn.naive_bayes import MultinomialNB
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
import pickle
import os

class SpamClassifier:
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.pipeline = None
        self.model_path = 'spam_model.pkl'
        self.vectorizer_path = 'vectorizer.pkl'
        
    def load_dataset(self, dataset_path='mail_data.csv'):
        """Load training data from a CSV dataset."""
        if not os.path.exists(dataset_path):
            return None, None

        emails = []
        labels = []

        with open(dataset_path, newline='', encoding='utf-8', errors='replace') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                category = row.get('Category', '').strip().lower()
                message = row.get('Message', '').strip()

                if not message:
                    continue

                if category == 'spam':
                    labels.append(1)
                elif category == 'ham':
                    labels.append(0)
                else:
                    continue

                emails.append(message)

        return emails, labels

    def create_sample_data(self):
        """Create sample training data for demonstration."""
        spam_emails = [
            "You have won a free iPhone! Click here to claim your prize",
            "Congratulations! You are selected to receive $1000000",
            "Click here to verify your account and confirm your password",
            "Urgent action needed! Your bank account has been compromised",
            "LIMITED TIME OFFER! Get 90% discount on all products",
            "You have inherited $5 million from a Nigerian prince",
            "Act now! This offer expires in 24 hours",
            "Viagra and cialis at discount prices",
            "Make money fast! Work from home and earn $5000/week",
            "Free money! No strings attached, just enter your credit card",
        ]

        ham_emails = [
            "Hi, I wanted to follow up on our meeting tomorrow at 2 PM",
            "Please find the quarterly report attached for your review",
            "Thanks for the feedback on the project proposal",
            "Can we reschedule the meeting to next Friday?",
            "Your order has been shipped and will arrive in 2-3 business days",
            "Welcome to our service, please confirm your email address",
            "Here are the updates from this week's team meeting",
            "Could you please review the attached document by EOD",
            "Thank you for your business. We appreciate your support",
            "The system maintenance is scheduled for Saturday night",
        ]

        emails = spam_emails + ham_emails
        labels = [1] * len(spam_emails) + [0] * len(ham_emails)
        return emails, labels

    def train(self):
        """Train the spam classifier."""
        emails, labels = self.load_dataset()
        if not emails or not labels:
            print('No dataset found or dataset empty. Falling back to sample training data.')
            emails, labels = self.create_sample_data()
        else:
            print(f'Loaded {len(emails)} training examples from mail_data.csv')

        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(lowercase=True, stop_words='english', max_features=5000)),
            ('classifier', MultinomialNB())
        ])

        self.pipeline.fit(emails, labels)
        self.save_model()
        print('Training complete. Model saved to', self.model_path)
    
    def load_model(self):
        """Load the trained model from disk"""
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f:
                self.pipeline = pickle.load(f)
            return True
        return False
    
    def save_model(self):
        """Save the trained model to disk"""
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.pipeline, f)
    
    def predict(self, email_text):
        """Predict if an email is spam or not"""
        if self.pipeline is None:
            if not self.load_model():
                self.train()
        
        # Make prediction
        prediction = self.pipeline.predict([email_text])[0]
        confidence = self.pipeline.predict_proba([email_text])[0]
        
        return {
            'is_spam': bool(prediction),
            'label': 'Spam' if prediction == 1 else 'Legitimate',
            'spam_confidence': float(confidence[1]),
            'legitimate_confidence': float(confidence[0])
        }


    def explain(self, email_text, top_n=5):
        """Return top contributing terms for the prediction.

        Uses the trained TF-IDF vectorizer and MultinomialNB feature log-probabilities
        to compute a simple contribution score per term present in the message.
        """
        if self.pipeline is None:
            if not self.load_model():
                self.train()

        # Access pipeline steps
        try:
            vectorizer = self.pipeline.named_steps['tfidf']
            clf = self.pipeline.named_steps['classifier']
        except Exception:
            return []

        X = vectorizer.transform([email_text])
        try:
            feature_names = vectorizer.get_feature_names_out()
        except Exception:
            feature_names = vectorizer.get_feature_names()

        x = X.toarray()[0]
        import numpy as _np

        nz = _np.where(x > 0)[0]
        if nz.size == 0:
            return []

        # feature_log_prob_[class_index, feature_index]
        log_prob = clf.feature_log_prob_
        classes = list(clf.classes_)
        # determine indices
        try:
            spam_idx = classes.index(1)
        except ValueError:
            spam_idx = 1 if classes[0] == 0 else 0
        try:
            ham_idx = classes.index(0)
        except ValueError:
            ham_idx = 0 if classes[0] == 0 else 1

        contributions = []
        for i in nz:
            term = feature_names[i]
            # contribution: tfidf_value * (logP(term|spam) - logP(term|ham))
            score = float(x[i] * (log_prob[spam_idx, i] - log_prob[ham_idx, i]))
            contributions.append((term, score))

        contributions.sort(key=lambda t: abs(t[1]), reverse=True)
        top = [{'term': t[0], 'score': round(t[1], 6)} for t in contributions[:top_n]]
        return top


if __name__ == '__main__':
    classifier = SpamClassifier()
    classifier.train()
