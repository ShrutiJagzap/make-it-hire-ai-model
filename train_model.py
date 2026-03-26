import spacy
from spacy.training.example import Example
import json
import os
import random

def train_ner():
    print("--- [ML PHASE] TRAINING CUSTOM RESUME NER MODEL ---")
    with open('data/resume_dataset.json', 'r') as f:
        raw = json.load(f)
    train_data = [(item['text'], {"entities": item['label']}) for item in raw]

    nlp = spacy.blank("en")
    ner = nlp.add_pipe("ner")
    for _, annotations in train_data:
        for ent in annotations.get("entities"):
            ner.add_label(ent[2])

    optimizer = nlp.begin_training()
    for i in range(25):
        random.shuffle(train_data)
        losses = {}
        for text, annot in train_data:
            doc = nlp.make_doc(text)
            example = Example.from_dict(doc, annot)
            nlp.update([example], drop=0.3, losses=losses)
        print(f"Epoch {i+1} | Loss: {losses['ner']:.4f}")

    if not os.path.exists("models"): os.makedirs("models")
    nlp.to_disk("models/resume_ner_model")
    print("\n[SUCCESS] Model saved to models/resume_ner_model")

if __name__ == "__main__":
    train_ner()