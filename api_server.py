import os, shutil, uuid, cv2, json
import base64
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests
from typing import Optional
import asyncio
from datetime import datetime
import logging

#Import your ML modules
from ml_core.resume_parser import ResumeAnalyzer
from ml_core.engine import RecruitmentEngine
from ml_core.voice_processor import VoiceInterface
from ml_core.report_generator import ReportGenerator
from ml_core.video_analyzer import VideoAnalyzer
from ml_core.ai_interviewer import AIInterviewer


#Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MakeItHired AI Service")

#Configure CORS
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://localhost:8081"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True,)

#Initialize ML components
analyzer, engine, voice = ResumeAnalyzer(), RecruitmentEngine(), VoiceInterface()
video_analyzer = VideoAnalyzer()
ai_interviewer = AIInterviewer()

UPLOAD_DIR = "data/uploads"
ID_PHOTOS_DIR = "data/id_photos"
REPORTS_DIR = "data/reports"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(ID_PHOTOS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Store active sessions
active_sessions = {}

# Gemini API Key (Replace with your actual key)
GEMINI_API_KEY = "AIzaSyCTr8nZkgmKXnKxGahSXxqYOOW13V9-nyo"  # Get from https://makersuite.google.com/app/apikey
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"

@app.get("/")
async def root():
    return {
        "service": "MakeItHired AI Service",
        "status": "active",
        "features": [
            "resume_parsing",
            "skill_extraction",
            "semantic_matching",
            "biometric_verification",
            "video_analysis",
            "voice_interview"
        ]
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/debug")
async def debug():
    return {
        "status": "running",
        "endpoints": ["/", "/health", "/upload-id-photo", "/verify-identity", "/parse-resume", "/generate-questions", "/evaluate-answer", "/generate-report"],
        "directories": {
            "id_photos": os.path.exists(ID_PHOTOS_DIR),
            "uploads": os.path.exists(UPLOAD_DIR)
        }
    }

@app.post("/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    """
    Parse resume and extract skills, experience, and generate score
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{session_id}.pdf")
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract text from resume
        resume_text = analyzer.extract_text(file_path)
        
        if not resume_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        # Extract skills using custom NER model
        skills = analyzer.extract_skills(resume_text)
        
        # Calculate resume score based on content
        resume_score = calculate_resume_score(resume_text, skills)
        
        # Extract experience years
        experience_years = extract_experience_years(resume_text)
        
        # Generate recommendations
        recommendations = generate_recommendations(resume_text, skills, experience_years)
        
        # Prepare response
        result = {
            "session_id": session_id,
            "resume_score": resume_score,
            "skills_found": skills,
            "experience_years": experience_years,
            "recommendations": recommendations,
            "word_count": len(resume_text.split()),
            "filename": file.filename,
            "has_email": "@" in resume_text,
            "has_phone": any(char.isdigit() for char in resume_text) and len(resume_text) > 9
        }
        
        # Store in active session
        active_sessions[session_id] = {
            "resume_text": resume_text,
            "skills": skills,
            "resume_score": resume_score,
            "timestamp": datetime.now().isoformat()
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/match-job")
async def match_job_with_resume(
    session_id: str = Form(...),
    job_description: str = Form(...)
):
    """
    Match resume with job description using semantic similarity
    """
    try:
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = active_sessions[session_id]
        resume_text = session_data["resume_text"]
        
        # Calculate semantic match score using SBERT
        match_score = engine.calculate_score(resume_text, job_description)
        
        # Extract job requirements
        job_skills = extract_skills_from_text(job_description)
        
        # Calculate skill match
        existing_skills = session_data.get("skills", [])
        matched_skills = [s for s in job_skills if any(skill.lower() in s.lower() or s.lower() in skill.lower() for skill in existing_skills)]
        
        # Update session
        session_data["match_score"] = match_score
        session_data["job_description"] = job_description
        
        return {
            "match_score": match_score,
            "skill_match_percentage": round((len(matched_skills) / len(job_skills) * 100) if job_skills else 0, 2),
            "matched_skills": matched_skills,
            "missing_skills": [s for s in job_skills if s not in matched_skills]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/verify-identity")
async def verify_identity(
    session_id: str = Form(...),
    image: str = Form(...),  # base64 image
    user_id: str = Form(None)
):
    """
    Verify candidate identity using ID card and live photo
    """
    try:
        logger.info(f"Starting identity verification for session: {session_id}, user_id: {user_id}")
        
        # Decode base64 image
        if ',' in image:
            image_data = base64.b64decode(image.split(',')[1])
        else:
            image_data = base64.b64decode(image)
            
        nparr = np.frombuffer(image_data, np.uint8)
        live_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if live_frame is None:
            logger.error("Failed to decode live image")
            return {
                "verified": False,
                "confidence": 0,
                "message": "Could not capture clear image. Please try again with better lighting."
            }

        # Save live image temporarily
        live_path = os.path.join(UPLOAD_DIR, f"{session_id}_live.jpg")
        cv2.imwrite(live_path, live_frame)
        
        # Find the ID photo for this user
        id_path = None
        
        # 1. Check in ID_PHOTOS_DIR with various extensions
        if user_id:
            extensions = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']
            for ext in extensions:
                test_path = os.path.join(ID_PHOTOS_DIR, f"user_{user_id}{ext}")
                if os.path.exists(test_path):
                    id_path = test_path
                    logger.info(f"Found ID photo at: {id_path}")
                    break

        # 2. Check in UPLOAD_DIR
        if not id_path and user_id:
            test_path = os.path.join(UPLOAD_DIR, f"id_photo_{user_id}.jpg")
            if os.path.exists(test_path):
                id_path = test_path
                logger.info(f"Found ID photo in uploads at: {id_path}")

        # 3. Check for any ID photo in uploads folder
        if not id_path:
            upload_files = os.listdir(UPLOAD_DIR)
            for file in upload_files:
                if 'id' in file.lower() and (file.endswith('.jpg') or file.endswith('.jpeg') or file.endswith('.png')):
                    id_path = os.path.join(UPLOAD_DIR, file)
                    logger.info(f"Found generic ID photo at: {id_path}")
                    break

        # 4. If still no ID photo, return error with upload option
        if not id_path or not os.path.exists(id_path):
            logger.warning("No ID photo found for verification")
            # Clean up
            if os.path.exists(live_path):
                os.remove(live_path)
            return {
                "verified": False,
                "confidence": 0,
                "message": "No ID photo found. Please upload your ID first.",
                "requiresUpload": True
            }
            
        logger.info(f"Comparing with ID photo: {id_path}")
        
        try:
            from deepface import DeepFace

            # Verify identity using DeepFace
            result = DeepFace.verify(
                img1_path=id_path,
                img2_path=live_path,
                model_name="VGG-Face",
                enforce_detection=False,
                distance_metric="cosine",
                silent=True
            )

            verified = result['verified']
            distance = result['distance']
            confidence = round((1 - distance) * 100, 2)

            logger.info(f"Verification result - Verified: {verified}, Distance: {distance}, Confidence: {confidence}%")

            # Try alternative model if confidence is low but close
            if not verified and confidence > 40:
                logger.info("Trying with alternative model...")
                try:
                    result2 = DeepFace.verify(
                        img1_path=id_path,
                        img2_path=live_path,
                        model_name="Facenet",
                        enforce_detection=False,
                        distance_metric="cosine",
                        silent=True
                    )
                    if result2['verified']:
                        verified = True
                        confidence = round((1 - result2['distance']) * 100, 2)
                        logger.info(f"Alternative model succeeded! New confidence: {confidence}%")
                except Exception as e:
                    logger.error(f"Alternative model error: {e}")

            # Clean up
            if os.path.exists(live_path):
                os.remove(live_path)
                logger.info("Cleaned up temporary live image")

            # Store in session
            if session_id not in active_sessions:
                active_sessions[session_id] = {}
            active_sessions[session_id]['verification'] = {
                'verified': verified,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat()
            }

            return {
                "verified": verified,
                "confidence": confidence,
                "message": "Identity verified successfully!" if verified else f"Verification failed. Confidence: {confidence}%. Please ensure good lighting and face the camera directly.",
                "distance": distance
            }
        
        except ImportError:
            logger.error("DeepFace not installed")
            if os.path.exists(live_path):
                os.remove(live_path)
            return {
                "verified": False,
                "confidence": 0,
                "message": "Face verification system not available. Please install required packages: pip install deepface tensorflow"
            }
    
        except Exception as e:
            logger.error(f"DeepFace verification error: {e}")
            if os.path.exists(live_path):
                os.remove(live_path)
            return {
                "verified": False,
                "confidence": 0,
                "message": f"Could not detect face. Please ensure your face is clearly visible and well-lit.",
                "error": str(e)
            }
            
    except Exception as e:
        logger.error(f"Verification error: {e}")
        return {
            "verified": False,
            "confidence": 0,
            "message": f"Verification failed: {str(e)}"
        }
    
@app.post("/upload-id-photo")
async def upload_id_photo(
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload ID photo for a user
    """
    try:
        logger.info(f"Uploading ID photo for user: {user_id}")
        logger.info(f"File: {file.filename}, Content-Type: {file.content_type}")

        #Validate file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if file.content_type not in allowed_types:
            return {
                    "success": False,
                    "message": f"Only JPEG, PNG, and Webp images are allowed. Received: {file.content_type}" 
            }
        # #Read file content
        contents = await file.read()
        if len(contents) == 0:
            logger.error("Empty file received")
            return { 
                "success": False,
                "message": "Empty file received" 
            }
        
        #Create directory if it does not extst
        os.makedirs(ID_PHOTOS_DIR,exist_ok=True)
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        # Save the file
        file_extension = file.filename.split('.')[-1]
        filename = f"user_{user_id}.{file_extension}"
        file_path = os.path.join(ID_PHOTOS_DIR, filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        
        logger.info(f"ID photo saved to: {file_path}")

        
        try:
            # import cv2
            # Convert to numpy array for OpenCV
            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is not None:
                # Save as JPEG in uploads folder
                jpg_path = os.path.join(UPLOAD_DIR, f"id_photo_{user_id}.jpg")
                cv2.imwrite(jpg_path, img)
                logger.info(f"Copy saved to: {jpg_path}")
        except Exception as e:
            logger.warning(f"Could not create copy: {e}")
        
        return {
            "success": True,
            "message": "ID photo uploaded successfully!",
            "path": file_path,
            "userId": user_id,
            "filename": filename
        }
        
    except Exception as e:
        logger.error(f"ID photo upload error: {e}", exc_info=True)
        return{ 
                "success": False,
                "message": f"Upload failed: {str(e)}"
        }
    
@app.get("/get-id-photo/{user_id}")
async def get_id_photo(user_id: str):
    """
    Get ID photo for a user
    """
    try:
        # Try different possible extensions
        extensions = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']
        
        for ext in extensions:
            file_path = os.path.join(ID_PHOTOS_DIR, f"user_{user_id}{ext}")
            if os.path.exists(file_path):
                return {"exists": True, "path": file_path}
        
        return {"exists": False, "message": "No ID photo found"}
        
    except Exception as e:
        return {"exists": False, "error": str(e)}

@app.post("/analyze-video")
async def analyze_video_frame(
    session_id: str = Form(...),
    frame: str = Form(...)  # base64 image
):
    """
    Analyze video frame for behavioral insights
    """
    try:
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Decode frame
        if ',' in frame:
            image_data = base64.b64decode(frame.split(',')[1])
        else:
            image_data = base64.b64decode(frame)
            
        nparr = np.frombuffer(image_data, np.uint8)
        frame_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Analyze behavior using DeepFace
        analysis = video_analyzer.analyze_behavior(frame_img)
        
        # Store in session (keep last few analyses)
        if "behavior_history" not in active_sessions[session_id]:
            active_sessions[session_id]["behavior_history"] = []
        
        active_sessions[session_id]["behavior_history"].append({
            "timestamp": datetime.now().isoformat(),
            **analysis
        })
        
        # Keep only last 10
        if len(active_sessions[session_id]["behavior_history"]) > 10:
            active_sessions[session_id]["behavior_history"] = active_sessions[session_id]["behavior_history"][-10:]
        
        return analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-questions")
async def generate_interview_questions(
    session_id: str = Form(...),
    job_title: str = Form(None),
    job_description: str = Form(None),
    resume_skills: str = Form(None)
):
    """
    Generate JOB-SPECIFIC interview questions based on:
    - Job requirements (from the job posting)
    - Candidate's resume skills
    """
    try:
        if session_id not in active_sessions:
            active_sessions[session_id] = {}
        
        session_data = active_sessions[session_id]
        
        # Get skills from resume
        candidate_skills = resume_skills or session_data.get("skills", "Full Stack Development","Python", "Java", "JavaScript")
        job_title_text = job_title or session_data.get("job_title", "Software Developer")
        job_desc_text = job_description or session_data.get("job_description", "")
        
        # Store job info in session
        session_data["job_title"] = job_title_text
        session_data["job_description"] = job_desc_text
        session_data["skills"] = candidate_skills
        
        # Create prompt for Gemini
        prompt = f"""
        You are a technical interviewer conducting a job interview for a {job_title_text} position.
        
        **Job Requirements:**
        {job_desc_text}
        
        **Candidate's Skills from Resume:**
        {candidate_skills}
        
        Generate 5 personalized interview questions that:
        1. Assess the candidate's fit for this specific job
        2. Test their knowledge in relevant technologies from the job requirements
        3. Validate their claimed skills from the resume
        4. Include ONE common introductory question: "Tell me about yourself and your experience relevant to this role"
        5. Include a mix of technical, problem-solving, and behavioral questions
        
        Format the response as JSON:
        {{
            "questions": [
                {{
                    "text": "Question text",
                    "type": "technical/problem-solving/behavioral/intro",
                    "skills_tested": ["skill1", "skill2"],
                    "keywords": ["keyword1", "keyword2"],
                    "difficulty": "easy/medium/hard"
                }}
            ]
        }}
        
        Make the questions challenging and job-specific. Ensure they directly relate to the job requirements.
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
                
                # Extract questions and metadata
                questions_list = [q["text"] for q in questions_data["questions"]]
                questions_metadata = questions_data["questions"]
                
                session_data["questions"] = questions_list
                session_data["questions_metadata"] = questions_metadata
                
                logger.info(f"Generated {len(questions_list)} job-specific questions")
                
                return {
                    "questions": questions_list,
                    "metadata": questions_metadata,
                    "job_title": job_title_text,
                    "total": len(questions_list)
                }
            else:
                # Fallback to default questions based on job title
                return generate_fallback_questions(job_title_text, candidate_skills)
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return generate_fallback_questions(job_title_text, candidate_skills)
            
    except Exception as e:
        logger.error(f"Question generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_fallback_questions(job_title, skills):
    """Generate fallback questions based on job title and skills"""
    questions = [
        {"text": f"Tell me about yourself and your experience relevant to this {job_title} position.", 
         "type": "intro", "skills_tested": ["communication"], "keywords": ["experience", "background", "skills"]},
        {"text": f"What experience do you have with {skills.split(',')[0] if skills else 'relevant technologies'}?",
         "type": "technical", "skills_tested": [skills.split(',')[0] if skills else "technical"], 
         "keywords": ["experience", "project", "implementation"]},
        {"text": "Describe a challenging technical problem you solved and how you approached it.",
         "type": "problem-solving", "skills_tested": ["problem-solving"], 
         "keywords": ["challenge", "solution", "approach"]},
        {"text": "How do you stay updated with the latest technologies in your field?",
         "type": "behavioral", "skills_tested": ["learning"], 
         "keywords": ["learn", "update", "technology"]},
        {"text": f"If you were hired for this {job_title} role, what would be your first 30-day priority?",
         "type": "behavioral", "skills_tested": ["planning"], 
         "keywords": ["plan", "priority", "first"]}
    ]
    return {
        "questions": [q["text"] for q in questions],
        "metadata": questions,
        "job_title": job_title,
        "total": len(questions)
    }



# @app.post("/evaluate-answer")
# async def evaluate_answer(
#     session_id: str = Form(...),
#     answer: str = Form(...),
#     question_index: int = Form(...)
# ):
#     """Evaluate answer using Gemini AI with job context"""
#     try:
#         if session_id not in active_sessions:
#             raise HTTPException(status_code=404, detail="Session not found")
        
#         session_data = active_sessions[session_id]
#         questions = session_data.get("questions", [])
#         questions_metadata = session_data.get("questions_metadata", [])
        
#         if question_index >= len(questions):
#             raise HTTPException(status_code=400, detail="Invalid question index")
        
#         current_question = questions[question_index]
#         current_metadata = questions_metadata[question_index] if question_index < len(questions_metadata) else {}
        
#         # Get job context
#         job_title = session_data.get("job_title", "the position")
#         expected_skills = current_metadata.get("skills_tested", [])
#         question_type = current_metadata.get("type", "technical")
#         expected_keywords = current_metadata.get("keywords", [])
        
#         # Use Gemini to evaluate
#         prompt = f"""
#         Evaluate this interview answer for a {job_title} position.
        
#         Question: {current_question}
#         Question Type: {question_type}
#         Expected Skills: {', '.join(expected_skills) if expected_skills else 'General knowledge'}
        
#         Candidate's Answer: {answer}
        
#         Provide evaluation in JSON format:
#         {{
#             "score": (0-100 integer),
#             "technical_accuracy": (0-100),
#             "clarity": (0-100),
#             "relevance": (0-100),
#             "feedback": "brief constructive feedback",
#             "strengths": ["strength1", "strength2"],
#             "areas_to_improve": ["area1", "area2"]
#         }}
        
#         Base the score on:
#         - Relevance to the question (30%)
#         - Technical accuracy (40%)
#         - Clarity and communication (30%)
#         """
        
#         try:
#             response = requests.post(
#                 GEMINI_URL,
#                 json={
#                     "contents": [{"parts": [{"text": prompt}]}],
#                     "generationConfig": {
#                         "temperature": 0.3,
#                         "maxOutputTokens": 1024,
#                         "responseMimeType": "application/json"
#                     }
#                 },
#                 timeout=30
#             )
            
#             if response.status_code == 200:
#                 result = response.json()
#                 evaluation_text = result['candidates'][0]['content']['parts'][0]['text']
#                 evaluation = json.loads(evaluation_text)
#                 score = evaluation.get("score", 70)
#                 feedback = evaluation.get("feedback", "Good answer!")
#             else:
#                 # Basic scoring
#                 word_count = len(answer.split())
#                 score = min(100, (word_count / 50) * 100)
#                 feedback = "Answer recorded successfully."
                
#         except Exception as e:
#             logger.error(f"Evaluation error: {e}")
#             score = 70
#             feedback = "Your answer has been recorded."
        
#         # Store answer
#         answer_data = {
#             "question": current_question,
#             "question_type": question_type,
#             "answer": answer,
#             "score": score,
#             "feedback": feedback,
#             "timestamp": datetime.now().isoformat()
#         }
        
#         if "answers" not in session_data:
#             session_data["answers"] = []
#         session_data["answers"].append(answer_data)
#         session_data["current_question"] = question_index + 1
        
#         is_complete = question_index + 1 >= len(questions)
        
#         return {
#             "score": score,
#             "feedback": feedback,
#             "is_complete": is_complete,
#             "next_question": questions[question_index + 1] if not is_complete else None
#         }
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.post("/evaluate-answer")
async def evaluate_answer(
    session_id: str = Form(...),
    answer: str = Form(...),
    question_index: int = Form(...)
):
    """Evaluate answer using Gemini AI with job context"""
    try:
        logger.info(f"Evaluating answer for session: {session_id}, question: {question_index}")
        
        if session_id not in active_sessions:
            logger.error(f"Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = active_sessions[session_id]
        
        # Check if questions exist
        if "questions" not in session_data or not session_data["questions"]:
            logger.error("No questions found in session")
            raise HTTPException(status_code=400, detail="No questions found in session")
        
        questions = session_data["questions"]
        
        if question_index >= len(questions):
            logger.error(f"Invalid question index: {question_index}, total: {len(questions)}")
            raise HTTPException(status_code=400, detail="Invalid question index")
        
        current_question = questions[question_index]
        
        # Get metadata if available
        questions_metadata = session_data.get("questions_metadata", [])
        current_metadata = questions_metadata[question_index] if question_index < len(questions_metadata) else {}
        
        # Get job context
        job_title = session_data.get("job_title", "the position")
        expected_skills = current_metadata.get("skills_tested", [])
        question_type = current_metadata.get("type", "technical")
        expected_keywords = current_metadata.get("keywords", [])
        
        # Simple scoring based on answer length and keyword matching
        answer_lower = answer.lower()
        word_count = len(answer.split())
        
        # Calculate keyword match score
        if expected_keywords:
            matches = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
            keyword_score = (matches / len(expected_keywords)) * 100
        else:
            keyword_score = 50
        
        # Calculate length score (aim for 30-50 words)
        if word_count >= 30:
            length_score = 100
        elif word_count >= 20:
            length_score = 80
        elif word_count >= 10:
            length_score = 60
        else:
            length_score = 40
        
        # Combined score (70% keyword match, 30% length)
        score = int((keyword_score * 0.7) + (length_score * 0.3))
        score = max(0, min(100, score))  # Clamp between 0-100
        
        # Generate feedback based on score
        if score >= 80:
            feedback = "Excellent answer! Good technical depth and clarity."
        elif score >= 60:
            feedback = "Good answer. Consider adding more specific details."
        elif score >= 40:
            feedback = "Fair answer. Try to elaborate more with specific examples."
        else:
            feedback = "Answer too brief. Please provide more detailed responses."
        
        # Store answer
        answer_data = {
            "question": current_question,
            "question_type": question_type,
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
        
        logger.info(f"Answer evaluated - Score: {score}, Complete: {is_complete}")
        
        return {
            "score": score,
            "feedback": feedback,
            "is_complete": is_complete,
            "next_question": questions[question_index + 1] if not is_complete else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Answer evaluation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# @app.post("/generate-report")
# async def generate_final_report(
#     session_id: str = Form(...),
#     candidate_name: str = Form(...),
#     candidate_email: str = Form(None),
#     job_id: int = Form(None),
#     job_title: str = Form(None)
# ):
#     """Generate comprehensive AI-powered interview report"""
#     try:
#         if session_id not in active_sessions:
#             raise HTTPException(status_code=404, detail="Session not found")
        
#         session_data = active_sessions[session_id]
#         answers = session_data.get("answers", [])
#         questions = session_data.get("questions", [])
        
#         # Calculate scores
#         if answers:
#             avg_score = sum(a["score"] for a in answers) / len(answers)
#             technical_scores = [a["score"] for a in answers if a.get("question_type") == "technical"]
#             technical_avg = sum(technical_scores) / len(technical_scores) if technical_scores else avg_score
#         else:
#             avg_score = 0
#             technical_avg = 0
        
#         # Generate AI summary
#         prompt = f"""
#         Generate a professional interview summary for candidate {candidate_name} applying for {session_data.get('job_title', 'a position')}.
        
#         Performance Metrics:
#         - Overall Score: {avg_score}%
#         - Technical Score: {technical_avg}%
#         - Questions Answered: {len(answers)}/{len(questions)}
        
#         Interview Highlights:
#         {json.dumps([{"question": a["question"], "score": a["score"]} for a in answers], indent=2)}
        
#         Provide summary in JSON format:
#         {{
#             "overall_assessment": "detailed paragraph summary",
#             "strengths": ["strength1", "strength2", "strength3"],
#             "areas_for_improvement": ["area1", "area2", "area3"],
#             "technical_proficiency": "rating",
#             "communication_skills": "rating",
#             "recommendation": "STRONG HIRE/HIRE/CONSIDER/REJECT",
#             "next_steps": "recommended next steps"
#         }}
#         """
        
#         try:
#             response = requests.post(GEMINI_URL, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
#             if response.status_code == 200:
#                 result = response.json()
#                 summary_text = result['candidates'][0]['content']['parts'][0]['text']
#                 summary_data = json.loads(summary_text)
#             else:
#                 summary_data = generate_fallback_summary(avg_score)
#         except:
#             summary_data = generate_fallback_summary(avg_score)
        
#         # Determine verdict
#         if avg_score >= 80:
#             verdict = "STRONG HIRE"
#             color = "success"
#         elif avg_score >= 65:
#             verdict = "HIRE"
#             color = "info"
#         elif avg_score >= 50:
#             verdict = "CONSIDER"
#             color = "warning"
#         else:
#             verdict = "REJECT"
#             color = "error"
        
#         # Create complete report
#         report = {
#             "candidate_name": candidate_name,
#             "candidate_email": candidate_email,
#             "job_id": job_id,
#             "job_title": session_data.get("job_title", "Not specified"),
#             "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#             "overall_score": round(avg_score, 2),
#             "technical_score": round(technical_avg, 2),
#             "questions_answered": len(answers),
#             "total_questions": len(questions),
#             "answers": answers,
#             "strengths": summary_data.get("strengths", []),
#             "areas_for_improvement": summary_data.get("areas_for_improvement", []),
#             "overall_assessment": summary_data.get("overall_assessment", "Interview completed."),
#             "technical_proficiency": summary_data.get("technical_proficiency", "Average"),
#             "communication_skills": summary_data.get("communication_skills", "Good"),
#             "recommendation": summary_data.get("recommendation", verdict),
#             "next_steps": summary_data.get("next_steps", "Awaiting HR review"),
#             "verdict": verdict,
#             "verdict_color": color,
#             "session_id": session_id
#         }
        
#         # Save report to file
#         report_filename = f"{candidate_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
#         report_path = os.path.join(REPORTS_DIR, report_filename)
#         with open(report_path, "w") as f:
#             json.dump(report, f, indent=2)
        
#         # Also save as latest report
#         latest_report_path = "latest_report.json"
#         with open(latest_report_path, "w") as f:
#             json.dump(report, f, indent=2)
        
#         return report
        
#     except Exception as e:
#         logger.error(f"Report generation error: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# def generate_fallback_summary(avg_score):
#     """Generate fallback summary if Gemini fails"""
#     if avg_score >= 80:
#         return {
#             "overall_assessment": "Excellent candidate with strong technical skills and clear communication.",
#             "strengths": ["Strong technical knowledge", "Clear communication", "Good problem-solving"],
#             "areas_for_improvement": ["Consider more detailed examples", "Practice system design"],
#             "technical_proficiency": "Expert",
#             "communication_skills": "Excellent",
#             "recommendation": "STRONG HIRE",
#             "next_steps": "Proceed to final interview round"
#         }
#     elif avg_score >= 65:
#         return {
#             "overall_assessment": "Good candidate with solid fundamentals and relevant experience.",
#             "strengths": ["Good technical foundation", "Relevant experience", "Enthusiastic"],
#             "areas_for_improvement": ["Deepen technical knowledge", "More structured answers"],
#             "technical_proficiency": "Proficient",
#             "communication_skills": "Good",
#             "recommendation": "HIRE",
#             "next_steps": "Technical assignment recommended"
#         }
#     else:
#         return {
#             "overall_assessment": "Candidate shows potential but needs improvement in key areas.",
#             "strengths": ["Good attitude", "Willing to learn"],
#             "areas_for_improvement": ["Technical depth", "Answer structure", "Specific examples"],
#             "technical_proficiency": "Developing",
#             "communication_skills": "Average",
#             "recommendation": "CONSIDER",
#             "next_steps": "Additional training recommended"
#         }
    

@app.post("/generate-questions")
async def generate_interview_questions(
    session_id: str = Form(...),
    job_title: str = Form(None),
    job_description: str = Form(None),
    resume_skills: str = Form(None)
):
    """
    Generate JOB-SPECIFIC interview questions based on:
    - Job requirements (from the job posting)
    - Candidate's resume skills
    """
    try:
        if session_id not in active_sessions:
            active_sessions[session_id] = {}
        
        session_data = active_sessions[session_id]
        
        # Get skills from resume - ensure they are not empty
        candidate_skills = resume_skills or session_data.get("skills", "")
        if not candidate_skills or candidate_skills.strip() == "":
            candidate_skills = "Full Stack Development, Python, Java, JavaScript"
            logger.warning("No skills found, using default skills")
        
        job_title_text = job_title or session_data.get("job_title", "Software Developer")
        job_desc_text = job_description or session_data.get("job_description", "")
        
        # Store job info in session
        session_data["job_title"] = job_title_text
        session_data["job_description"] = job_desc_text
        session_data["skills"] = candidate_skills
        
        # Enhanced prompt for Gemini
        prompt = f"""
        You are a technical interviewer for a {job_title_text} position.
        
        **Job Requirements:**
        {job_desc_text if job_desc_text else "Not specified, but the role requires strong technical skills."}
        
        **Candidate's Skills from Resume:**
        {candidate_skills}
        
        Generate 5 personalized interview questions that:
        1. **Must directly reference the candidate's specific skills** from the list above. For example, if they know Python, ask a Python-related question.
        2. Include ONE introductory question: "Tell me about yourself and your experience relevant to this role."
        3. Include a mix of technical, problem-solving, and behavioral questions.
        4. Make each question clear, specific, and job-relevant.
        
        Format the response as JSON with this exact structure:
        {{
            "questions": [
                {{
                    "text": "The question text (must include a skill name if possible)",
                    "type": "intro/technical/problem-solving/behavioral",
                    "skills_tested": ["skill1", "skill2"],
                    "keywords": ["keyword1", "keyword2"]
                }}
            ]
        }}
        
        Example of a good question: "Based on your Python experience, how would you optimize a slow database query?"
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
                
                # Parse JSON response
                try:
                    questions_data = json.loads(questions_text)
                    questions_list = [q["text"] for q in questions_data["questions"]]
                    questions_metadata = questions_data["questions"]
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Failed to parse Gemini response: {e}")
                    logger.error(f"Raw response: {questions_text}")
                    # Fallback to manual parsing if JSON is malformed
                    questions_list = generate_fallback_questions_list(job_title_text, candidate_skills)
                    questions_metadata = []
                
                # Ensure we have exactly 5 questions
                if len(questions_list) < 5:
                    # Add fallback questions if needed
                    fallback = generate_fallback_questions_list(job_title_text, candidate_skills)
                    questions_list.extend(fallback[len(questions_list):5])
                
                session_data["questions"] = questions_list
                session_data["questions_metadata"] = questions_metadata
                
                logger.info(f"Generated {len(questions_list)} job-specific questions")
                
                return {
                    "questions": questions_list,
                    "metadata": questions_metadata,
                    "job_title": job_title_text,
                    "total": len(questions_list)
                }
            else:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                return generate_fallback_questions(job_title_text, candidate_skills)
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return generate_fallback_questions(job_title_text, candidate_skills)
            
    except Exception as e:
        logger.error(f"Question generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_fallback_questions_list(job_title, skills):
    """Generate fallback questions if Gemini fails"""
    skill_list = [s.strip() for s in skills.split(',') if s.strip()]
    main_skill = skill_list[0] if skill_list else "programming"
    
    return [
        f"Tell me about yourself and your experience relevant to this {job_title} role.",
        f"What experience do you have with {main_skill} and how have you applied it in real projects?",
        f"Describe a challenging technical problem you solved using {main_skill}.",
        f"How do you stay updated with the latest technologies in {main_skill}?",
        f"If hired for this {job_title} role, what would be your first 30-day priority?"
    ]

def generate_fallback_questions(job_title, skills):
    """Generate fallback questions with metadata"""
    questions_list = generate_fallback_questions_list(job_title, skills)
    metadata = [
        {"type": "intro", "skills_tested": ["communication"], "keywords": ["experience", "background"]},
        {"type": "technical", "skills_tested": [skills.split(',')[0] if skills else "technical"], "keywords": ["experience", "project"]},
        {"type": "problem-solving", "skills_tested": ["problem-solving"], "keywords": ["challenge", "solution"]},
        {"type": "behavioral", "skills_tested": ["learning"], "keywords": ["learn", "update"]},
        {"type": "behavioral", "skills_tested": ["planning"], "keywords": ["plan", "priority"]}
    ]
    return {
        "questions": questions_list,
        "metadata": metadata,
        "job_title": job_title,
        "total": len(questions_list)
    }

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
                        "verdict": report.get("verdict", "PENDING"),
                        "verdict_color": report.get("verdict_color", "warning")
                    })
    
    # Sort by date (newest first)
    reports.sort(key=lambda x: x.get("date", ""), reverse=True)
    return reports

@app.get("/reports/{candidate_name}")
async def get_candidate_reports(candidate_name: str):
    """Get reports for a specific candidate (for user dashboard)"""
    reports = []
    if os.path.exists(REPORTS_DIR):
        for filename in os.listdir(REPORTS_DIR):
            if filename.endswith('.json') and candidate_name.lower() in filename.lower():
                with open(os.path.join(REPORTS_DIR, filename), 'r') as f:
                    report = json.load(f)
                    reports.append(report)
    
    reports.sort(key=lambda x: x.get("date", ""), reverse=True)
    return reports



@app.get("/session/{session_id}")
async def get_session_data(session_id: str):
    """
    Get session data
    """
    if session_id in active_sessions:
        return active_sessions[session_id]
    raise HTTPException(status_code=404, detail="Session not found")

@app.get("/reports")
async def get_all_reports():
    """
    Get all generated reports
    """
    reports = []
    if os.path.exists(REPORTS_DIR):
        for filename in os.listdir(REPORTS_DIR):
            if filename.endswith('.json'):
                with open(os.path.join(REPORTS_DIR, filename), 'r') as f:
                    report = json.load(f)
                    reports.append({
                        "id": filename.replace('.json', ''),
                        "candidate_name": report.get("candidate_name", "Unknown"),
                        "date": report.get("date", ""),
                        "overall_score": report.get("overall_score", 0),
                        "verdict": report.get("verdict", "PENDING")
                    })
    
    # Sort by date (newest first)
    reports.sort(key=lambda x: x.get("date", ""), reverse=True)
    return reports

@app.get("/report/{report_id}")
async def get_report(report_id: str):
    """
    Get specific report by ID
    """
    report_path = os.path.join(REPORTS_DIR, f"{report_id}.json")
    if os.path.exists(report_path):
        with open(report_path, 'r') as f:
            return json.load(f)
    
    # Try the main final_report.json
    if report_id == "latest" and os.path.exists("final_report.json"):
        with open("final_report.json", 'r') as f:
            return json.load(f)
    
    raise HTTPException(status_code=404, detail="Report not found")

# Helper functions
def calculate_resume_score(text: str, skills: list) -> int:
    """Calculate resume score based on various factors"""
    score = 0
    
    # Check for contact info
    if "@" in text: score += 10
    if any(char.isdigit() for char in text) and len(text) > 10: score += 10
    
    # Check for education
    education_keywords = ['bachelor', 'master', 'phd', 'degree', 'university', 'college']
    if any(k in text.lower() for k in education_keywords): score += 15
    
    # Check for experience
    experience_keywords = ['experience', 'worked', 'employed', 'intern']
    if any(k in text.lower() for k in experience_keywords): score += 15
    
    # Skills count
    score += min(len(skills) * 2, 20)  # Max 20 from skills
    
    # Length check
    word_count = len(text.split())
    if word_count > 500: score += 20
    elif word_count > 300: score += 15
    elif word_count > 200: score += 10
    
    return min(score, 100)

def extract_experience_years(text: str) -> float:
    """Extract years of experience from text"""
    import re
    patterns = [
        r'(\d+)\+?\s*years? of experience',
        r'experience of (\d+)\+?\s*years?',
        r'(\d+)\+?\s*years? experience',
        r'worked for (\d+)\+?\s*years?'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return float(match.group(1))
    
    # Try to find any year numbers
    years = re.findall(r'\b(20\d{2})\b', text)
    if years:
        return 2026 - int(max(years))
    
    return 0.0

def extract_skills_from_text(text: str) -> list:
    """Extract potential skills from job description"""
    common_skills = [
        'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node.js',
        'spring boot', 'django', 'flask', 'mysql', 'postgresql', 'mongodb',
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'git', 'jenkins',
        'html', 'css', 'sass', 'typescript', 'php', 'ruby', 'c++', 'c#',
        '.net', 'go', 'rust', 'swift', 'kotlin', 'flutter', 'react native',
        'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy', 'tableau',
        'power bi', 'excel', 'word', 'powerpoint', 'outlook', 'photoshop',
        'illustrator', 'figma', 'sketch', 'adobe xd', 'ui/ux', 'agile',
        'scrum', 'jira', 'confluence', 'trello', 'slack'
    ]
    
    text_lower = text.lower()
    found = []
    
    for skill in common_skills:
        if skill in text_lower:
            found.append(skill)
    
    return list(set(found))  # Remove duplicates

def generate_recommendations(text: str, skills: list, experience: float) -> list:
    """Generate resume improvement recommendations"""
    recommendations = []
    
    if not skills:
        recommendations.append("Add a dedicated skills section with relevant technical skills")
    elif len(skills) < 5:
        recommendations.append("Include more relevant skills to improve your profile")
    
    if not experience or experience < 1:
        recommendations.append("Clearly mention your years of experience")
    
    if "education" not in text.lower() and "university" not in text.lower():
        recommendations.append("Add your educational qualifications")
    
    if "project" not in text.lower():
        recommendations.append("Include projects you've worked on with specific achievements")
    
    if len(text.split()) < 200:
        recommendations.append("Add more content to your resume - aim for at least 200-300 words")
    
    if "@" not in text:
        recommendations.append("Include your email address for contact")
    
    if not recommendations:
        recommendations.append("Your resume looks good! Consider adding more quantifiable achievements")
    
    return recommendations

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
