# import os, shutil, uuid, cv2, json
# import base64
# import numpy as np
# from fastapi import FastAPI, UploadFile, File, Form, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# import requests
# from typing import Optional, List
# from datetime import datetime
# import logging
# import re
# import time
# # import whisper
# import tempfile
# import subprocess

# # Import your ML modules
# from ml_core.resume_parser import ResumeAnalyzer
# from ml_core.engine import RecruitmentEngine
# from ml_core.report_generator import ReportGenerator
# from ml_core.video_analyzer import VideoAnalyzer

# import firebase_admin
# from firebase_admin import credentials, storage
# import tempfile

# from dotenv import load_dotenv
# load_dotenv()

# # Configure Logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# app = FastAPI(title="MakeItHired AI Service")


# ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", 
#     "http://localhost:5173,"
#     "http://localhost:8081,"
#     "https://make-it-hire-frontend.vercel.app,"
#     "https://make-it-hire-backend.onrender.com"
# ).split(",")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=ALLOWED_ORIGINS,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Initialize ML components
# analyzer = ResumeAnalyzer()
# engine = RecruitmentEngine()
# video_analyzer = VideoAnalyzer()

# # model = whisper.load_model("base")

# UPLOAD_DIR = "data/uploads"
# ID_PHOTOS_DIR = "data/id_photos"
# REPORTS_DIR = "data/reports"
# os.makedirs(UPLOAD_DIR, exist_ok=True)
# os.makedirs(ID_PHOTOS_DIR, exist_ok=True)
# os.makedirs(REPORTS_DIR, exist_ok=True)

# # Store active sessions
# active_sessions = {}


# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# firebase_initialized = False

# GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

# try:
#     # Check if service account file exists in current directory
#     if os.path.exists("firebase-service-account.json"):
#         cred = credentials.Certificate("firebase-service-account.json")
#         firebase_admin.initialize_app(cred, {
#             'storageBucket': 'make-it-hire-70beb.appspot.com'  # Replace with YOUR bucket name
#         })
#         firebase_initialized = True
#         print(" Firebase Storage initialized for Python service")
#     else:
#         print("⚠️ Firebase service account not found, using local storage")
# except Exception as e:
#     print(f"⚠️ Firebase initialization failed: {e}")

# # ========== ADD UPLOAD FUNCTION HERE ==========
# def upload_to_firebase(file_path, folder, user_id):
#     """Upload file to Firebase Storage"""
#     if not firebase_initialized:
#         return None
    
#     try:
#         bucket = storage.bucket()
#         blob_name = f"{folder}/{user_id}_{int(time.time())}_{os.path.basename(file_path)}"
#         blob = bucket.blob(blob_name)
#         blob.upload_from_filename(file_path)
        
#         # Make public (optional)
#         blob.make_public()
        
#         print(f" File uploaded to Firebase: {blob_name}")
#         return blob.public_url
        
#     except Exception as e:
#         print(f"Firebase upload error: {e}")
#         return None
    
# # whisper_model = None

# # def get_whisper_model():
# #     global whisper_model
# #     if whisper_model is None:
# #         print("🔄 Loading Whisper model...")
# #         whisper_model = whisper.load_model("base")
# #         print("✅ Whisper model loaded")
# #     return whisper_model

# # ==================== HELPER FUNCTIONS ====================

# def calculate_resume_score(text: str, skills: list) -> int:
#     """Calculate resume score based on various factors"""
#     score = 0
#     if "@" in text: score += 10
#     if any(char.isdigit() for char in text) and len(text) > 10: score += 10
#     education_keywords = ['bachelor', 'master', 'phd', 'degree', 'university', 'college']
#     if any(k in text.lower() for k in education_keywords): score += 15
#     experience_keywords = ['experience', 'worked', 'employed', 'intern']
#     if any(k in text.lower() for k in experience_keywords): score += 15
#     score += min(len(skills) * 2, 20)
#     word_count = len(text.split())
#     if word_count > 500: score += 20
#     elif word_count > 300: score += 15
#     elif word_count > 200: score += 10
#     return min(score, 100)

# def extract_experience_years(text: str) -> float:
#     """Extract years of experience from text"""
#     patterns = [
#         r'(\d+)\+?\s*years? of experience',
#         r'experience of (\d+)\+?\s*years?',
#         r'(\d+)\+?\s*years? experience',
#     ]
#     for pattern in patterns:
#         match = re.search(pattern, text.lower())
#         if match:
#             return float(match.group(1))
#     years = re.findall(r'\b(20\d{2})\b', text)
#     if years:
#         return 2026 - int(max(years))
#     return 0.0

# def generate_recommendations(text: str, skills: list, experience: float) -> list:
#     """Generate resume improvement recommendations"""
#     recommendations = []
#     if not skills:
#         recommendations.append("Add a dedicated skills section with relevant technical skills")
#     elif len(skills) < 5:
#         recommendations.append("Include more relevant skills to improve your profile")
#     if not experience or experience < 1:
#         recommendations.append("Clearly mention your years of experience")
#     if "education" not in text.lower() and "university" not in text.lower():
#         recommendations.append("Add your educational qualifications")
#     if "project" not in text.lower():
#         recommendations.append("Include projects you've worked on with specific achievements")
#     if len(text.split()) < 200:
#         recommendations.append("Add more content to your resume - aim for at least 200-300 words")
#     if not recommendations:
#         recommendations.append("Your resume looks good! Consider adding more quantifiable achievements")
#     return recommendations

# # ==================== ENDPOINTS ====================

# @app.get("/")
# async def root():
#     return {
#         "service": "MakeItHired AI Service",
#         "status": "active",
#         "features": ["resume_parsing", "skill_extraction", "semantic_matching", "biometric_verification", "video_analysis"]
#     }

# @app.get("/health")
# async def health():
#     return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# @app.post("/parse-resume")
# async def parse_resume(file: UploadFile = File(...)):
#     """Parse resume and extract skills, experience, and generate score"""
#     try:
#         if not file.filename.endswith('.pdf'):
#             raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
#         session_id = str(uuid.uuid4())
#         file_path = os.path.join(UPLOAD_DIR, f"{session_id}.pdf")
        
#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)
        
#         resume_text = analyzer.extract_text(file_path)
        
#         if not resume_text.strip():
#             raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
#         skills = analyzer.extract_skills(resume_text)
#         resume_score = calculate_resume_score(resume_text, skills)
#         experience_years = extract_experience_years(resume_text)
#         recommendations = generate_recommendations(resume_text, skills, experience_years)
        
#         result = {
#             "session_id": session_id,
#             "resume_score": resume_score,
#             "skills_found": skills,
#             "experience_years": experience_years,
#             "recommendations": recommendations,
#             "word_count": len(resume_text.split()),
#             "filename": file.filename,
#             "has_email": "@" in resume_text,
#             "has_phone": any(char.isdigit() for char in resume_text) and len(resume_text) > 9,
#             "has_education": any(k in resume_text.lower() for k in ['bachelor', 'master', 'phd', 'degree']),
#             "has_project": "project" in resume_text.lower()
#         }
        
#         active_sessions[session_id] = {
#             "resume_text": resume_text,
#             "skills": skills,
#             "resume_score": resume_score,
#             "timestamp": datetime.now().isoformat()
#         }
        
#         return result
        
#     except Exception as e:
#         logger.error(f"Parse resume error: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/generate-questions")
# async def generate_interview_questions(
#     session_id: str = Form(...),
#     job_title: str = Form(None),
#     job_description: str = Form(None),
#     resume_skills: str = Form(None)
# ):
#     """Generate JOB-SPECIFIC interview questions based on role"""
#     try:
#         if session_id not in active_sessions:
#             active_sessions[session_id] = {}
#             logger.info(f"Created new session: {session_id}")
        
#         session_data = active_sessions[session_id]
        
#         # Get job title - this is the key for role-based questions
#         job_title_text = job_title or session_data.get("job_title", "Software Developer")
#         job_desc_text = job_description or session_data.get("job_description", "")
        
#         # Get skills from resume
#         candidate_skills = resume_skills or session_data.get("skills", "")
#         if not candidate_skills or candidate_skills.strip() == "":
#             candidate_skills = "Full Stack Development, Python, Java, JavaScript"
        
#         # Store in session
#         session_data["job_title"] = job_title_text
#         session_data["job_description"] = job_desc_text
#         session_data["skills"] = candidate_skills
        
#         logger.info(f"Generating questions for role: {job_title_text}")
        
#         # Create role-specific prompt for Gemini
#         prompt = f"""
#         You are a technical interviewer for a {job_title_text} position.
        
#         **IMPORTANT: Generate questions SPECIFIC to this role: {job_title_text}**
        
#         Candidate's Skills: {candidate_skills}
        
#         Generate EXACTLY 5 interview questions:
        
#         1. FIRST QUESTION MUST BE: "Tell me about yourself and your experience relevant to this {job_title_text} role."
        
#         2. For remaining 4 questions, make them SPECIFIC to {job_title_text}:
#            - If Java Full Stack: Ask about Spring Boot, React, REST APIs, databases
#            - If Data Science: Ask about Python, pandas, machine learning algorithms, data visualization
#            - If Frontend: Ask about React/Vue, JavaScript, CSS, state management
#            - If Backend: Ask about APIs, databases, microservices, authentication
        
#         Format response as JSON:
#         {{
#             "questions": [
#                 {{"text": "question text", "type": "intro/technical/problem-solving/behavioral", "keywords": ["keyword1", "keyword2"]}}
#             ]
#         }}
#         """
        
#         try:
#             response = requests.post(
#                 GEMINI_URL,
#                 json={
#                     "contents": [{"parts": [{"text": prompt}]}],
#                     "generationConfig": {
#                         "temperature": 0.7,
#                         "maxOutputTokens": 2048,
#                         "responseMimeType": "application/json"
#                     }
#                 },
#                 timeout=30
#             )
            
