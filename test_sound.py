import subprocess
import os

text = "Testing the AI Recruitment Voice Engine. Can you hear me?"

print("Trying Method 1 (PowerShell)...")
ps = f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")'
subprocess.run(["powershell", "-Command", ps])

print("Trying Method 2 (VBScript)...")
with open("test.vbs", "w") as f:
    f.write(f'CreateObject("SAPI.SpVoice").Speak "{text}"')
os.system("cscript //nologo test.vbs")
os.remove("test.vbs")

print("If you heard nothing, check your Windows Volume Mixer and ensure your speakers are on.")