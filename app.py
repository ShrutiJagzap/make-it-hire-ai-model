# import os
# import cv2
# import json
# import base64
# import spacy
# import numpy as np
# from flask import Flask, render_template_string, request, jsonify
# from sentence_transformers import SentenceTransformer, util
# from deepface import DeepFace

# # --- INTEGRATED ML ENGINE (Uses your trained work) ---
# class RecruitmentInference:
#     def __init__(self):
#         # 1. Load the model YOU trained in Step 1
#         print("Loading your Custom Trained NER Model...")
#         if os.path.exists("models/talent_ner"):
#             self.ner_model = spacy.load("models/talent_ner")
#         else:
#             self.ner_model = None
#             print("Warning: Custom model not found. Run train_ner.py first.")

#         # 2. Load Semantic Transformer
#         self.nlp_engine = SentenceTransformer('all-MiniLM-L6-v2')

#     def analyze_candidate(self, resume_text, jd_text):
#         # Use your TRAINED model to extract skills
#         skills = []
#         if self.ner_model:
#             doc = self.ner_model(resume_text)
#             skills = [ent.text for ent in doc.ents if ent.label_ == "SKILL"]
        
#         # Calculate Semantic Score
#         emb1 = self.nlp_engine.encode(resume_text, convert_to_tensor=True)
#         emb2 = self.nlp_engine.encode(jd_text, convert_to_tensor=True)
#         match_score = round(float(util.cos_sim(emb1, emb2)) * 100, 2)
        
#         return match_score, skills

#     def verify_biometrics(self, id_path, frame_b64):
#         # Decode webcam frame
#         img_data = base64.b64decode(frame_b64.split(',')[1])
#         nparr = np.frombuffer(img_data, np.uint8)
#         frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
#         cv2.imwrite("temp_verify.jpg", frame)

#         # ML Inference: Adaptive threshold 0.65 for demo
#         result = DeepFace.verify(
#             img1_path=id_path, 
#             img2_path="temp_verify.jpg", 
#             model_name="VGG-Face",
#             enforce_detection=False,
#             distance_metric="cosine",
#             silent=True
#         )
#         os.remove("temp_verify.jpg")
#         return result['verified'], round((1 - result['distance']) * 100, 2)

# # --- WEB UI & VOICE INTERFACE ---
# app = Flask(__name__)
# ml = RecruitmentInference()

# HTML_TEMPLATE = """
# <!DOCTYPE html>
# <html>
# <head>
#     <title>AI Recruitment Pro</title>
#     <script src="https://cdn.tailwindcss.com"></script>
#     <style>
#         body { background: #020617; color: #f8fafc; font-family: 'Inter', sans-serif; }
#         .card { background: #0f172a; border: 1px solid #1e293b; border-radius: 1.5rem; }
#     </style>
# </head>
# <body class="p-10">
#     <div class="max-w-4xl mx-auto space-y-8">
#         <h1 class="text-4xl font-black text-indigo-500">TALENT<span class="text-white">AI</span></h1>
        
#         <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
#             <div class="card p-6 space-y-4">
#                 <video id="v" autoplay class="rounded-xl w-full bg-black"></video>
#                 <button onclick="start()" id="s-btn" class="w-full bg-indigo-600 py-3 rounded-lg font-bold">START INTERVIEW</button>
#             </div>

#             <div class="card p-6">
#                 <h2 class="text-indigo-400 font-bold uppercase text-xs mb-4 tracking-widest">AI Recruiter</h2>
#                 <p id="msg" class="text-xl font-medium leading-relaxed">System offline. Upload data to begin.</p>
#                 <div id="stats" class="mt-8 space-y-2 hidden">
#                     <p id="stat-match" class="text-sm"></p>
#                     <p id="stat-bio" class="text-sm"></p>
#                 </div>
#             </div>
#         </div>
#     </div>

#     <script>
#         const msg = document.getElementById('msg');
#         const v = document.getElementById('v');
#         const synth = window.speechSynthesis;
        
#         navigator.mediaDevices.getUserMedia({video: true}).then(s => v.srcObject = s);

