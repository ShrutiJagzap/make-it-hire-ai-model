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
            # Programming Languages
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'go', 'golang', 
            'rust', 'php', 'swift', 'kotlin', 'scala', 'r', 'html', 'css', 'sass', 'sql', 
            'bash', 'shell',
            # Frameworks & Libraries
            'react', 'angular', 'vue', 'node', 'nodejs', 'spring', 'spring boot', 'express', 
            'django', 'flask', 'fastapi', 'laravel', 'asp.net', 'hibernate', 'redux', 'next.js', 
            'nextjs', 'nuxt', 'jquery', 'bootstrap', 'tailwind', 'pandas', 'numpy', 
            'scikit-learn', 'tensorflow', 'pytorch', 'keras',
            # Databases & Storage
            'mongodb', 'postgresql', 'postgres', 'mysql', 'oracle', 'redis', 'elasticsearch', 
            'dynamodb', 'cassandra', 'sqlite', 'mariadb', 'firebase', 'firestore',
            # Cloud & DevOps
            'aws', 'amazon web services', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 
            'jenkins', 'git', 'github', 'gitlab', 'terraform', 'ansible', 'circleci', 'travis', 
            'devops', 'ci/cd', 'cicd',
            # APIs & Protocols
            'rest api', 'rest', 'restful', 'graphql', 'grpc', 'soap', 'websocket',
            # Methodologies & Concepts
            'agile', 'scrum', 'kanban', 'microservices', 'mvc', 'oop', 'tdd', 'system design', 
            'machine learning', 'artificial intelligence', 'deep learning', 'data science', 
            'natural language processing', 'nlp', 'computer vision', 'cloud computing'
        ]
        text_lower = text.lower()
        found_skills = [skill for skill in skill_keywords if skill in text_lower]
        return list(set(found_skills))