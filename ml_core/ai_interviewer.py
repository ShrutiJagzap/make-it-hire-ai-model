import logging

class AIInterviewer:
    """
    Handles dynamic question generation and response evaluation.
    """
    async def generate_question(self, resume_summary: str) -> str:
        """
        Generates a context-aware question.
        For production, this would call the Gemini API.
        """
        # Context-aware rule engine for the core logic
        if "python" in resume_summary.lower():
            return "Given your Python experience, can you explain the differences between multiprocessing and multithreading in a high-load environment?"
        elif "ml" in resume_summary.lower() or "machine learning" in resume_summary.lower():
            return "How would you handle high bias vs high variance in a predictive model you are deploying?"
        return "Can you describe a significant technical challenge you faced and the specific steps you took to resolve it?"

    def evaluate_response(self, response: str) -> dict:
        """
        Grades the candidate's technical response depth.
        """
        word_count = len(response.strip().split())
        
        if word_count > 45:
            score, feedback = 90, "Highly technical and thorough response."
        elif word_count > 20:
            score, feedback = 70, "Adequate response, but lacks deep technical nuance."
        else:
            score, feedback = 35, "Response is significantly too brief for a professional role."
            
        return {"score": score, "feedback": feedback}