#             if response.status_code == 200:
#                 result = response.json()
#                 questions_text = result['candidates'][0]['content']['parts'][0]['text']
#                 questions_data = json.loads(questions_text)
#                 questions_list = [q["text"] for q in questions_data["questions"]]
#                 questions_metadata = questions_data["questions"]
                
#                 session_data["questions"] = questions_list
#                 session_data["questions_metadata"] = questions_metadata
#                 session_data["current_question"] = 0
                
#                 logger.info(f"Generated {len(questions_list)} questions for {job_title_text}")
                
#                 return {
#                     "questions": questions_list,
#                     "metadata": questions_metadata,
#                     "job_title": job_title_text,
#                     "total": len(questions_list)
#                 }
#             else:
#                 fallback = generate_fallback_questions(job_title_text, candidate_skills)
#                 session_data["questions"] = fallback["questions"]
#                 session_data["questions_metadata"] = fallback["metadata"]
#                 logger.info(f"✅ Using fallback questions: {len(fallback['questions'])} questions")
#                 return fallback
                
#         except Exception as e:
#             logger.error(f"Gemini API error: {e}")
#             fallback = generate_fallback_questions(job_title_text, candidate_skills)
#             # Store fallback questions in session
#             session_data["questions"] = fallback["questions"]
#             session_data["questions_metadata"] = fallback["metadata"]
#             return fallback
            
            
#     except Exception as e:
#         logger.error(f"Question generation error: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# def generate_fallback_questions(job_title: str, skills: str) -> dict:
#     """Generate role-specific fallback questions"""
#     job_lower = job_title.lower()
    
#     # Java Full Stack questions
#     if "java" in job_lower or "full stack" in job_lower:
#         questions = [
#             {"text": "Tell me about yourself and your experience relevant to this Java Full Stack role.", "type": "intro", "keywords": ["experience", "java", "full stack"]},
#             {"text": "Explain the difference between Spring Boot and Spring MVC. When would you use each?", "type": "technical", "keywords": ["spring boot", "spring mvc", "difference"]},
#             {"text": "How do you handle state management in React? Explain Redux or Context API.", "type": "technical", "keywords": ["react", "state management", "redux"]},
#             {"text": "Describe how you would design a REST API for a banking application.", "type": "problem-solving", "keywords": ["rest api", "design", "endpoints"]},
#             {"text": "How do you ensure data consistency in a microservices architecture?", "type": "technical", "keywords": ["microservices", "consistency", "transactions"]}
#         ]
#     # Data Science questions
#     elif "data science" in job_lower or "data scientist" in job_lower:
#         questions = [
#             {"text": "Tell me about yourself and your experience relevant to this Data Science role.", "type": "intro", "keywords": ["experience", "data science", "analytics"]},
#             {"text": "Explain the difference between supervised and unsupervised learning with examples.", "type": "technical", "keywords": ["supervised", "unsupervised", "machine learning"]},
#             {"text": "How do you handle missing data in a dataset? What are the best practices?", "type": "technical", "keywords": ["missing data", "imputation", "cleaning"]},
#             {"text": "What evaluation metrics would you use for an imbalanced classification problem?", "type": "technical", "keywords": ["precision", "recall", "f1 score", "roc auc"]},
#             {"text": "Explain the bias-variance tradeoff and how to find the right balance.", "type": "technical", "keywords": ["bias", "variance", "overfitting", "underfitting"]}
#         ]
#     # Frontend questions
#     elif "frontend" in job_lower or "front end" in job_lower:
#         questions = [
#             {"text": "Tell me about yourself and your frontend development experience.", "type": "intro", "keywords": ["experience", "frontend", "ui"]},
#             {"text": "Explain React hooks and their advantages over class components.", "type": "technical", "keywords": ["react hooks", "useState", "useEffect"]},
#             {"text": "How do you optimize a slow-loading web application?", "type": "problem-solving", "keywords": ["performance", "optimization", "lazy loading"]},
#             {"text": "What is the virtual DOM and how does it improve performance?", "type": "technical", "keywords": ["virtual dom", "react", "performance"]},
#             {"text": "How do you handle responsive design for different screen sizes?", "type": "technical", "keywords": ["responsive", "css", "media queries", "flexbox"]}
#         ]
#     # Backend questions
#     elif "backend" in job_lower or "back end" in job_lower:
#         questions = [
#             {"text": "Tell me about yourself and your backend development experience.", "type": "intro", "keywords": ["experience", "backend", "api"]},
#             {"text": "Explain database indexing and when you would use it.", "type": "technical", "keywords": ["indexing", "database", "performance"]},
#             {"text": "How do you handle authentication and authorization in a REST API?", "type": "technical", "keywords": ["jwt", "oauth", "authentication"]},
#             {"text": "What is the difference between SQL and NoSQL databases? When would you use each?", "type": "technical", "keywords": ["sql", "nosql", "database"]},
#             {"text": "Explain how you would design a rate limiting system for an API.", "type": "problem-solving", "keywords": ["rate limiting", "api", "throttling"]}
#         ]
#     # Default
#     else:
#         questions = [
#             {"text": f"Tell me about yourself and your experience relevant to this {job_title} role.", "type": "intro", "keywords": ["experience", "background", "skills"]},
#             {"text": "What technical skills do you consider your strongest and why?", "type": "technical", "keywords": ["skills", "strength", "expertise"]},
#             {"text": "Describe a challenging technical problem you solved recently.", "type": "problem-solving", "keywords": ["challenge", "solution", "approach"]},
#             {"text": "How do you stay updated with the latest technologies?", "type": "behavioral", "keywords": ["learning", "update", "technology"]},
#             {"text": f"If hired for this {job_title} role, what would be your first 30-day priority?", "type": "behavioral", "keywords": ["plan", "priority", "first"]}
#         ]
    
#     return {
#         "questions": [q["text"] for q in questions],
#         "metadata": questions,
#         "job_title": job_title,
#         "total": len(questions)
#     }

# @app.post("/evaluate-answer")
# async def evaluate_answer(
#     session_id: str = Form(...),
#     answer: str = Form(...),
#     question_index: int = Form(...)
# ):
#     """Evaluate answer with proper scoring and "I don't know" detection"""
#     try:
#         logger.info(f"📝 Evaluating answer for session: {session_id}, question: {question_index}")
#         logger.info(f"Answer: {answer[:200]}...")
        
#         if session_id not in active_sessions:
#             logger.error(f"Session not found: {session_id}")
#             return {
#                 "score": 0,
#                 "feedback": "Session expired. Please restart interview.",
#                 "is_complete": True,
#                 "next_question": None
#             }
        
#         session_data = active_sessions[session_id]
        
#         # Check if questions exist
#         if "questions" not in session_data or not session_data["questions"]:
#             logger.error("No questions found in session")
#             logger.error(f"Session data: {session_data}")
#             return {
#                 "score": 0,
#                 "feedback": "No questions found. Please restart interview.",
#                 "is_complete": True,
#                 "next_question": None
#             }
        
#         questions = session_data["questions"]
        
#         if question_index >= len(questions):
#             logger.error(f"Invalid question index: {question_index}, total: {len(questions)}")
#             return {
#                 "score": 0,
#                 "feedback": "Interview completed.",
#                 "is_complete": True,
#                 "next_question": None
#             }
        
#         current_question = questions[question_index]
        
#         # ========== IMPROVED "I DON'T KNOW" DETECTION ==========
#         dont_know_patterns = [
#             "sorry", "don't know", "no idea", "not sure", "i don't know", 
#             "i dont know", "i'm not sure", "i am not sure", "pass", 
#             "skip", "next question", "can't answer", "dont know",
#             "don't no", "dont no", "not know", "no answer",
#             "i cannot", "i can't", "unable to answer"
#         ]
        
#         answer_lower = answer.lower().strip()
#         is_dont_know = any(pattern in answer_lower for pattern in dont_know_patterns)
        
#         # Also check for very short answers (less than 5 words)
#         word_count = len(answer.split())
#         is_too_short = word_count < 5
        
#         if is_dont_know or is_too_short:
#             if is_dont_know:
#                 score = 0
#                 feedback = "You indicated you don't know the answer. Moving to next question."
#                 logger.info(f"Candidate doesn't know the answer. Score: 0")
#             else:
#                 score = 10
#                 feedback = "Your answer is too brief. Please provide more detailed responses in future questions. Moving to next question."
#                 logger.info(f"Answer too short ({word_count} words). Score: 10")
#         else:
#             # ========== PROPER SCORING BASED ON ANSWER QUALITY ==========
            
#             # 1. Length score (aim for 30-50 words)
#             if word_count >= 40:
#                 length_score = 100
#             elif word_count >= 30:
#                 length_score = 90
#             elif word_count >= 20:
#                 length_score = 70
#             elif word_count >= 10:
#                 length_score = 50
#             else:
#                 length_score = 30
            
#             # 2. Get expected keywords from metadata if available
#             questions_metadata = session_data.get("questions_metadata", [])
#             expected_keywords = []
#             if question_index < len(questions_metadata):
#                 expected_keywords = questions_metadata[question_index].get("keywords", [])
            
#             # 3. Calculate keyword match score
#             if expected_keywords:
#                 matches = 0
#                 for kw in expected_keywords:
#                     if kw.lower() in answer_lower:
#                         matches += 1
#                         logger.info(f"✅ Keyword matched: '{kw}'")
#                 keyword_score = (matches / len(expected_keywords)) * 100
#             else:
#                 # If no keywords, use relevance detection
#                 keyword_score = 60
            
#             # 4. Check for technical depth indicators
#             tech_indicators = [
#                 "spring boot", "react", "api", "database", "microservice",
#                 "cloud", "docker", "kubernetes", "java", "python", "javascript",
#                 "rest", "sql", "nosql", "git", "ci/cd", "testing", "deployment"
#             ]
#             tech_matches = sum(1 for tech in tech_indicators if tech in answer_lower)
#             tech_score = min(100, (tech_matches / 3) * 100) if tech_matches > 0 else 40
            
