# import cv2
# import os
# from deepface import DeepFace
# from sentence_transformers import SentenceTransformer, util

# class RecruitmentEngine:
#     def __init__(self):
#         # SBERT model understands that "Coding" and "Programming" are the same thing.
#         self.model = SentenceTransformer('all-MiniLM-L6-v2')

#     def calculate_score(self, resume_text, jd_text):
#         """Calculates semantic similarity between Resume and dynamic JD."""
#         if not resume_text or not jd_text: return 0.0
#         emb1 = self.model.encode(resume_text, convert_to_tensor=True)
#         emb2 = self.model.encode(jd_text, convert_to_tensor=True)
#         score = util.cos_sim(emb1, emb2)
#         return round(float(score[0][0]) * 100, 2)

#     def verify_identity(self, id_path, frame):
#         """Strict biometric check. No bypass allowed."""
#         temp = "temp_capture.jpg"
#         cv2.imwrite(temp, frame)
#         try:
#             result = DeepFace.verify(img1_path=id_path, img2_path=temp, enforce_detection=False, silent=True)
#             if os.path.exists(temp): os.remove(temp)
#             conf = round((1 - result['distance']) * 100, 2)
#             return result['verified'], conf
#         except:
#             return False, 0.0


import cv2
import os

class RecruitmentEngine:
    def __init__(self):
        # Initialize model lazily to save startup memory
        self.model = None

    def calculate_score(self, resume_text, jd_text):
        """Calculates semantic similarity between Resume and dynamic JD."""
        if not resume_text or not jd_text: return 0.0
        
        # Lazy imports and initialization
        if self.model is None:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
        from sentence_transformers import util
        emb1 = self.model.encode(resume_text, convert_to_tensor=True)
        emb2 = self.model.encode(jd_text, convert_to_tensor=True)
        score = util.cos_sim(emb1, emb2)
        return round(float(score[0][0]) * 100, 2)

    def verify_identity(self, id_path, frame):
        """Strict biometric check. No bypass allowed."""
        temp = "temp_capture.jpg"
        cv2.imwrite(temp, frame)
        try:
            from deepface import DeepFace
            result = DeepFace.verify(img1_path=id_path, img2_path=temp, enforce_detection=False, silent=True)
            if os.path.exists(temp): os.remove(temp)
            conf = round((1 - result['distance']) * 100, 2)
            return result['verified'], conf
        except:
            if os.path.exists(temp): os.remove(temp)
            return False, 0.0