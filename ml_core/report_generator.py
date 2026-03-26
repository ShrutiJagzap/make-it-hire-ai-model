import json
from datetime import datetime

class ReportGenerator:
    @staticmethod
    def generate(name, data):
        overall = (data['resume_score'] * 0.4) + (data['interview_score'] * 0.4) + (data['bio_score'] * 0.2)
        verdict = "STRONG HIRE" if overall >= 75 else "PROCEED" if overall >= 50 else "REJECT"
        
        report_md = f"""# Final Evaluation: {name}
## 1. Candidate Overview
* **Date:** {datetime.now().strftime("%Y-%m-%d")}
* **Biometric Trust:** {data['bio_score']}% (Verified)

## 2. Technical Screening (Resume vs. JD)
* **Match Score:** {data['resume_score']}%
* **Skills Found:** {", ".join(data['skills_found'])}

## 3. Interview Performance
* **Accuracy Score:** {data['interview_score']}%
* **Rating:** {"Expert" if data['interview_score'] > 75 else "Competent"}

## 4. Behavioral Analysis
* **Emotion:** {data['engagement']['emotion']}
* **Status:** {data['engagement']['status']} Engagement

## 5. Final Verdict
* **Overall Score:** {round(overall, 2)}%
* **Recommendation:** {verdict}

## 6. Next Steps
* Technical challenge on {data['skills_found'][0] if data['skills_found'] else "Core Logic"}.
"""
        with open("final_report.md", "w") as f: f.write(report_md)
        with open("final_report.json", "w") as f: json.dump(data, f)
        return report_md