#             # 5. Combined score (40% length, 30% keywords, 30% technical depth)
#             score = int((length_score * 0.4) + (keyword_score * 0.3) + (tech_score * 0.3))
#             score = max(0, min(100, score))  # Clamp between 0-100
            
#             # Generate detailed feedback based on score
#             if score >= 80:
#                 feedback = "Excellent answer! Good technical depth and clarity."
#             elif score >= 65:
#                 feedback = "Good answer. Consider adding more specific examples or technical details."
#             elif score >= 50:
#                 feedback = "Fair answer. Try to elaborate more with specific experiences."
#             elif score >= 30:
#                 feedback = "Basic answer. Please provide more detailed responses with technical depth."
#             else:
#                 feedback = "Insufficient answer. Please provide more comprehensive responses."
            
#             logger.info(f"✅ Answer scored - Length: {length_score}, Keywords: {keyword_score}, Tech: {tech_score}, Final: {score}")
        
#         # Store answer
#         answer_data = {
#             "question": current_question,
#             "answer": answer,
#             "score": score,
#             "feedback": feedback,
#             "word_count": word_count,
#             "timestamp": datetime.now().isoformat()
#         }
        
#         if "answers" not in session_data:
#             session_data["answers"] = []
#         session_data["answers"].append(answer_data)
#         session_data["current_question"] = question_index + 1
        
#         is_complete = question_index + 1 >= len(questions)
#         next_question = questions[question_index + 1] if not is_complete else None
        
#         logger.info(f"📊 Answer evaluated - Score: {score}, Complete: {is_complete}")
        
#         return {
#             "score": score,
#             "feedback": feedback,
#             "is_complete": is_complete,
#             "next_question": next_question
#         }
        
#     except Exception as e:
#         logger.error(f"Answer evaluation error: {e}")
#         import traceback
#         traceback.print_exc()
#         return {
#             "score": 50,
#             "feedback": "Answer recorded. Moving to next question.",
#             "is_complete": False,
#             "next_question": None
#         }

# @app.post("/verify-identity")
# async def verify_identity(
#     session_id: str = Form(...),
#     image: str = Form(...),
#     user_id: str = Form(None)
# ):
#     """Verify candidate identity"""
#     try:
#         logger.info(f"Starting identity verification for session: {session_id}")
        
#         if ',' in image:
#             image_data = base64.b64decode(image.split(',')[1])
#         else:
#             image_data = base64.b64decode(image)
            
#         nparr = np.frombuffer(image_data, np.uint8)
#         live_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

#         if live_frame is None:
#             return {
#                 "verified": False,
#                 "confidence": 0,
#                 "message": "Could not capture clear image. Please try again with better lighting."
#             }

#         live_path = os.path.join(UPLOAD_DIR, f"{session_id}_live.jpg")
#         cv2.imwrite(live_path, live_frame)
        
#         # Find ID photo
#         id_path = None
#         if user_id:
#             extensions = ['.jpg', '.jpeg', '.png']
#             for ext in extensions:
#                 test_path = os.path.join(ID_PHOTOS_DIR, f"user_{user_id}{ext}")
#                 if os.path.exists(test_path):
#                     id_path = test_path
#                     break

#         if not id_path:
#             if os.path.exists(live_path):
#                 os.remove(live_path)
#             return {
#                 "verified": False,
#                 "confidence": 0,
#                 "message": "No ID photo found. Please upload your ID first.",
#                 "requiresUpload": True
#             }
        
#         try:
#             from deepface import DeepFace
#             result = DeepFace.verify(
#                 img1_path=id_path,
#                 img2_path=live_path,
#                 model_name="VGG-Face",
#                 enforce_detection=False,
#                 silent=True
#             )
#             verified = result['verified']
#             confidence = round((1 - result['distance']) * 100, 2)
            
#             if os.path.exists(live_path):
#                 os.remove(live_path)
            
#             return {
#                 "verified": verified,
#                 "confidence": confidence,
#                 "message": "Identity verified successfully!" if verified else "Verification failed. Please ensure good lighting."
#             }
        
#         except ImportError:
#             if os.path.exists(live_path):
#                 os.remove(live_path)
#             return {
#                 "verified": False,
#                 "confidence": 0,
#                 "message": "Face verification system not available. Please install deepface."
#             }
            
#     except Exception as e:
#         logger.error(f"Verification error: {e}")
#         return {"verified": False, "confidence": 0, "message": f"Verification failed: {str(e)}"}



# @app.post("/upload-id-photo")
# async def upload_id_photo(
#     user_id: str = Form(...),
#     file: UploadFile = File(...)
# ):
#     """Upload ID photo with Firebase support"""
#     try:
#         logger.info(f"Uploading ID photo for user: {user_id}")
        
#         contents = await file.read()
        
#         # Save temporarily
#         temp_path = os.path.join(UPLOAD_DIR, f"temp_{user_id}_{file.filename}")
#         with open(temp_path, "wb") as buffer:
#             buffer.write(contents)
        
#         # Try Firebase first
#         firebase_url = upload_to_firebase(temp_path, "id_photos", user_id)
        
#         # Clean up temp file
#         if os.path.exists(temp_path):
#             os.remove(temp_path)
        
#         if firebase_url:
#             return {
#                 "success": True,
#                 "message": "ID photo uploaded to Firebase successfully!",
#                 "url": firebase_url,
#                 "userId": user_id
#             }
#         else:
#             # Fallback to local storage
#             os.makedirs(ID_PHOTOS_DIR, exist_ok=True)
#             filename = f"user_{user_id}.jpg"
#             file_path = os.path.join(ID_PHOTOS_DIR, filename)
#             with open(file_path, "wb") as buffer:
#                 buffer.write(contents)
            
#             return {
#                 "success": True,
#                 "message": "ID photo uploaded locally",
#                 "path": file_path,
#                 "userId": user_id
#             }
        
#     except Exception as e:
#         logger.error(f"Upload error: {e}")
#         return {"success": False, "message": str(e)}

# @app.post("/analyze-video")
# async def analyze_video_frame(
#     session_id: str = Form(...),
#     frame: str = Form(...)
# ):
#     """Analyze video frame for behavioral insights"""
#     try:
#         if ',' in frame:
#             image_data = base64.b64decode(frame.split(',')[1])
#         else:
#             image_data = base64.b64decode(frame)
            
#         nparr = np.frombuffer(image_data, np.uint8)
#         frame_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
#         analysis = video_analyzer.analyze_behavior(frame_img)
#         return analysis
        
#     except Exception as e:
#         return {"emotion": "neutral", "engagement_score": 50, "status": "Analyzing"}

# @app.post("/generate-report")
# async def generate_final_report(
#     session_id: str = Form(...),
#     candidate_name: str = Form(...),
#     candidate_email: str = Form(None),
#     job_title: str = Form(None)
# ):
#     """Generate comprehensive interview report"""
#     try:
#         if session_id not in active_sessions:
#             raise HTTPException(status_code=404, detail="Session not found")
        
#         session_data = active_sessions[session_id]
#         answers = session_data.get("answers", [])
#         questions = session_data.get("questions", [])
        
#         # Calculate scores
#         if answers:
#             scores = [a["score"] for a in answers]
#             avg_score = sum(scores) / len(scores)
#             passed_questions = len([s for s in scores if s >= 50])
#         else:
#             avg_score = 0
#             passed_questions = 0
        
#         # Determine verdict
#         if avg_score >= 80:
#             verdict = "STRONG HIRE"
#             verdict_color = "success"
#             recommendation = "Highly recommended. Proceed to final round."
#         elif avg_score >= 65:
#             verdict = "HIRE"
#             verdict_color = "info"
#             recommendation = "Good candidate. Consider for the position."
#         elif avg_score >= 50:
#             verdict = "CONSIDER"
#             verdict_color = "warning"
#             recommendation = "Potential candidate. May need additional training."
#         else:
#             verdict = "REJECT"
#             verdict_color = "error"
#             recommendation = "Not recommended at this time."
        
#         # Create report
#         report = {
#             "id": f"{candidate_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
#             "candidate_name": candidate_name,
#             "candidate_email": candidate_email,
#             "job_title": job_title or session_data.get("job_title", "Not specified"),
#             "date": datetime.now().isoformat(),
#             "overall_score": round(avg_score, 2),
#             "technical_score": round(avg_score, 2),
#             "questions_answered": len(answers),
#             "total_questions": len(questions),
#             "answers": answers,
#             "strengths": [
#                 "Good communication skills" if any(a["score"] >= 70 for a in answers) else "Areas for improvement in communication",
#                 "Technical knowledge demonstrated" if any("technical" in str(a) for a in answers) else "Technical depth needs improvement"
#             ],
#             "areas_for_improvement": [
#                 "Provide more detailed answers" if any(a["word_count"] < 20 for a in answers) else "Answer quality is good",
#                 "Practice technical concepts" if avg_score < 70 else "Continue building on strong foundation"
#             ],
#             "overall_assessment": f"Candidate answered {passed_questions}/{len(questions)} questions satisfactorily with an average score of {round(avg_score, 2)}%.",
#             "verdict": verdict,
#             "verdict_color": verdict_color,
#             "recommendation": recommendation,
#             "next_steps": "HR will contact you within 3-5 business days with further updates."
#         }
        
#         # Save report
#         report_filename = f"{candidate_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
#         report_path = os.path.join(REPORTS_DIR, report_filename)
#         with open(report_path, "w") as f:
#             json.dump(report, f, indent=2)
        
#         return report
        
