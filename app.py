import os
import numpy as np
import spacy
from flask import Flask, request, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv


# Initialize Flask app
app = Flask(__name__)

# Load spaCy model
load_dotenv()


try:
    nlp = spacy.load("en_core_web_md")
    print("Model loaded successfully.")
except OSError:
    print("Model not found. Please run: python -m spacy download en_core_web_md")
    raise

# MongoDB Connection
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    # Warn but don't crash immediately, allow env var to be set later or check during request?
    # Better to crash or warn loudly if this is a strict requirement.
    # User requirement: "Do NOT hardcode MongoDB credentials."
    # Let's assume it might be set in the environment where this runs.
    print("Warning: MONGO_URI environment variable not set.")

def get_db_collection():
    if not MONGO_URI:
        raise ValueError("MONGO_URI environment variable not set")
    client = MongoClient(MONGO_URI)
    db = client["ai_service"]
    return db["company_faqs"]

def cosine_similarity(v1, v2):
    """Compute cosine similarity between two vectors."""
    v1 = np.array(v1)
    v2 = np.array(v2)
    
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
        
    return float(np.dot(v1, v2) / (norm1 * norm2))

@app.route('/train', methods=['POST'])
def train():
    """
    Endpoint to train/update FAQs for a company.
    Input structure:
    {
        "company_id": "companyA",
        "faqs": [
            {"question": "...", "answer": "..."},
            ...
        ]
    }
    """
    data = request.json
    if not data or 'company_id' not in data or 'faqs' not in data:
        return jsonify({"message": "Invalid input. 'company_id' and 'faqs' are required."}), 400

    company_id = data['company_id']
    faqs = data['faqs']
    
    processed_faqs = []
    
    for item in faqs:
        question = item.get('question')
        answer = item.get('answer')
        
        if not question or not answer:
            continue
            
        # Generate embedding
        doc = nlp(question)
        vector = doc.vector.tolist() # Convert numpy array to list for MongoDB storage
        
        processed_faqs.append({
            "question": question,
            "answer": answer,
            "vector": vector
        })

    if not processed_faqs:
         return jsonify({"message": "No valid FAQs provided."}), 400

    try:
        collection = get_db_collection()
        
        # Check if company document exists
        existing_doc = collection.find_one({"company_id": company_id})
        
        if existing_doc:
            # Append new FAQs to existing document
            collection.update_one(
                {"company_id": company_id},
                {"$push": {"faqs": {"$each": processed_faqs}}}
            )
        else:
            # Create new document
            new_doc = {
                "company_id": company_id,
                "faqs": processed_faqs
            }
            collection.insert_one(new_doc)
            
        return jsonify({"message": "Training successful"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ask', methods=['POST'])
def ask():
    """
    Endpoint to answer questions.
    Input structure:
    {
        "company_id": "companyA",
        "question": "..."
    }
    """
    data = request.json
    if not data or 'company_id' not in data or 'question' not in data:
        return jsonify({"message": "Invalid input. 'company_id' and 'question' are required."}), 400
        
    company_id = data['company_id']
    user_question = data['question']
    
    try:
        collection = get_db_collection()
        company_doc = collection.find_one({"company_id": company_id})
        
        if not company_doc:
            return jsonify({"answer": "Company not trained yet."}), 200 # As per requirement
            
        # Generate embedding for the user question
        query_doc = nlp(user_question)
        query_vector = query_doc.vector
        
        best_similarity = -1.0
        best_match = None
        
        faqs = company_doc.get("faqs", [])
        
        for faq in faqs:
            stored_vector = faq.get('vector')
            if not stored_vector:
                continue
                
            similarity = cosine_similarity(query_vector, stored_vector)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = faq
                
        # Threshold check
        SIMILARITY_THRESHOLD = 0.7
        
        if best_similarity >= SIMILARITY_THRESHOLD and best_match:
            return jsonify({
                "answer": best_match['answer'],
                # "similarity": best_similarity, # Not strictly required by prompt output example, but useful for debug. 
                # Prompt output example just says "Return best match".
                # But requirement says "If similarity < 0.7 return ..."
                # Let's return just answer or object? 
                # Prompt says: "Return best match". 
                # Wait, prompt says "If similarity < 0.7 return: 'Sorry, no relevant answer found.'"
                # It doesn't explicitly format the success response for /ask. 
                # Implicitly it usually returns the answer.
                # Let's return the simplified object or just the answer text?
                # The prompt has "Behavior: ... Return best match".
                # And "Return full updated app.py".
                # Standard is usually {"answer": ...}.
                # I'll stick to a reasonable JSON structure. 
            }), 200
        else:
            return jsonify({"answer": "Sorry, no relevant answer found."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run the app
    app.run(host='0.0.0.0', port=5000)
