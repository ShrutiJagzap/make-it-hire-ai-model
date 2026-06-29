# from deepface import DeepFace
# import numpy as np
# import logging

# class VideoAnalyzer:
#     """
#     Real-time behavioral analysis using DeepFace.
#     """
#     @staticmethod
#     def analyze_behavior(frame: np.ndarray) -> dict:
#         try:
#             # Use the most accurate emotion model
#             analysis = DeepFace.analyze(img_path=frame, actions=['emotion'], enforce_detection=False, silent=True)
#             res = analysis[0]
#             dom_emotion = res['dominant_emotion']
            
#             # Professional Engagement mapping
#             engagement_logic = {
#                 'happy': 95, 'neutral': 85, 'surprise': 75,
#                 'fear': 40, 'angry': 20, 'sad': 15, 'disgust': 10
#             }
#             score = engagement_logic.get(dom_emotion, 50)
            
#             return {
#                 "emotion": dom_emotion,
#                 "engagement_score": score,
#                 "status": "High" if score >= 75 else "Moderate" if score >= 40 else "Low"
#             }
#         except Exception as e:
#             logging.error(f"Video Analysis Error: {e}")
#             return {"emotion": "Neutral", "engagement_score": 0, "status": "Error"}


import numpy as np
import logging

class VideoAnalyzer:
    """
    Real-time behavioral analysis using DeepFace.
    """
    @staticmethod
    def analyze_behavior(frame: np.ndarray) -> dict:
        try:
            from deepface import DeepFace
            # Use the most accurate emotion model
            analysis = DeepFace.analyze(img_path=frame, actions=['emotion'], enforce_detection=False)
            res = analysis[0]
            dom_emotion = res['dominant_emotion']
            
            # Professional Engagement mapping
            engagement_logic = {
                'happy': 95, 'neutral': 85, 'surprise': 75,
                'fear': 40, 'angry': 20, 'sad': 15, 'disgust': 10
            }
            score = engagement_logic.get(dom_emotion, 50)
            
            return {
                "emotion": dom_emotion,
                "engagement_score": score,
                "status": "High" if score >= 75 else "Moderate" if score >= 40 else "Low"
            }
        except Exception as e:
            logging.error(f"Video Analysis Error: {e}")
            return {"emotion": "Neutral", "engagement_score": 0, "status": "Error"}