#     except Exception as e:
#         logger.error(f"Report generation error: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# @app.get("/reports/all")
# async def get_all_reports():
#     """Get all reports for admin dashboard"""
#     reports = []
#     if os.path.exists(REPORTS_DIR):
#         for filename in os.listdir(REPORTS_DIR):
#             if filename.endswith('.json'):
#                 with open(os.path.join(REPORTS_DIR, filename), 'r') as f:
#                     report = json.load(f)
#                     reports.append({
#                         "id": filename.replace('.json', ''),
#                         "candidate_name": report.get("candidate_name", "Unknown"),
#                         "candidate_email": report.get("candidate_email", ""),
#                         "job_title": report.get("job_title", "Not specified"),
#                         "date": report.get("date", ""),
#                         "overall_score": report.get("overall_score", 0),
#                         "verdict": report.get("verdict", "PENDING")
#                     })
#     reports.sort(key=lambda x: x.get("date", ""), reverse=True)
#     return reports

# @app.get("/reports/{candidate_name}")
# async def get_candidate_reports(candidate_name: str):
#     """Get reports for a specific candidate"""
#     reports = []
#     if os.path.exists(REPORTS_DIR):
#         for filename in os.listdir(REPORTS_DIR):
#             if filename.endswith('.json') and candidate_name.lower() in filename.lower():
#                 with open(os.path.join(REPORTS_DIR, filename), 'r') as f:
#                     report = json.load(f)
#                     reports.append(report)
#     reports.sort(key=lambda x: x.get("date", ""), reverse=True)
#     return reports

# @app.get("/report/{report_id}")
# async def get_report(report_id: str):
#     """Get specific report by ID"""
#     report_path = os.path.join(REPORTS_DIR, f"{report_id}.json")
#     if os.path.exists(report_path):
#         with open(report_path, 'r') as f:
#             return json.load(f)
#     raise HTTPException(status_code=404, detail="Report not found")


# @app.post("/speech-to-text")
# async def speech_to_text(audio: UploadFile = File(...)):
#     try:
#         print("🎤 Processing speech-to-text...")
        
#         # Save webm file
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
#             content = await audio.read()
#             tmp.write(content)
#             webm_path = tmp.name
#             print(f"📁 Webm saved: {webm_path}, size: {len(content)} bytes")

#         # Try using speech_recognition first (lighter, no FFmpeg needed)
#         try:
#             import speech_recognition as sr
            
#             # Convert webm to wav using pydub (pure Python)
#             try:
#                 from pydub import AudioSegment
#                 wav_path = webm_path.replace(".webm", ".wav")
#                 audio_segment = AudioSegment.from_file(webm_path, format="webm")
#                 audio_segment.export(wav_path, format="wav")
#                 print(f" Converted to wav using pydub")
                
#                 # Use speech_recognition
#                 recognizer = sr.Recognizer()
#                 with sr.AudioFile(wav_path) as source:
#                     recognizer.adjust_for_ambient_noise(source, duration=0.5)
#                     audio_data = recognizer.record(source)
#                     text = recognizer.recognize_google(audio_data)
                
#                 # Cleanup
#                 os.unlink(webm_path)
#                 os.unlink(wav_path)
                
#                 print(f"🎤 Transcribed (Google): '{text}'")
#                 return {"text": text}
                
#             except ImportError:
#                 print("pydub not installed, trying direct webm...")
#                 # Try direct webm with speech_recognition
#                 recognizer = sr.Recognizer()
#                 with sr.AudioFile(webm_path) as source:
#                     audio_data = recognizer.record(source)
#                     text = recognizer.recognize_google(audio_data)
#                 os.unlink(webm_path)
#                 print(f"🎤 Transcribed (direct): '{text}'")
#                 return {"text": text}
                
#         except Exception as e:
#             print(f"Speech recognition failed: {e}")
            
#             # Fallback: Try Whisper with proper ffmpeg path
#             try:
#                 import whisper
#                 import subprocess
                
#                 # Set ffmpeg path explicitly for whisper
#                 ffmpeg_path = "C:\\ffmpeg\\bin\\ffmpeg.exe"
                
#                 if os.path.exists(ffmpeg_path):
#                     # Set environment variable for ffmpeg
#                     os.environ["PATH"] = os.environ["PATH"] + os.pathsep + "C:\\ffmpeg\\bin"
                    
#                     # Convert webm to wav using explicit ffmpeg
#                     wav_path = webm_path.replace(".webm", ".wav")
#                     subprocess.run([
#                         ffmpeg_path, "-y",
#                         "-i", webm_path,
#                         "-ar", "16000",
#                         "-ac", "1",
#                         wav_path
#                     ], capture_output=True, check=True)
                    
#                     # Load whisper model
#                     model = whisper.load_model("base")
#                     result = model.transcribe(wav_path)
#                     text = result.get("text", "").strip()
                    
#                     # Cleanup
#                     os.unlink(webm_path)
#                     os.unlink(wav_path)
                    
#                     print(f"🎤 Transcribed (Whisper): '{text}'")
#                     return {"text": text}
#                 else:
#                     raise Exception("FFmpeg not found")
                    
#             except Exception as whisper_error:
#                 print(f"Whisper transcription failed: {whisper_error}")
#                 os.unlink(webm_path)
#                 return {"text": ""}
        
#     except Exception as e:
#         print(f"Speech error: {e}")
#         import traceback
#         traceback.print_exc()
#         return {"text": ""}
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)


import os
# Configure environment variables to limit ML thread allocation and memory overhead
# (Must be done before importing any ML libraries)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TF_NUM_INTRAOP_THREADS"] = "1"
os.environ["TF_NUM_INTEROP_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"

import shutil, uuid, cv2, json
import base64
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from typing import Optional, List
from datetime import datetime
import logging
import re
import time
# import whisper
import tempfile
import subprocess

# Import your ML modules
from ml_core.resume_parser import ResumeAnalyzer
from ml_core.engine import RecruitmentEngine
from ml_core.report_generator import ReportGenerator
from ml_core.video_analyzer import VideoAnalyzer

from dotenv import load_dotenv
load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MakeItHired AI Service")


ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", 
    "http://localhost:5173,"
    "http://localhost:8081,"
    "https://make-it-hire-frontend.onrender.com,"
    "https://make-it-hire-backend.onrender.com"
).split(",")

# if "https://make-it-hire-frontend.onrender.com" not in ALLOWED_ORIGINS:
#     ALLOWED_ORIGINS.append("https://make-it-hire-frontend.onrender.com")


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ML components
analyzer = ResumeAnalyzer()
engine = RecruitmentEngine()
video_analyzer = VideoAnalyzer()

# model = whisper.load_model("base")

UPLOAD_DIR = "data/uploads"
ID_PHOTOS_DIR = "data/id_photos"
REPORTS_DIR = "data/reports"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(ID_PHOTOS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Store active sessions
active_sessions = {}


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

# firebase_initialized = False

# ========== ADD UPLOAD FUNCTION HERE ==========
# def upload_to_firebase(file_path, folder, user_id):
#     """Upload file to Firebase Storage (Disabled, fallback to local storage)"""
#     return None
    
# whisper_model = None

# def get_whisper_model():
#     global whisper_model
#     if whisper_model is None:
#         print("🔄 Loading Whisper model...")
#         whisper_model = whisper.load_model("base")
#         print("✅ Whisper model loaded")
#     return whisper_model

# ==================== HELPER FUNCTIONS ====================

def partition_resume(text: str) -> dict:
    """Intelligently partition the resume text into sections using regex headers."""
    text_lower = text.lower()
    
    # Define header keywords for each section
    section_patterns = {
        "skills": [
            r'\btechnical skills\b', r'\bcore competencies\b', r'\bkey skills\b',
            r'\bskills & tools\b', r'\btechnical expertise\b', r'\bskills\b', 
            r'\btechnologies\b', r'\bexpertise\b'
        ],
        "experience": [
            r'\bwork experience\b', r'\bprofessional experience\b', r'\bemployment history\b',
            r'\bwork history\b', r'\bcareer history\b', r'\bexperience\b', r'\bemployment\b'
        ],
        "education": [
            r'\beducational background\b', r'\bacademic profile\b', r'\bacademic qualification\b',
            r'\beducational qualification\b', r'\beducation\b', r'\bacademics\b', r'\bqualifications\b'
        ],
        "projects": [
            r'\bacademic projects\b', r'\bkey projects\b', r'\bpersonal projects\b',
            r'\brecent projects\b', r'\btechnical projects\b', r'\bprojects\b'
        ]
    }
    
    found_headers = []
    
    for section, patterns in section_patterns.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text_lower):
                start, end = match.span()
                # Heuristic: Check if the match is at the start of a line or preceded by newline/spaces
                before = text_lower[max(0, start - 10):start]
                if start == 0 or '\n' in before or re.match(r'^\s*$', before):
                    found_headers.append({
                        "section": section,
                        "start": start,
                        "end": end
                    })
                    break # Use the first good header match for this section
                    
    found_headers.sort(key=lambda x: x["start"])
    
    sections = {
        "skills": "",
        "experience": "",
        "education": "",
        "projects": "",
        "contact_info": "",
        "other": ""
    }
    
    if not found_headers:
        sections["other"] = text
        return sections
        
    # Text before the first header is contact_info / summary
    first_start = found_headers[0]["start"]
    sections["contact_info"] = text[:first_start]
    
    for i, header in enumerate(found_headers):
        current_section = header["section"]
        start_idx = header["end"]
        end_idx = found_headers[i+1]["start"] if i + 1 < len(found_headers) else len(text)
        sections[current_section] += " " + text[start_idx:end_idx]
        
    return {k: v.strip() for k, v in sections.items()}

