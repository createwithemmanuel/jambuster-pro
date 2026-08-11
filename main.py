
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
import os

app = FastAPI(title="JAMBuster AI - Powered by Groq")

# Allow your frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================
# 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
# ================================================
GROQ_API_KEY = "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"

# Initialize the Groq client
client = Groq(api_key=GROQ_API_KEY)

# ================================================
# MAIN ENDPOINTS
# ================================================

@app.get("/")
def root():
    return {
        "message": "JAMBuster is Alive!",
        "student": "Ogundipe Emmanuel",
        "mission": "Built by a student, for students",
        "status": f"AI Powered by Groq 🇳🇬"
    }

@app.get("/ask")
async def ask(question: str, subject: str = "General"):
    """Ask the AI to explain anything in Pidgin"""
    
    prompt = f"""
    You are a JAMB tutor. Answer this question in Pidgin English and simple English.
    
    Subject: {subject}
    Question: {question}
    
    Instructions:
    - Start with "Make I break this down small-small."
    - Use Nigerian examples (food, football, market)
    - Keep it simple for SS3 students
    - If it's math, show step-by-step working
    - If it's physics, explain the formula first
    - If it's chemistry, use cooking analogies
    - End with "Any other question? Just ask me o!"
    """
    
    return await call_groq(prompt)

@app.get("/generate")
async def generate(topic: str, count: int = 10):
    """Generate fresh JAMB-style questions on any topic"""
    
    prompt = f"""
    Generate {count} JAMB-style questions on the topic: {topic}
    
    Format each question like this:
    Q1: [Question]
    A. [Option A]
    B. [Option B]
    C. [Option C]
    D. [Option D]
    Answer: [Correct Letter]
    Explanation: [Simple explanation in Pidgin]
    
    Make it suitable for SS3 students in Nigeria.
    Use Pidgin English where appropriate.
    """
    
    return await call_groq(prompt)

@app.get("/grade")
async def grade(question: str, student_answer: str):
    """Grade a student's answer and give feedback"""
    
    prompt = f"""
    Grade this answer like a JAMB examiner.
    
    Question: {question}
    Student's Answer: {student_answer}
    
    Instructions:
    1. Tell if the answer is correct or wrong
    2. Explain why in simple Pidgin English
    3. Give the correct answer if wrong
    4. Give encouragement like "No worry, you try! Next time you go get am!"
    """
    
    return await call_groq(prompt)

@app.get("/analyze")
async def analyze(subject: str, performance: str):
    """Analyze student's weak areas"""
    
    prompt = f"""
    Analyze this student's performance in {subject}.
    
    Their performance: {performance}
    
    Instructions:
    1. Identify 3 topics they are weak in
    2. Suggest how to improve
    3. Give motivation in Pidgin English
    4. Create a study plan for 2 weeks
    """
    
    return await call_groq(prompt)

# ================================================
# THE GROQ AI ENGINE
# ================================================

async def call_groq(prompt: str):
    """Call the Groq API and return the response"""
    try:
        # Use the llama-3.3-70b-versatile model for great performance
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile", # You can also try "llama-3.1-70b-versatile" or "mixtral-8x7b-32768"[reference:17]
        )

        # Extract the AI's response text
        ai_response = chat_completion.choices[0].message.content

        return {
            "success": True,
            "response": ai_response,
            "powered_by": "Groq (Llama 3.3 70B) 🇳🇬"
        }
                
    except Exception as e:
        return {
            "success": False,
            "response": f"Omo! Something went wrong. No worry, we go fix am!",
            "error": str(e),
            "tip": "Check your internet connection and API key."
        }

@app.get("/health")
def health():
    return {
        "status": "Healthy",
        "brain": "Groq (Llama 3.3 70B)",
        "builder": "Ogundipe Emmanuel",
        "version": "1.0.0"
    }
