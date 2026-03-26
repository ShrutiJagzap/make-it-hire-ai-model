import os
import speech_recognition as sr
import subprocess
import requests
import json
import time

class VoiceInterface:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.api_key = "" # Empty string, key provided by env

    def generate_questions(self, skills):
        """Calls Gemini for unlimited questions based on skills."""
        prompt = f"Interviewer: Generate 5 technical questions for skills: {skills}. Return ONLY a JSON object with questions as keys and a list of 3 keywords as values."
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}
        
        for delay in [1, 2, 4]:
            try:
                res = requests.post(url, json=payload).json()
                return json.loads(res['candidates'][0]['content']['parts'][0]['text'])
            except: time.sleep(delay)
        return {"Describe your technical journey?": ["experience", "stack", "projects"]}

    def speak(self, text):
        print(f"\n[AI]: {text}")
        clean = text.replace('"', "")
        cmd = f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{clean}")'
        subprocess.call(["powershell", "-Command", cmd], stderr=subprocess.DEVNULL)

    def listen(self):
        print("\n>>> PRESS ENTER THEN SPEAK <<<")
        input()
        with sr.Microphone() as source:
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                return self.recognizer.recognize_google(audio)
            except: return input("Mic Error. Type Answer: ")