def extract_experience_years_improved(text: str) -> float:
    """Extract years of experience from explicit patterns and date ranges."""
    # Look for explicit patterns like "X+ years", "X years of experience"
    patterns = [
        r'(\d+(?:\.\d+)?)\+?\s*years?\s+(?:of\s+)?experience',
        r'experience\s+(?:of\s+)?(\d+(?:\.\d+)?)\+?\s*years?',
        r'(\d+(?:\.\d+)?)\+?\s*years?\s+experience',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
                
    # Search for year ranges (e.g. 2018 - 2022 or 2020 to Present)
    # Match pairs of years or year-to-present
    range_regex = r'\b(19\d{2}|20\d{2})\s*(?:-|to|until)\s*(Present|Current|Now|\b(?:19|20)\d{2}\b)'
    ranges = re.findall(range_regex, text, re.IGNORECASE)
    
    current_year = datetime.now().year
    total_years = 0.0
    
    if ranges:
        for start_yr, end_yr in ranges:
            try:
                start = int(start_yr)
                if end_yr.lower() in ['present', 'current', 'now']:
                    end = current_year
                else:
                    end = int(end_yr)
                duration = end - start
                if 0 < duration <= 40: # Ignore invalid spans
                    total_years += duration
            except ValueError:
                pass
                
    if total_years > 0:
        return min(total_years, 20.0)
        
    # Fallback to simple year logic
    year_pattern = r'\b(19\d{2}|20\d{2})\b'
    years = [int(y) for y in re.findall(year_pattern, text)]
    if years:
        min_year = min(years)
        max_year = max(years)
        diff = max_year - min_year
        if 0 < diff <= 15:
            return float(diff)
            
    return 0.0

def extract_experience_years(text: str) -> float:
    """Wrapper function to extract experience years"""
    sections = partition_resume(text)
    exp_text = sections.get("experience", "")
    if exp_text:
        return extract_experience_years_improved(exp_text)
    return extract_experience_years_improved(text)

def calculate_resume_score_detailed(text: str, skills: list) -> dict:
    """Calculate resume score based on various weighted factors, out of 100."""
    if not text or not text.strip():
        return {
            "total": 35,
            "breakdown": {
                "contact_info": 5,
                "education": 10,
                "experience": 10,
                "skills": 5,
                "projects": 3,
                "formatting_length": 2
            }
        }
        
    sections = partition_resume(text)
    
    # 1. Contact Info (Max 10)
    contact_score = 0
    # Email
    if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text):
        contact_score += 3
    elif "@" in text:
        contact_score += 2
        
    # Phone number
    phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\b\d{10}\b'
    if re.search(phone_pattern, text):
        contact_score += 3
    elif any(char.isdigit() for char in text) and len(text) > 9:
        contact_score += 2
        
    # LinkedIn
    if "linkedin" in text.lower():
        contact_score += 2
        
    # GitHub or Portfolio
    if "github" in text.lower() or "portfolio" in text.lower() or "personal website" in text.lower() or "website" in text.lower():
        contact_score += 2
        
    contact_score = min(contact_score, 10)
    
    # 2. Education (Max 15)
    education_score = 0
    education_text = sections.get("education", "")
    
    # Degree patterns
    phd_pat = r'\bph\.?d\.?\b|doctor of philosophy'
    master_pat = r'\bm\.?s\.?\b|master|m\.?tech\b|m\.?b\.?a\.?\b|m\.?c\.?a\.?\b'
    bachelor_pat = r'\bb\.?s\.?\b|bachelor|b\.?tech\b|b\.?e\.?\b|b\.?c\.?a\.?\b|b\.?b\.?a\.?\b'
    associate_pat = r'\bassociate\b|\bdiploma\b'
    
    search_text = education_text if education_text else text
    
    degree_points = 0
    if re.search(phd_pat, search_text, re.IGNORECASE):
        degree_points = 10
    elif re.search(master_pat, search_text, re.IGNORECASE):
        degree_points = 8
    elif re.search(bachelor_pat, search_text, re.IGNORECASE):
        degree_points = 6
    elif re.search(associate_pat, search_text, re.IGNORECASE):
        degree_points = 4
    elif "degree" in search_text.lower() or "university" in search_text.lower() or "college" in search_text.lower():
        degree_points = 4
        
    education_score += degree_points
    
    # Academic institutions & Major keywords
    academic_inst_pat = r'\buniversity\b|\bcollege\b|\binstitute\b|\bacademy\b|\bschool\b'
    if re.search(academic_inst_pat, search_text, re.IGNORECASE):
        education_score += 3
        
    major_pat = r'\bcomputer science\b|\bengineering\b|\binformation technology\b|\bmathematics\b|\bbusiness\b|\bfinance\b|\bscience\b|\bmajor\b'
    if re.search(major_pat, search_text, re.IGNORECASE):
        education_score += 2
        
    education_score = min(education_score, 15)
    
    # 3. Experience (Max 20)
    exp_text = sections.get("experience", "")
    experience_years = extract_experience_years_improved(exp_text if exp_text else text)
    experience_score = 0
    
    # Base score on years of experience
    if experience_years >= 5:
        experience_score += 16
    elif experience_years >= 3:
        experience_score += 12
    elif experience_years >= 1:
        experience_score += 8
    elif experience_years > 0:
        experience_score += 4
        
    # Quality / relevance keywords in experience section
    action_verbs = ['developed', 'designed', 'managed', 'led', 'implemented', 'optimized', 'delivered', 'collaborated', 'created', 'built']
    exp_text = sections.get("experience", "") if sections.get("experience", "") else text
    verb_count = sum(1 for verb in action_verbs if verb in exp_text.lower())
    
    if verb_count >= 4:
        experience_score += 4
    elif verb_count >= 2:
        experience_score += 2
    elif verb_count >= 1:
        experience_score += 1
        
    experience_score = min(experience_score, 20)
    
    # 4. Skills (Max 25)
    skills_score = 0
    if skills:
        # Each unique skill is worth 3 points, up to 18 points (requires 6 skills)
        skills_score += min(len(skills) * 3, 18)
        
        # Advanced / specialized skills add extra weight, up to 7 points (2 points per advanced skill)
        advanced_techs = ['aws', 'docker', 'kubernetes', 'cloud', 'devops', 'ci/cd', 'cicd', 'microservices', 'system design', 'machine learning', 'tensorflow', 'pytorch', 'django', 'spring boot']
        adv_count = sum(1 for tech in advanced_techs if tech in [s.lower() for s in skills])
        skills_score += min(adv_count * 2, 7)
        
    skills_score = min(skills_score, 25)
    
    # 5. Projects (Max 15)
    projects_score = 0
    projects_text = sections.get("projects", "")
    
    if projects_text:
        projects_score += 5  # Section presence
        
        # Count bullets or paragraphs
        bullets = len(re.findall(r'^\s*[-*•]\s+', projects_text, re.MULTILINE))
        if bullets >= 4:
            projects_score += 5
        elif bullets >= 2:
            projects_score += 3
        else:
            words = len(projects_text.split())
            if words > 100:
                projects_score += 5
            elif words > 50:
                projects_score += 3
            elif words > 15:
                projects_score += 1
                
        # Count technical terms inside project text
        techs_in_projects = sum(1 for skill in skills if skill in projects_text.lower())
        projects_score += min(techs_in_projects * 1.5, 5.0)
        
    elif "project" in text.lower():
        # Fallback if section wasn't clearly separated
        projects_score = 5
        project_mentions = len(re.findall(r'\bproject\b', text, re.IGNORECASE))
        if project_mentions >= 3:
            projects_score += 5
        elif project_mentions >= 1:
            projects_score += 3
        projects_score += min(len(skills) * 0.5, 5.0)
        
    projects_score = min(round(projects_score), 15)
    
    # 6. Formatting / Content Quality (Max 15)
    # Word count
    word_count = len(text.split())
    if 300 <= word_count <= 800:
        length_score = 5
    elif 150 <= word_count < 300:
        length_score = 3
    elif word_count > 800:
        length_score = 4
    else:
        length_score = 1
        
    # Formatting (headers found)
    sections_found = sum(1 for sec, val in sections.items() if val and sec not in ["other", "contact_info"])
    bullet_points = len(re.findall(r'^\s*[-*•]\s+', text, re.MULTILINE))
    
    formatting_score = min(sections_found * 1.25, 4.0)
    if bullet_points >= 8:
        formatting_score += 1.0
    elif bullet_points >= 4:
        formatting_score += 0.5
        
    # Keyword density
    industry_keywords = [
        "develop", "software", "design", "manage", "team", "engineer", "build", 
        "solution", "system", "code", "programming", "implement", "deploy", 
        "test", "analysis", "data", "cloud", "project", "technology", "agile"
    ]
    keyword_count = 0
    text_lower = text.lower()
    for kw in industry_keywords:
        keyword_count += text_lower.count(kw)
        
    if keyword_count >= 15:
        density_score = 5
    elif keyword_count >= 10:
        density_score = 4
    elif keyword_count >= 5:
        density_score = 2.5
    elif keyword_count >= 2:
        density_score = 1
    else:
        density_score = 0
        
    formatting_length_score = round(length_score + formatting_score + density_score)
    formatting_length_score = min(formatting_length_score, 15)
    
    # Total
    total_score = contact_score + education_score + experience_score + skills_score + projects_score + formatting_length_score
    total_score = min(total_score, 100)
    
    return {
        "total": total_score,
        "breakdown": {
            "contact_info": contact_score,
            "education": education_score,
            "experience": experience_score,
            "skills": skills_score,
            "projects": projects_score,
            "formatting_length": formatting_length_score
        }
    }

def calculate_resume_score(text: str, skills: list) -> int:
    """Calculate resume score based on various factors"""
    return calculate_resume_score_detailed(text, skills)["total"]

