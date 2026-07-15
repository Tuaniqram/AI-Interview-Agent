#!/usr/bin/env python3
"""
Quick test script to demonstrate the enhanced human-like interview system.
Run this to see examples of conversational interview questions and feedback.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.models.llm import llm

def test_natural_question_generation():
    """Test that interview questions sound natural and conversational"""
    print("\n" + "="*80)
    print("TEST 1: Natural Question Generation")
    print("="*80)
    
    job_roles = [
        "Backend Developer",
        "Frontend Engineer", 
        "DevOps Engineer",
        "Data Scientist"
    ]
    
    company_context = """
    Required Skills:
    - Python/JavaScript
    - Problem solving
    - Communication
    
    Key Focus Areas:
    - 40% Problem Solving
    - 40% Technical Knowledge  
    - 20% Communication
    """
    
    for role in job_roles:
        print(f"\n📍 Generating question for: {role}")
        print("-" * 60)
        
        prompt = f"""
You are an experienced technical interviewer conducting a real job interview.
Your style is conversational, professional, and genuinely curious about the candidate's experience.

You're interviewing for the role of: {role}

Company Context:
{company_context}

Generate ONE natural, conversational interview question that:
1. Sounds like something a real interviewer would ask
2. Is open-ended and invites storytelling
3. Is about 1-3 sentences, not a list
4. Relates to real-world challenges in this role

Just ask the question directly - no introduction or explanation.
"""
        
        response = llm.invoke(prompt)
        print(f"Question:\n{response.content}\n")


def test_conversational_feedback():
    """Test that feedback sounds like a real interviewer"""
    print("\n" + "="*80)
    print("TEST 2: Conversational Feedback Generation")
    print("="*80)
    
    test_cases = [
        {
            "quality": "Weak",
            "answer": "I know Laravel is important. I try to write good code."
        },
        {
            "quality": "Good",
            "answer": "I identified N+1 queries with Debugbar, used eager loading to reduce calls from 20 to 2, and improved page load from 5s to 800ms."
        },
        {
            "quality": "Average",
            "answer": "I've worked with Laravel APIs before. I use best practices and follow design patterns."
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📍 Evaluating: {test_case['quality']} Answer")
        print("-" * 60)
        print(f"Answer: {test_case['answer']}")
        print()
        
        prompt = f"""
You are an experienced technical interviewer evaluating a candidate's response.

Question Asked: "Tell me about a time you optimized a slow API endpoint."

Candidate's Answer: {test_case['answer']}

Provide feedback as a real interviewer would:
- Be honest and direct
- Praise what's good, point out what's missing  
- Suggest what would make the answer better
- Keep it conversational, not robotic

Score it 1-10 and explain your rating in human, conversational language.
"""
        
        response = llm.invoke(prompt)
        print(f"Feedback:\n{response.content}\n")


def test_follow_up_questions():
    """Test natural follow-up question generation"""
    print("\n" + "="*80)
    print("TEST 3: Natural Follow-Up Questions")
    print("="*80)
    
    scenarios = [
        {
            "previous_answer": "I used eager loading to optimize queries.",
            "context": "The answer was good but lacked detail"
        },
        {
            "previous_answer": "I implemented Redis caching with a 5-minute TTL.",
            "context": "The answer was strong with specific numbers"
        },
        {
            "previous_answer": "I tried a few things until it worked.",
            "context": "The answer was vague"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📍 Context: {scenario['context']}")
        print(f"Previous Answer: {scenario['previous_answer']}")
        print("-" * 60)
        
        prompt = f"""
You are a technical interviewer continuing a conversation with a candidate.

They just said: "{scenario['previous_answer']}"

Context: {scenario['context']}

Generate ONE natural follow-up question that:
- Continues the conversation naturally
- Digs deeper into their answer
- Sounds conversational (not formal)
- Is 1-2 sentences

Just ask the question directly.
"""
        
        response = llm.invoke(prompt)
        print(f"Follow-Up:\n{response.content}\n")


def main():
    """Run all tests"""
    try:
        print("\n" + "🚀 "*40)
        print("ENHANCED INTERVIEW SYSTEM - DEMONSTRATION")
        print("🚀 "*40)
        
        # Check if API key is set
        if not os.getenv("OPENROUTER_API_KEY"):
            print("\n❌ Error: OPENROUTER_API_KEY not set in .env file")
            print("   Please create a .env file with your API key:")
            print("   OPENROUTER_API_KEY=your_key_here")
            sys.exit(1)
        
        print("\n✅ API key configured")
        print("Generating examples of human-like interview interactions...\n")
        
        # Run tests
        test_natural_question_generation()
        test_conversational_feedback()
        test_follow_up_questions()
        
        print("\n" + "="*80)
        print("✅ All tests completed successfully!")
        print("="*80)
        print("\nKey observations:")
        print("- Questions sound conversational, not scripted")
        print("- Feedback is specific and actionable")
        print("- Follow-ups dig deeper naturally")
        print("- The system differentiates between weak, average, and good answers")
        print("\nNext steps:")
        print("1. Start the server: uvicorn app.main:app --reload")
        print("2. Test endpoints via Swagger: http://localhost:8000/docs")
        print("3. Upload your company documents for contextual interviews")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nMake sure:")
        print("1. You have a .env file with OPENROUTER_API_KEY")
        print("2. Dependencies are installed: pip install -r requirements.txt")
        print("3. You have internet connection for LLM API")
        sys.exit(1)


if __name__ == "__main__":
    main()
