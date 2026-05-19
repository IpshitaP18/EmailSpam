import os
import csv
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.model_selection import train_test_split
from spam_classifier import SpamClassifier

# Load dataset
classifier = SpamClassifier()
emails, labels = classifier.load_dataset('mail_data.csv')
if emails is None or labels is None:
    raise SystemExit('mail_data.csv not found in backend folder.')

spam_count = sum(1 for l in labels if l == 1)
ham_count = sum(1 for l in labels if l == 0)

# Split data for evaluation
X_train, X_test, y_train, y_test = train_test_split(
    emails, labels, test_size=0.2, random_state=42, stratify=labels
)

# Ensure model is trained
if not classifier.load_model():
    classifier.train()

predictions = classifier.pipeline.predict(X_test)
accuracy = accuracy_score(y_test, predictions)
report = classification_report(y_test, predictions, target_names=['ham', 'spam'])
cm = confusion_matrix(y_test, predictions)

stats = [
    'Spam Classifier Model Statistics',
    '=================================',
    f'Dataset path: {os.path.abspath("mail_data.csv")}',
    f'Total examples: {len(labels)}',
    f' - Spam examples: {spam_count}',
    f' - Ham examples: {ham_count}',
    f'Training examples: {len(X_train)}',
    f'Test examples: {len(X_test)}',
    '',
    'Model: Naive Bayes with TF-IDF',
    f'Model file: {os.path.abspath(classifier.model_path)}',
    '',
    'Performance Metrics',
    '-------------------',
    f'Accuracy: {accuracy:.4f}',
    '',
    'Classification report:',
    report,
    'Confusion matrix:',
    str(cm),
]

output_file = 'model_statistics.txt'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(stats))

print(f'Created {output_file}')