def generate_recommendations(text: str, skills: list, experience: float) -> list:
    """Generate resume improvement recommendations based on computed breakdown."""
    score_details = calculate_resume_score_detailed(text, skills)
    breakdown = score_details["breakdown"]
    
    recommendations = []
    
    # Contact Info
    if breakdown.get("contact_info", 0) < 7:
        missing_contact = []
        if "@" not in text:
            missing_contact.append("email address")
        if not (any(char.isdigit() for char in text) and len(text) > 9):
            missing_contact.append("phone number")
        if "linkedin" not in text.lower():
            missing_contact.append("LinkedIn profile link")
        if missing_contact:
            recommendations.append(f"Add missing contact details to header: {', '.join(missing_contact)}.")
            
    # Skills
    if len(skills) < 5:
        recommendations.append("Include more technical skills relevant to your target jobs. Aim for at least 6-8 core technologies.")
    elif breakdown.get("skills", 0) < 18:
        recommendations.append("Differentiate your skills section by grouping them into categories (e.g. Languages, Frameworks, Tools).")
        
    # Experience
    if experience < 1:
        recommendations.append("Provide details on your professional experience or internships, highlighting roles and key tasks.")
    elif breakdown.get("experience", 0) < 15:
        recommendations.append("Use strong action verbs (e.g., 'led', 'developed', 'optimized') in your experience descriptions to show impact.")
        
    # Education
    if breakdown.get("education", 0) < 10:
        recommendations.append("Make sure your educational qualifications (degree name, major, university, graduation year) are clearly listed.")
        
    # Projects
    if breakdown.get("projects", 0) < 8:
        recommendations.append("Add a 'Projects' section highlighting personal or academic coding projects with the technologies used.")
    elif breakdown.get("projects", 0) < 13:
        recommendations.append("Describe your projects using the STAR method (Situation, Task, Action, Result) and mention specific tech stack details.")
        
    # Content Quality & Formatting
    word_count = len(text.split())
    if word_count < 200:
        recommendations.append("Expand the content of your resume. An ideal resume has between 300 and 800 words of dense, relevant text.")
    elif word_count > 900:
        recommendations.append("Your resume might be too lengthy. Try to condense your descriptions to keep it concise and under 2 pages.")
        
    bullet_points = len(re.findall(r'^\s*[-*•]\s+', text, re.MULTILINE))
    if bullet_points < 5:
        recommendations.append("Use bullet points instead of long paragraphs to make your experience and project descriptions easy to scan.")
        
    if not recommendations:
        recommendations.append("Your resume is well-structured! Consider tailoring it with specific keywords from the job description for each application.")
        
    return recommendations

# ==================== ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "service": "MakeItHired AI Service",
        "status": "active",
        "features": ["resume_parsing", "skill_extraction", "semantic_matching", "biometric_verification", "video_analysis"]
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    """Parse resume and extract skills, experience, and generate score"""
    session_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{session_id}.pdf")
    
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        resume_text = analyzer.extract_text(file_path)
        
        # If extraction completely fails, handle it gracefully
        if not resume_text or not resume_text.strip():
            logger.warning("Empty text extracted from PDF. Using metadata/filename fallback.")
            resume_text = f"Resume filename: {file.filename}. Please upload a text-based PDF."
            
        skills = analyzer.extract_skills(resume_text)
        score_details = calculate_resume_score_detailed(resume_text, skills)
        resume_score = score_details["total"]
        score_breakdown = score_details["breakdown"]
        
        experience_years = extract_experience_years(resume_text)
        recommendations = generate_recommendations(resume_text, skills, experience_years)
        
        # Check if we are in fallback text mode
        warning_msg = None
        if "Please upload a text-based PDF" in resume_text:
            warning_msg = "We had trouble reading text from your PDF. The score is a baseline estimate. Please ensure it is a text PDF rather than a scanned image."
            recommendations.append("Ensure your PDF contains selectable text (not scanned images) to get full analysis.")
            
        result = {
            "session_id": session_id,
            "resume_score": resume_score,
            "score_breakdown": score_breakdown,
            "skills_found": skills,
            "experience_years": experience_years,
            "recommendations": recommendations,
            "word_count": len(resume_text.split()),
            "filename": file.filename,
            "has_email": "@" in resume_text,
            "has_phone": any(char.isdigit() for char in resume_text) and len(resume_text) > 9,
            "has_education": any(k in resume_text.lower() for k in ['bachelor', 'master', 'phd', 'degree']),
            "has_project": "project" in resume_text.lower()
        }
        if warning_msg:
            result["warning"] = warning_msg
        
        active_sessions[session_id] = {
            "resume_text": resume_text,
            "skills": skills,
            "resume_score": resume_score,
            "score_breakdown": score_breakdown,
            "timestamp": datetime.now().isoformat()
        }
        
        return result
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Parse resume error: {e}")
        import traceback
        traceback.print_exc()
        
        # Robust fallback response in case of system errors
        fallback_details = {
            "session_id": session_id,
            "resume_score": 45,
            "score_breakdown": {
                "contact_info": 5,
                "education": 10,
                "experience": 10,
                "skills": 10,
                "projects": 5,
                "formatting_length": 5
            },
            "skills_found": [],
            "experience_years": 0.0,
            "recommendations": [
                "System encountered an error during parsing. Returning baseline estimate.",
                f"Error detail: {str(e)}"
            ],
            "word_count": 0,
            "filename": file.filename,
            "warning": f"AI Parsing error: {str(e)}. Using fallback score."
        }
        return fallback_details
    finally:
        # Clean up temp file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up temp file: {file_path}")
            except Exception as clean_ex:
                logger.error(f"Failed to delete temp file {file_path}: {clean_ex}")