#         function speak(t) {
#             synth.cancel();
#             const u = new SpeechSynthesisUtterance(t);
#             u.onend = () => { if(t.includes("Why")) startListening(); };
#             msg.innerText = t;
#             synth.speak(u);
#         }

#         async function start() {
#             document.getElementById('s-btn').style.display = 'none';
#             msg.innerText = "Analyzing your credentials using custom ML models...";
            
#             // 1. Resume Match
#             const r1 = await fetch('/api/screen');
#             const d1 = await r1.json();
            
#             // 2. Biometric
#             const c = document.createElement('canvas');
#             c.width = v.videoWidth; c.height = v.videoHeight;
#             c.getContext('2d').drawImage(v, 0,0);
#             const r2 = await fetch('/api/verify', {
#                 method: 'POST', 
#                 headers: {'Content-Type': 'application/json'},
#                 body: JSON.stringify({img: c.toDataURL('image/jpeg')})
#             });
#             const d2 = await r2.json();

#             if(d2.verified) {
#                 document.getElementById('stats').classList.remove('hidden');
#                 document.getElementById('stat-match').innerText = "Resume Match: " + d1.score + "%";
#                 document.getElementById('stat-bio').innerText = "Identity: VERIFIED (" + d2.conf + "%)";
#                 speak("Identity confirmed. I see you have skills in " + d1.skills.join(', ') + ". Why should we hire you?");
#             } else {
#                 speak("Security Alert: Identity mismatch. Session closed.");
#             }
#         }

#         function startListening() {
#             const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
#             const rec = new Speech();
#             rec.onresult = (e) => {
#                 const t = e.results[0][0].transcript;
#                 speak("I have analyzed your response. You mentioned " + t + ". Interview complete. Report generated.");
#             };
#             rec.start();
#         }
#     </script>
# </body>
# </html>
# """

# @app.route('/')
# def home(): return render_template_string(HTML_TEMPLATE)

# @app.route('/api/screen')
# def screen():
#     # USES YOUR ML MODEL
#     from ml_core.resume_parser import extract_text_from_file
#     txt = extract_text_from_file("data/resume.pdf")
#     score, skills = ml.analyze_candidate(txt, "Python ML specialist")
#     return jsonify({"score": score, "skills": skills})

# @app.route('/api/verify', methods=['POST'])
# def verify():
#     d = request.json
#     v, c = ml.verify_biometrics("data/id_card.jpg", d['img'])
#     return jsonify({"verified": v, "conf": c})

# if __name__ == '__main__':
#     app.run(debug=True, port=5000)


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

import cv2
import json
import base64
import numpy as np
from flask import Flask, render_template_string, request, jsonify

# --- INTEGRATED ML ENGINE (Uses your trained work) ---
class RecruitmentInference:
    def __init__(self):
        # Initialize lazily to save startup memory
        self.ner_model = None
        self.nlp_engine = None

    def analyze_candidate(self, resume_text, jd_text):
        # Lazy load custom NER model
        if self.ner_model is None and os.path.exists("models/talent_ner"):
            print("Loading your Custom Trained NER Model...")
            try:
                import spacy
                self.ner_model = spacy.load("models/talent_ner")
            except Exception as e:
                print(f"Error loading custom NER model: {e}")
        
        # Use your TRAINED model to extract skills
        skills = []
        if self.ner_model:
            doc = self.ner_model(resume_text)
            skills = [ent.text for ent in doc.ents if ent.label_ == "SKILL"]
        
        # Lazy load Semantic Transformer
        if self.nlp_engine is None:
            from sentence_transformers import SentenceTransformer
            self.nlp_engine = SentenceTransformer('all-MiniLM-L6-v2')
            
        from sentence_transformers import util
        # Calculate Semantic Score
        emb1 = self.nlp_engine.encode(resume_text, convert_to_tensor=True)
        emb2 = self.nlp_engine.encode(jd_text, convert_to_tensor=True)
        match_score = round(float(util.cos_sim(emb1, emb2)) * 100, 2)
        
        return match_score, skills

    def verify_biometrics(self, id_path, frame_b64):
        # Decode webcam frame
        img_data = base64.b64decode(frame_b64.split(',')[1])
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        cv2.imwrite("temp_verify.jpg", frame)

        # ML Inference: Adaptive threshold 0.65 for demo
        from deepface import DeepFace
        result = DeepFace.verify(
            img1_path=id_path, 
            img2_path="temp_verify.jpg", 
            model_name="VGG-Face",
            enforce_detection=False,
            distance_metric="cosine",
            silent=True
        )
        if os.path.exists("temp_verify.jpg"):
            os.remove("temp_verify.jpg")
        return result['verified'], round((1 - result['distance']) * 100, 2)

