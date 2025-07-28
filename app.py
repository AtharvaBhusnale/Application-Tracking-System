from flask import Flask, request, jsonify, render_template
from resume_parser import ResumeParser
from database import ResumeDatabase
import os

app = Flask(__name__)
db = ResumeDatabase()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "File must be a PDF"}), 400

    try:
        parser = ResumeParser()
        resume_text = parser.extract_text_from_pdf(file)
        parsed_data = parser.parse(resume_text)
        resume_id = db.insert_resume(parsed_data)
        return jsonify({"resume_id": resume_id, "data": parsed_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/resumes', methods=['GET'])
def get_resumes():
    try:
        resumes = db.get_all_resumes()
        return jsonify(resumes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/resume/<int:resume_id>', methods=['GET'])
def get_resume(resume_id):
    try:
        resume = db.get_resume(resume_id)
        if resume:
            return jsonify(resume)
        return jsonify({"error": "Resume not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)