import spacy
import re
import json
import sys
import os
import PyPDF2
import logging
from typing import Dict, List, Optional
from datetime import datetime

# --- Setup Logging ---
logging.basicConfig(filename='resume_parser.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class ResumeParser:
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            error_msg = "Spacy model 'en_core_web_sm' not found. Install it with: python -m spacy download en_core_web_sm"
            logging.error(error_msg)
            raise Exception(error_msg)

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text
        except FileNotFoundError:
            logging.error(f"File not found: {pdf_path}")
            raise FileNotFoundError(f"Error: File not found: {pdf_path}")
        except Exception as e:
            logging.error(f"Error reading PDF {pdf_path}: {e}")
            raise Exception(f"Error reading PDF: {e}")

    def extract_name(self, doc) -> Optional[str]:
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                # FIX: Clean the name to remove adjacent words like 'Email'
                name = ent.text.strip()
                return name.split('\n')[0].strip()
        return None

    def extract_email(self, text: str) -> Optional[str]:
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(email_pattern, text)
        return match.group(0) if match else None

    def extract_phone(self, text: str) -> Optional[str]:
        phone_pattern = r'(\+?\d{1,2}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'
        match = re.search(phone_pattern, text)
        return match.group(0) if match else None

    def extract_education(self, text: str) -> List[str]:
        qualifications = ['MCA', 'MCS', 'ME', 'BE', 'B.E.', 'B.Tech', 'M.Tech', 'BCA', 'BSc', 'MSc']
        found_education = []
        for qual in qualifications:
            # FIX: Made regex more flexible to handle PDF text extraction quirks
            pattern = r'\b' + re.escape(qual) + r'(?![a-zA-Z])'
            if re.search(pattern, text, re.IGNORECASE):
                # Standardize the output (e.g., B.E. becomes BE)
                found_education.append(qual.replace('.', ''))
        return list(set(found_education)) if found_education else ["No specific qualifications found"]

    def calculate_total_experience(self, text: str) -> float:
        # FIX: Updated regex to handle optional commas in dates (e.g., "February, 2025")
        date_pattern = re.compile(
            r'(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?,?\s+\d{4})\s*-\s*(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?,?\s+\d{4}|\bPresent\b)',
            re.IGNORECASE
        )
        matches = date_pattern.findall(text)
        total_months = 0

        for start_date_str, end_date_str in matches:
            try:
                # Normalize date strings by removing periods and commas
                start_date = datetime.strptime(start_date_str.replace('.', '').replace(',', ''), '%b %Y')
                
                if 'Present' in end_date_str:
                    end_date = datetime.now()
                else:
                    end_date = datetime.strptime(end_date_str.replace('.', '').replace(',', ''), '%b %Y')

                # Ensure start date is before end date
                if start_date < end_date:
                    total_months += (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
            except ValueError:
                continue

        return round(total_months / 12, 1)

    def extract_experience(self, doc) -> List[Dict]:
        experience_keywords = ['experience', 'worked', 'employed', 'position', 'role', 'job', 'project', 'internship']
        experiences = []
        
        experience_doc = self.nlp(doc.text)
        for sent in experience_doc.sents:
            if any(keyword in sent.text.lower() for keyword in experience_keywords):
                experiences.append(sent.text.strip().replace('\n', ' '))

        return experiences if experiences else ["No experience details found"]

    def extract_skills(self, text: str) -> List[str]:
        skill_keywords = [
            'Python', 'Java', 'JavaScript', 'C', 'C++', 'SQL', 'NoSQL', 'HTML', 'CSS', 'React', 'Angular', 'Vue.js', 'Flask',
            'Node.js', 'Express.js', 'Django', 'Spring', 'Machine Learning', 'Data Analysis', 'Pandas',
            'NumPy', 'TensorFlow', 'PyTorch', 'OpenCV', 'AWS', 'Azure', 'Google Cloud', 'Docker', 'Kubernetes', 'Git',
            'JIRA', 'Agile', 'Scrum', 'Project Management', 'Communication', 'MongoDB', 'PostgreSQL', 'MySQL', 'SQLite'
        ]
        skills = []
        for skill in skill_keywords:
            if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
                skills.append(skill)
        return list(set(skills)) if skills else ["No skills identified"]

    def parse(self, resume_text: str) -> Dict:
        doc = self.nlp(resume_text)
        return {
            "name": self.extract_name(doc),
            "email": self.extract_email(resume_text),
            "phone": self.extract_phone(resume_text),
            "education_qualifications": self.extract_education(resume_text),
            "total_experience_years": self.calculate_total_experience(resume_text),
            "experience_summary": self.extract_experience(doc),
            "skills": self.extract_skills(resume_text)
        }

# The main function remains the same
def main():
    if len(sys.argv) != 2:
        print("Usage: python resume_parser.py <resume_file.pdf>")
        sys.exit(1)

    input_file = os.path.abspath(sys.argv[1])
    if not input_file.lower().endswith('.pdf'):
        logging.warning(f"Input file '{input_file}' is not a PDF. Aborting.")
        print("Error: Input file must be a PDF.")
        sys.exit(1)

    try:
        parser = ResumeParser()
        resume_text = parser.extract_text_from_pdf(input_file)
        if not resume_text.strip():
            logging.error(f"Failed to extract text from {input_file}. It might be empty or image-based.")
            print(json.dumps({"error": f"Could not extract text from {input_file}"}, indent=2))
            sys.exit(1)
        
        result = parser.parse(resume_text)
        print(json.dumps(result, indent=2))
        logging.info(f"Successfully parsed: {input_file}")

    except Exception as e:
        logging.error(f"An unexpected error occurred while processing {input_file}: {e}")
        print(json.dumps({"error": f"An unexpected error occurred: {e}"}, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()