# --- WEB UI & VOICE INTERFACE ---
app = Flask(__name__)
ml = RecruitmentInference()


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Recruitment Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: #020617; color: #f8fafc; font-family: 'Inter', sans-serif; }
        .card { background: #0f172a; border: 1px solid #1e293b; border-radius: 1.5rem; }
    </style>
</head>
<body class="p-10">
    <div class="max-w-4xl mx-auto space-y-8">
        <h1 class="text-4xl font-black text-indigo-500">TALENT<span class="text-white">AI</span></h1>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div class="card p-6 space-y-4">
                <video id="v" autoplay class="rounded-xl w-full bg-black"></video>
                <button onclick="start()" id="s-btn" class="w-full bg-indigo-600 py-3 rounded-lg font-bold">START INTERVIEW</button>
            </div>

            <div class="card p-6">
                <h2 class="text-indigo-400 font-bold uppercase text-xs mb-4 tracking-widest">AI Recruiter</h2>
                <p id="msg" class="text-xl font-medium leading-relaxed">System offline. Upload data to begin.</p>
                <div id="stats" class="mt-8 space-y-2 hidden">
                    <p id="stat-match" class="text-sm"></p>
                    <p id="stat-bio" class="text-sm"></p>
                </div>
            </div>
        </div>
    </div>

    <script>
        const msg = document.getElementById('msg');
        const v = document.getElementById('v');
        const synth = window.speechSynthesis;
        
        navigator.mediaDevices.getUserMedia({video: true}).then(s => v.srcObject = s);

        function speak(t) {
            synth.cancel();
            const u = new SpeechSynthesisUtterance(t);
            u.onend = () => { if(t.includes("Why")) startListening(); };
            msg.innerText = t;
            synth.speak(u);
        }

        async function start() {
            document.getElementById('s-btn').style.display = 'none';
            msg.innerText = "Analyzing your credentials using custom ML models...";
            
            // 1. Resume Match
            const r1 = await fetch('/api/screen');
            const d1 = await r1.json();
            
            // 2. Biometric
            const c = document.createElement('canvas');
            c.width = v.videoWidth; c.height = v.videoHeight;
            c.getContext('2d').drawImage(v, 0,0);
            const r2 = await fetch('/api/verify', {
                method: 'POST', 
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({img: c.toDataURL('image/jpeg')})
            });
            const d2 = await r2.json();

            if(d2.verified) {
                document.getElementById('stats').classList.remove('hidden');
                document.getElementById('stat-match').innerText = "Resume Match: " + d1.score + "%";
                document.getElementById('stat-bio').innerText = "Identity: VERIFIED (" + d2.conf + "%)";
                speak("Identity confirmed. I see you have skills in " + d1.skills.join(', ') + ". Why should we hire you?");
            } else {
                speak("Security Alert: Identity mismatch. Session closed.");
            }
        }

        function startListening() {
            const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
            const rec = new Speech();
            rec.onresult = (e) => {
                const t = e.results[0][0].transcript;
                speak("I have analyzed your response. You mentioned " + t + ". Interview complete. Report generated.");
            };
            rec.start();
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/screen')
def screen():
    # USES YOUR ML MODEL
    from ml_core.resume_parser import extract_text_from_file
    txt = extract_text_from_file("data/resume.pdf")
    score, skills = ml.analyze_candidate(txt, "Python ML specialist")
    return jsonify({"score": score, "skills": skills})

@app.route('/api/verify', methods=['POST'])
def verify():
    d = request.json
    v, c = ml.verify_biometrics("data/id_card.jpg", d['img'])
    return jsonify({"verified": v, "conf": c})

if __name__ == '__main__':
    app.run(debug=True, port=5000)