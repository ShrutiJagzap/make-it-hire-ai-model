import cv2
import os
import time
import threading
from ml_core.resume_parser import ResumeAnalyzer
from ml_core.engine import RecruitmentEngine
from ml_core.voice_processor import VoiceInterface
from ml_core.report_generator import ReportGenerator

class CameraThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(0)
        self.running = True
        self.current_frame = None

    def run(self):
        """Continuously updates the webcam feed in the background."""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                # Visual feedback for the candidate
                display_frame = frame.copy()
                cv2.putText(display_frame, "● LIVE MONITORING", (20, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.imshow("TalentAI Security Monitor", display_frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        self.cap.release()
        cv2.destroyAllWindows()

    def stop(self):
        """Safely stops the thread and releases the camera."""
        self.running = False

def run_interview():
    # Initialize all ML components
    analyzer = ResumeAnalyzer()
    engine = RecruitmentEngine()
    voice = VoiceInterface()
    
    # Start webcam thread
    cam = CameraThread()
    cam.start()

    print("\n" + "="*50 + "\n      TALENT AI PRO: STANDALONE MODE\n" + "="*50)

    # 1. SCREENING PHASE
    # Now that resume_dataset.json is gone, it uses Semantic SBERT
    res_path = "data/resume.pdf"
    if not os.path.exists(res_path):
        print(f"Error: {res_path} not found.")
        cam.stop()
        return

    jd_text = input("\n[INPUT] Paste Job Description for matching: ")
    if not jd_text.strip(): 
        jd_text = "Senior Software Engineer with Java and Python expertise"

    print("\n[ML] Analyzing Semantic Similarity...")
    text = analyzer.extract_text(res_path)
    resume_score = engine.calculate_score(text, jd_text)
    skills = analyzer.extract_skills(text)
    print(f"✅ JD Match Score: {resume_score}%")

    # 2. BIOMETRIC LOCK PHASE
    voice.speak("Screening complete. Please face the camera for biometric verification.")
    time.sleep(3) # Give candidate time to pose
    
    if cam.current_frame is not None:
        verified, bio_score = engine.verify_identity("data/id_card.jpg", cam.current_frame)
        if not verified:
            print(f"CRITICAL: Identity Mismatch ({bio_score}%).")
            voice.speak("Identity verification failed. This session is being terminated.")
            cam.stop() # This now works perfectly!
            return
        print(f"✅ Identity Verified: {bio_score}% Confidence")
    else:
        print("Error: Camera frame not captured.")
        cam.stop()
        return

    # 3. DYNAMIC INTERVIEW PHASE
    # Calls Gemini to generate questions based on detected skills
    question_bank = voice.generate_questions(skills if skills else ["General Software Engineering"])
    voice.speak(f"Verification successful. I will now ask {len(question_bank)} technical questions.")
    
    total_q_score = 0
    for i, (q, keys) in enumerate(question_bank.items(), 1):
        voice.speak(f"Question {i}: {q}")
        answer = voice.listen().lower()
        
        # Accuracy check against Gemini's keywords
        matches = [k for k in keys if k.lower() in answer]
        q_acc = (len(matches)/len(keys))*100 if keys else 50
        total_q_score += q_acc
        print(f"--- Q{i} Accuracy: {round(q_acc, 2)}% ---")

    final_int_score = round(total_q_score / len(question_bank), 2)
    
    # 4. REPORT GENERATION PHASE
    report_data = {
        "resume_score": resume_score,
        "bio_score": bio_score,
        "interview_score": final_int_score,
        "skills_found": skills,
        "missing_skills": ["System Design", "Unit Testing"], # Example placeholders
        "engagement": {"emotion": "Focused", "score": 90.0, "status": "High"}
    }
    
    ReportGenerator.generate("Candidate_User", report_data)
    voice.speak("Interview complete. Your evaluation report has been generated. Thank you.")
    
    # Cleanup
    time.sleep(2)
    cam.stop()
    print("\n[SYSTEM] Session closed successfully.")

if __name__ == "__main__":
    try:
        run_interview()
    except Exception as e:
        print(f"System Error: {e}")