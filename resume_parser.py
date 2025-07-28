import spacy
import re
import json
import sys
import PyPDF2
import os
from typing import Dict, List, Optional

class ResumeParser:
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            raise Exception("Spacy model 'en_core_web_sm' not found. Install it with: python -m spacy download en_core_web_sm")

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        try:
            if isinstance(pdf_path, str):
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    return text
            else:
                reader = PyPDF2.PdfReader(pdf_path)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text
        except FileNotFoundError:
            raise FileNotFoundError(f"Error: File not found: {pdf_path}")
        except Exception as e:
            raise Exception(f"Error reading PDF: {e}")

    def extract_name(self, doc) -> Optional[str]:
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text
        return None

    def extract_email(self, text: str) -> Optional[str]:
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(email_pattern, text)
        return match.group(0) if match else None

    def extract_phone(self, text: str) -> Optional[str]:
        phone_pattern = r'(\+?\d{1,2}\s?)?(\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}'
        match = re.search(phone_pattern, text)
        return match.group(0) if match else None

    def extract_education(self, doc) -> List[str]:
        education_keywords = ['university', 'college', 'institute', 'school', 'bachelor', 'master', 'phd', 'degree']
        education = []
        for sent in doc.sents:
            if any(keyword in sent.text.lower() for keyword in education_keywords):
                education.append(sent.text.strip())
        return education if education else ["No education details found"]

    def extract_experience(self, doc, text: str) -> List[Dict]:
        experience_keywords = ['experience', 'worked', 'employed', 'position', 'role', 'job', 'project', 'developed', 'built', 'hackathon']
        date_pattern = r'(\d{4}\s*-\s*\d{4}|\d{4}\s*-\s*Present|Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?\s+\d{4}\s*-\s*(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)?\s*\d{4}|Present)'
        company_pattern = r'(?:at|with|for)\s+([A-Z][\w\s&,-]+?)(?=\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{4}|$))'
        project_pattern = r'(?:Project|Hackathon)\s*:\s*([A-Za-z\s]+)(?=\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{4}|$))'

        experiences = []
        current_exp = {}
        for sent in doc.sents:
            sent_text = sent.text.strip()
            if any(keyword in sent_text.lower() for keyword in experience_keywords) or re.search(date_pattern, sent_text) or re.search(company_pattern, sent_text) or re.search(project_pattern, sent_text):
                project_match = re.search(project_pattern, sent_text)
                if project_match and not current_exp.get('title'):
                    current_exp['title'] = project_match.group(1).strip()

                company_match = re.search(company_pattern, sent_text)
                if company_match and not current_exp.get('company'):
                    current_exp['company'] = company_match.group(1).strip()

                date_match = re.search(date_pattern, sent_text)
                if date_match and not current_exp.get('dates'):
                    current_exp['dates'] = date_match.group(0).strip()

                current_exp.setdefault('description', []).append(sent_text)

                if current_exp.get('title') or current_exp.get('company') or current_exp.get('dates'):
                    experiences.append(current_exp)
                    current_exp = {}

        return experiences if experiences else [{"title": "No experience details found", "company": "", "dates": "", "description": []}]

    def extract_skills(self, text: str) -> List[str]:
        skill_keywords = [
            'python', 'java', 'javascript', 'sql', 'html', 'css', 'react', 'node.js',
            'machine learning', 'data analysis', 'project management', 'communication',
            'mongodb', 'express.js', 'angular', 'vue.js', 'typescript', 'aws', 'docker'
        ]
        skills = []
        for skill in skill_keywords:
            if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
                skills.append(skill)
        return skills if skills else ["No skills identified"]

    def parse(self, resume_text: str) -> Dict:
        doc = self.nlp(resume_text)
        return {
            "name": self.extract_name(doc),
            "email": self.extract_email(resume_text),
            "phone": self.extract_phone(resume_text),
            "education": self.extract_education(doc),
            "experience": self.extract_experience(doc, resume_text),
            "skills": self.extract_skills(resume_text)
        }

def main():
    if len(sys.argv) != 2:
        print("Usage: python resume_parser.py <resume_file.pdf>")
        sys.exit(1)

    input_file = os.path.abspath(sys.argv[1])  # Use absolute path
    if not input_file.lower().endswith('.pdf'):
        print("Error: Input file must be a PDF.")
        sys.exit(1)

    parser = ResumeParser()
    resume_text = parser.extract_text_from_pdf(input_file)
    result = parser.parse(resume_text)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()