@app.post("/generate-questions")
async def generate_interview_questions(
    session_id: str = Form(...),
    job_title: str = Form(None),
    job_description: str = Form(None),
    resume_skills: str = Form(None)
):
    """Generate JOB-SPECIFIC interview questions based on role"""
    try:
        if session_id not in active_sessions:
            active_sessions[session_id] = {}
            logger.info(f"Created new session: {session_id}")
        
        session_data = active_sessions[session_id]
        
        # Get job title - this is the key for role-based questions
        job_title_text = job_title or session_data.get("job_title", "Software Developer")
        job_desc_text = job_description or session_data.get("job_description", "")
        
        # Get skills from resume
        candidate_skills = resume_skills or session_data.get("skills", "")
        if not candidate_skills or candidate_skills.strip() == "":
            candidate_skills = "Full Stack Development, Python, Java, JavaScript"
        
        # Store in session
        session_data["job_title"] = job_title_text
        session_data["job_description"] = job_desc_text
        session_data["skills"] = candidate_skills
        
        logger.info(f"Generating questions for role: {job_title_text}")
        
        # Create role-specific prompt for Gemini
        prompt = f"""
        You are a technical interviewer for a {job_title_text} position.
        
        **IMPORTANT: Generate questions SPECIFIC to this role: {job_title_text}**
        
        Candidate's Skills: {candidate_skills}
        
        Generate EXACTLY 5 interview questions:
        
        1. FIRST QUESTION MUST BE: "Tell me about yourself and your experience relevant to this {job_title_text} role."
        
        2. For remaining 4 questions, make them SPECIFIC to {job_title_text}:
           - If Java Full Stack: Ask about Spring Boot, React, REST APIs, databases
           - If Data Science: Ask about Python, pandas, machine learning algorithms, data visualization
           - If Frontend: Ask about React/Vue, JavaScript, CSS, state management
           - If Backend: Ask about APIs, databases, microservices, authentication
        
        Format response as JSON:
        {{
            "questions": [
                {{"text": "question text", "type": "intro/technical/problem-solving/behavioral", "keywords": ["keyword1", "keyword2"]}}
            ]
        }}
        """
        
        try:
            response = requests.post(
                GEMINI_URL,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 2048,
                        "responseMimeType": "application/json"
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                questions_text = result['candidates'][0]['content']['parts'][0]['text']
                questions_data = json.loads(questions_text)
                questions_list = [q["text"] for q in questions_data["questions"]]
                questions_metadata = questions_data["questions"]
                
                session_data["questions"] = questions_list
                session_data["questions_metadata"] = questions_metadata
                session_data["current_question"] = 0
                
                logger.info(f"Generated {len(questions_list)} questions for {job_title_text}")
                
                return {
                    "questions": questions_list,
                    "metadata": questions_metadata,
                    "job_title": job_title_text,
                    "total": len(questions_list)
                }
            else:
                fallback = generate_fallback_questions(job_title_text, candidate_skills)
                session_data["questions"] = fallback["questions"]
                session_data["questions_metadata"] = fallback["metadata"]
                logger.info(f"✅ Using fallback questions: {len(fallback['questions'])} questions")
                return fallback
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            fallback = generate_fallback_questions(job_title_text, candidate_skills)
            # Store fallback questions in session
            session_data["questions"] = fallback["questions"]
            session_data["questions_metadata"] = fallback["metadata"]
            return fallback
            
            
    except Exception as e:
        logger.error(f"Question generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_fallback_questions(job_title: str, skills: str) -> dict:
    """Generate role-specific fallback questions"""
    job_lower = job_title.lower()
    
    # Java Full Stack questions
    if "java" in job_lower or "full stack" in job_lower:
        questions = [
            {"text": "Tell me about yourself and your experience relevant to this Java Full Stack role.", "type": "intro", "keywords": ["experience", "java", "full stack"]},
            {"text": "Explain the difference between Spring Boot and Spring MVC. When would you use each?", "type": "technical", "keywords": ["spring boot", "spring mvc", "difference"]},
            {"text": "How do you handle state management in React? Explain Redux or Context API.", "type": "technical", "keywords": ["react", "state management", "redux"]},
            {"text": "Describe how you would design a REST API for a banking application.", "type": "problem-solving", "keywords": ["rest api", "design", "endpoints"]},
            {"text": "How do you ensure data consistency in a microservices architecture?", "type": "technical", "keywords": ["microservices", "consistency", "transactions"]}
        ]
    # Data Science questions
    elif "data science" in job_lower or "data scientist" in job_lower:
        questions = [
            {"text": "Tell me about yourself and your experience relevant to this Data Science role.", "type": "intro", "keywords": ["experience", "data science", "analytics"]},
            {"text": "Explain the difference between supervised and unsupervised learning with examples.", "type": "technical", "keywords": ["supervised", "unsupervised", "machine learning"]},
            {"text": "How do you handle missing data in a dataset? What are the best practices?", "type": "technical", "keywords": ["missing data", "imputation", "cleaning"]},
            {"text": "What evaluation metrics would you use for an imbalanced classification problem?", "type": "technical", "keywords": ["precision", "recall", "f1 score", "roc auc"]},
            {"text": "Explain the bias-variance tradeoff and how to find the right balance.", "type": "technical", "keywords": ["bias", "variance", "overfitting", "underfitting"]}
        ]
    # Frontend questions
    elif "frontend" in job_lower or "front end" in job_lower:
        questions = [
            {"text": "Tell me about yourself and your frontend development experience.", "type": "intro", "keywords": ["experience", "frontend", "ui"]},
            {"text": "Explain React hooks and their advantages over class components.", "type": "technical", "keywords": ["react hooks", "useState", "useEffect"]},
            {"text": "How do you optimize a slow-loading web application?", "type": "problem-solving", "keywords": ["performance", "optimization", "lazy loading"]},
            {"text": "What is the virtual DOM and how does it improve performance?", "type": "technical", "keywords": ["virtual dom", "react", "performance"]},
            {"text": "How do you handle responsive design for different screen sizes?", "type": "technical", "keywords": ["responsive", "css", "media queries", "flexbox"]}
        ]
    # Backend questions
    elif "backend" in job_lower or "back end" in job_lower:
        questions = [
            {"text": "Tell me about yourself and your backend development experience.", "type": "intro", "keywords": ["experience", "backend", "api"]},
            {"text": "Explain database indexing and when you would use it.", "type": "technical", "keywords": ["indexing", "database", "performance"]},
            {"text": "How do you handle authentication and authorization in a REST API?", "type": "technical", "keywords": ["jwt", "oauth", "authentication"]},
            {"text": "What is the difference between SQL and NoSQL databases? When would you use each?", "type": "technical", "keywords": ["sql", "nosql", "database"]},
            {"text": "Explain how you would design a rate limiting system for an API.", "type": "problem-solving", "keywords": ["rate limiting", "api", "throttling"]}
        ]
    # Default
    else:
        questions = [
            {"text": f"Tell me about yourself and your experience relevant to this {job_title} role.", "type": "intro", "keywords": ["experience", "background", "skills"]},
            {"text": "What technical skills do you consider your strongest and why?", "type": "technical", "keywords": ["skills", "strength", "expertise"]},
            {"text": "Describe a challenging technical problem you solved recently.", "type": "problem-solving", "keywords": ["challenge", "solution", "approach"]},
            {"text": "How do you stay updated with the latest technologies?", "type": "behavioral", "keywords": ["learning", "update", "technology"]},
            {"text": f"If hired for this {job_title} role, what would be your first 30-day priority?", "type": "behavioral", "keywords": ["plan", "priority", "first"]}
        ]
    
    return {
        "questions": [q["text"] for q in questions],
        "metadata": questions,
        "job_title": job_title,
        "total": len(questions)
    }

@app.post("/evaluate-answer")
async def evaluate_answer(
    session_id: str = Form(...),
    answer: str = Form(...),
    question_index: int = Form(...)
):
    """Evaluate answer with proper scoring and "I don't know" detection"""
    try:
        logger.info(f"📝 Evaluating answer for session: {session_id}, question: {question_index}")
        logger.info(f"Answer: {answer[:200]}...")
        
        if session_id not in active_sessions:
            logger.error(f"Session not found: {session_id}")
            return {
                "score": 0,
                "feedback": "Session expired. Please restart interview.",
                "is_complete": True,
                "next_question": None
            }
        
        session_data = active_sessions[session_id]
        
        # Check if questions exist
        if "questions" not in session_data or not session_data["questions"]:
            logger.error("No questions found in session")
            logger.error(f"Session data: {session_data}")
            return {
                "score": 0,
                "feedback": "No questions found. Please restart interview.",
                "is_complete": True,
                "next_question": None
            }
        
        questions = session_data["questions"]
        
        if question_index >= len(questions):
            logger.error(f"Invalid question index: {question_index}, total: {len(questions)}")
            return {
                "score": 0,
                "feedback": "Interview completed.",
                "is_complete": True,
                "next_question": None
            }
        
        current_question = questions[question_index]
        
        # ========== IMPROVED "I DON'T KNOW" DETECTION ==========
        dont_know_patterns = [
            "sorry", "don't know", "no idea", "not sure", "i don't know", 
            "i dont know", "i'm not sure", "i am not sure", "pass", 
            "skip", "next question", "can't answer", "dont know",
            "don't no", "dont no", "not know", "no answer",
            "i cannot", "i can't", "unable to answer"
        ]
        
        answer_lower = answer.lower().strip()
        is_dont_know = any(pattern in answer_lower for pattern in dont_know_patterns)
        
        # Also check for very short answers (less than 5 words)
        word_count = len(answer.split())
        is_too_short = word_count < 5
        
        if is_dont_know or is_too_short:
            if is_dont_know:
                score = 0
                feedback = "You indicated you don't know the answer. Moving to next question."
                logger.info(f"Candidate doesn't know the answer. Score: 0")
            else:
                score = 10
                feedback = "Your answer is too brief. Please provide more detailed responses in future questions. Moving to next question."
                logger.info(f"Answer too short ({word_count} words). Score: 10")
        else:
            # ========== PROPER SCORING BASED ON ANSWER QUALITY ==========
            
            # 1. Length score (aim for 30-50 words)
            if word_count >= 40:
                length_score = 100
            elif word_count >= 30:
                length_score = 90
            elif word_count >= 20:
                length_score = 70
            elif word_count >= 10:
                length_score = 50
            else:
                length_score = 30
            
            # 2. Get expected keywords from metadata if available
            questions_metadata = session_data.get("questions_metadata", [])
            expected_keywords = []
            if question_index < len(questions_metadata):
                expected_keywords = questions_metadata[question_index].get("keywords", [])
            
            # 3. Calculate keyword match score
            if expected_keywords:
                matches = 0
                for kw in expected_keywords:
                    if kw.lower() in answer_lower:
                        matches += 1
                        logger.info(f"✅ Keyword matched: '{kw}'")
                keyword_score = (matches / len(expected_keywords)) * 100
            else:
                # If no keywords, use relevance detection
                keyword_score = 60
            
            # 4. Check for technical depth indicators
            tech_indicators = [
                "spring boot", "react", "api", "database", "microservice",
                "cloud", "docker", "kubernetes", "java", "python", "javascript",
                "rest", "sql", "nosql", "git", "ci/cd", "testing", "deployment"
            ]
            tech_matches = sum(1 for tech in tech_indicators if tech in answer_lower)
            tech_score = min(100, (tech_matches / 3) * 100) if tech_matches > 0 else 40
            
            # 5. Combined score (40% length, 30% keywords, 30% technical depth)
            score = int((length_score * 0.4) + (keyword_score * 0.3) + (tech_score * 0.3))
            score = max(0, min(100, score))  # Clamp between 0-100
            
            # Generate detailed feedback based on score
            if score >= 80:
                feedback = "Excellent answer! Good technical depth and clarity."
            elif score >= 65:
                feedback = "Good answer. Consider adding more specific examples or technical details."
            elif score >= 50:
                feedback = "Fair answer. Try to elaborate more with specific experiences."
            elif score >= 30:
                feedback = "Basic answer. Please provide more detailed responses with technical depth."
            else:
                feedback = "Insufficient answer. Please provide more comprehensive responses."
            
            logger.info(f"✅ Answer scored - Length: {length_score}, Keywords: {keyword_score}, Tech: {tech_score}, Final: {score}")
        
        # Store answer
        answer_data = {
            "question": current_question,
            "answer": answer,
            "score": score,
            "feedback": feedback,
            "word_count": word_count,
            "timestamp": datetime.now().isoformat()
        }
        
        if "answers" not in session_data:
            session_data["answers"] = []
        session_data["answers"].append(answer_data)
        session_data["current_question"] = question_index + 1
        
        is_complete = question_index + 1 >= len(questions)
        next_question = questions[question_index + 1] if not is_complete else None
        
        logger.info(f"📊 Answer evaluated - Score: {score}, Complete: {is_complete}")
        
        return {
            "score": score,
            "feedback": feedback,
            "is_complete": is_complete,
            "next_question": next_question
        }
        
    except Exception as e:
        logger.error(f"Answer evaluation error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "score": 50,
            "feedback": "Answer recorded. Moving to next question.",
            "is_complete": False,
            "next_question": None
        }

@app.post("/verify-identity")
async def verify_identity(
    session_id: str = Form(...),
    image: str = Form(...),
    user_id: str = Form(None)
):
    """Verify candidate identity"""
    try:
        logger.info(f"Starting identity verification for session: {session_id}")
        
        if ',' in image:
            image_data = base64.b64decode(image.split(',')[1])
        else:
            image_data = base64.b64decode(image)
            
        nparr = np.frombuffer(image_data, np.uint8)
        live_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if live_frame is None:
            return {
                "verified": False,
                "confidence": 0,
                "message": "Could not capture clear image. Please try again with better lighting."
            }

        live_path = os.path.join(UPLOAD_DIR, f"{session_id}_live.jpg")
        cv2.imwrite(live_path, live_frame)
        
        # Find ID photo
        id_path = None
        if user_id:
            extensions = ['.jpg', '.jpeg', '.png']
            for ext in extensions:
                test_path = os.path.join(ID_PHOTOS_DIR, f"user_{user_id}{ext}")
                if os.path.exists(test_path):
                    id_path = test_path
                    break

        if not id_path:
            if os.path.exists(live_path):
                os.remove(live_path)
            return {
                "verified": False,
                "confidence": 0,
                "message": "No ID photo found. Please upload your ID first.",
                "requiresUpload": True
            }
        
        try:
            from deepface import DeepFace
            result = DeepFace.verify(
                img1_path=id_path,
                img2_path=live_path,
                model_name="VGG-Face",
                enforce_detection=False,
                silent=True
            )
            verified = result['verified']
            confidence = round((1 - result['distance']) * 100, 2)
            
            if os.path.exists(live_path):
                os.remove(live_path)
            
            return {
                "verified": verified,
                "confidence": confidence,
                "message": "Identity verified successfully!" if verified else "Verification failed. Please ensure good lighting."
            }
        
        except ImportError:
            if os.path.exists(live_path):
                os.remove(live_path)
            return {
                "verified": False,
                "confidence": 0,
                "message": "Face verification system not available. Please install deepface."
            }
            
    except Exception as e:
        logger.error(f"Verification error: {e}")
        return {"verified": False, "confidence": 0, "message": f"Verification failed: {str(e)}"}



@app.post("/upload-id-photo")
async def upload_id_photo(
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload ID photo with Firebase support"""
    try:
        logger.info(f"Uploading ID photo for user: {user_id}")
        
        contents = await file.read()
        
        # Save temporarily
        temp_path = os.path.join(UPLOAD_DIR, f"temp_{user_id}_{file.filename}")
        with open(temp_path, "wb") as buffer:
            buffer.write(contents)
        
        # Try Firebase first
        firebase_url = upload_to_firebase(temp_path, "id_photos", user_id)
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        if firebase_url:
            return {
                "success": True,
                "message": "ID photo uploaded to Firebase successfully!",
                "url": firebase_url,
                "userId": user_id
            }
        else:
            # Fallback to local storage
            os.makedirs(ID_PHOTOS_DIR, exist_ok=True)
            filename = f"user_{user_id}.jpg"
            file_path = os.path.join(ID_PHOTOS_DIR, filename)
            with open(file_path, "wb") as buffer:
                buffer.write(contents)
            
            return {
                "success": True,
                "message": "ID photo uploaded locally",
                "path": file_path,
                "userId": user_id
            }
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return {"success": False, "message": str(e)}

@app.post("/analyze-video")
async def analyze_video_frame(
    session_id: str = Form(...),
    frame: str = Form(...)
):
    """Analyze video frame for behavioral insights"""
    try:
        if ',' in frame:
            image_data = base64.b64decode(frame.split(',')[1])
        else:
            image_data = base64.b64decode(frame)
            
        nparr = np.frombuffer(image_data, np.uint8)
        frame_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        analysis = video_analyzer.analyze_behavior(frame_img)
        return analysis
        
    except Exception as e:
        return {"emotion": "neutral", "engagement_score": 50, "status": "Analyzing"}

@app.post("/generate-report")
async def generate_final_report(
    session_id: str = Form(...),
    candidate_name: str = Form(...),
    candidate_email: str = Form(None),
    job_title: str = Form(None)
):
    """Generate comprehensive interview report"""
    try:
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = active_sessions[session_id]
        answers = session_data.get("answers", [])
        questions = session_data.get("questions", [])
        
        # Calculate scores
        if answers:
            scores = [a["score"] for a in answers]
            avg_score = sum(scores) / len(scores)
            passed_questions = len([s for s in scores if s >= 50])
        else:
            avg_score = 0
            passed_questions = 0
        
        # Determine verdict
        if avg_score >= 80:
            verdict = "STRONG HIRE"
            verdict_color = "success"
            recommendation = "Highly recommended. Proceed to final round."
        elif avg_score >= 65:
            verdict = "HIRE"
            verdict_color = "info"
            recommendation = "Good candidate. Consider for the position."
        elif avg_score >= 50:
            verdict = "CONSIDER"
            verdict_color = "warning"
            recommendation = "Potential candidate. May need additional training."
        else:
            verdict = "REJECT"
            verdict_color = "error"
            recommendation = "Not recommended at this time."
        
        # Create report
        report = {
            "id": f"{candidate_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "job_title": job_title or session_data.get("job_title", "Not specified"),
            "date": datetime.now().isoformat(),
            "overall_score": round(avg_score, 2),
            "technical_score": round(avg_score, 2),
            "questions_answered": len(answers),
            "total_questions": len(questions),
            "answers": answers,
            "strengths": [
                "Good communication skills" if any(a["score"] >= 70 for a in answers) else "Areas for improvement in communication",
                "Technical knowledge demonstrated" if any("technical" in str(a) for a in answers) else "Technical depth needs improvement"
            ],
            "areas_for_improvement": [
                "Provide more detailed answers" if any(a["word_count"] < 20 for a in answers) else "Answer quality is good",
                "Practice technical concepts" if avg_score < 70 else "Continue building on strong foundation"
            ],
            "overall_assessment": f"Candidate answered {passed_questions}/{len(questions)} questions satisfactorily with an average score of {round(avg_score, 2)}%.",
            "verdict": verdict,
            "verdict_color": verdict_color,
            "recommendation": recommendation,
            "next_steps": "HR will contact you within 3-5 business days with further updates."
        }
        
        # Save report
        report_filename = f"{candidate_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join(REPORTS_DIR, report_filename)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        return report
        
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/all")
async def get_all_reports():
    """Get all reports for admin dashboard"""
    reports = []
    if os.path.exists(REPORTS_DIR):
        for filename in os.listdir(REPORTS_DIR):
            if filename.endswith('.json'):
                with open(os.path.join(REPORTS_DIR, filename), 'r') as f:
                    report = json.load(f)
                    reports.append({
                        "id": filename.replace('.json', ''),
                        "candidate_name": report.get("candidate_name", "Unknown"),
                        "candidate_email": report.get("candidate_email", ""),
                        "job_title": report.get("job_title", "Not specified"),
                        "date": report.get("date", ""),
                        "overall_score": report.get("overall_score", 0),
                        "verdict": report.get("verdict", "PENDING")
                    })
    reports.sort(key=lambda x: x.get("date", ""), reverse=True)
    return reports

@app.get("/reports/{candidate_name}")
async def get_candidate_reports(candidate_name: str):
    """Get reports for a specific candidate"""
    reports = []
    if os.path.exists(REPORTS_DIR):
        for filename in os.listdir(REPORTS_DIR):
            if filename.endswith('.json') and candidate_name.lower() in filename.lower():
                with open(os.path.join(REPORTS_DIR, filename), 'r') as f:
                    report = json.load(f)
                    reports.append(report)
    reports.sort(key=lambda x: x.get("date", ""), reverse=True)
    return reports

@app.get("/report/{report_id}")
async def get_report(report_id: str):
    """Get specific report by ID"""
    report_path = os.path.join(REPORTS_DIR, f"{report_id}.json")
    if os.path.exists(report_path):
        with open(report_path, 'r') as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Report not found")


@app.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    try:
        print("🎤 Processing speech-to-text...")
        
        # Save webm file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            content = await audio.read()
            tmp.write(content)
            webm_path = tmp.name
            print(f"📁 Webm saved: {webm_path}, size: {len(content)} bytes")

        # Try using speech_recognition first (lighter, no FFmpeg needed)
        try:
            import speech_recognition as sr
            
            # Convert webm to wav using pydub (pure Python)
            try:
                from pydub import AudioSegment
                wav_path = webm_path.replace(".webm", ".wav")
                audio_segment = AudioSegment.from_file(webm_path, format="webm")
                audio_segment.export(wav_path, format="wav")
                print(f" Converted to wav using pydub")
                
                # Use speech_recognition
                recognizer = sr.Recognizer()
                with sr.AudioFile(wav_path) as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio_data = recognizer.record(source)
                    text = recognizer.recognize_google(audio_data)
                
                # Cleanup
                os.unlink(webm_path)
                os.unlink(wav_path)
                
                print(f"🎤 Transcribed (Google): '{text}'")
                return {"text": text}
                
            except ImportError:
                print("pydub not installed, trying direct webm...")
                # Try direct webm with speech_recognition
                recognizer = sr.Recognizer()
                with sr.AudioFile(webm_path) as source:
                    audio_data = recognizer.record(source)
                    text = recognizer.recognize_google(audio_data)
                os.unlink(webm_path)
                print(f"🎤 Transcribed (direct): '{text}'")
                return {"text": text}
                
        except Exception as e:
            print(f"Speech recognition failed: {e}")
            
            # Fallback: Try Whisper with proper ffmpeg path
            try:
                import whisper
                import subprocess
                
                # Set ffmpeg path explicitly for whisper
                ffmpeg_path = "C:\\ffmpeg\\bin\\ffmpeg.exe"
                
                if os.path.exists(ffmpeg_path):
                    # Set environment variable for ffmpeg
                    os.environ["PATH"] = os.environ["PATH"] + os.pathsep + "C:\\ffmpeg\\bin"
                    
                    # Convert webm to wav using explicit ffmpeg
                    wav_path = webm_path.replace(".webm", ".wav")
                    subprocess.run([
                        ffmpeg_path, "-y",
                        "-i", webm_path,
                        "-ar", "16000",
                        "-ac", "1",
                        wav_path
                    ], capture_output=True, check=True)
                    
                    # Load whisper model
                    model = whisper.load_model("base")
                    result = model.transcribe(wav_path)
                    text = result.get("text", "").strip()
                    
                    # Cleanup
                    os.unlink(webm_path)
                    os.unlink(wav_path)
                    
                    print(f"🎤 Transcribed (Whisper): '{text}'")
                    return {"text": text}
                else:
                    raise Exception("FFmpeg not found")
                    
            except Exception as whisper_error:
                print(f"Whisper transcription failed: {whisper_error}")
                os.unlink(webm_path)
                return {"text": ""}
        
    except Exception as e:
        print(f"Speech error: {e}")
        import traceback
        traceback.print_exc()
        return {"text": ""}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
