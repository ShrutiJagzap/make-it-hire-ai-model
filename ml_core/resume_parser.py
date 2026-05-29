# import spacy
# import os
# import PyPDF2

# class ResumeAnalyzer:
#     def __init__(self):
#         path = "models/talent_ner"
#         self.nlp = spacy.load(path) if os.path.exists(path) else None

#     def extract_text(self, path):
#         text = ""
#         try:
#             with open(path, 'rb') as f:
#                 pdf = PyPDF2.PdfReader(f)
#                 for page in pdf.pages:
#                     text += page.extract_text() or ""
#         except Exception as e: print(f"PDF Error: {e}")
#         return text

#     def extract_skills(self, text):
#         if not self.nlp: return []
#         doc = self.nlp(text)
#         return list(set([ent.text for ent in doc.ents if ent.label_ == "SKILL"]))


import os
import PyPDF2
import re

class ResumeAnalyzer:
    def __init__(self):
        # Don't load spacy model
        self.nlp = None

    def extract_text(self, path):
        text = ""
        try:
            with open(path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                for page in pdf.pages:
                    text += page.extract_text() or ""
        except Exception as e: 
            print(f"PDF Error: {e}")
        return text

    def extract_skills(self, text):
        # Use keyword matching instead of spacy
        skill_keywords = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node', 
            'spring', 'sql', 'mongodb', 'postgresql', 'mysql', 'docker', 'kubernetes', 
            'aws', 'git', 'jenkins', 'rest api', 'graphql', 'html', 'css', 
            'typescript', 'flask', 'django', 'fastapi', 'c++', 'c#'
        ]
        text_lower = text.lower()
        found_skills = [skill for skill in skill_keywords if skill in text_lower]
        return list(set(found_skills))