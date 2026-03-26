import spacy
import os
import PyPDF2

class ResumeAnalyzer:
    def __init__(self):
        path = "models/talent_ner"
        self.nlp = spacy.load(path) if os.path.exists(path) else None

    def extract_text(self, path):
        text = ""
        try:
            with open(path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                for page in pdf.pages:
                    text += page.extract_text() or ""
        except Exception as e: print(f"PDF Error: {e}")
        return text

    def extract_skills(self, text):
        if not self.nlp: return []
        doc = self.nlp(text)
        return list(set([ent.text for ent in doc.ents if ent.label_ == "SKILL"]))