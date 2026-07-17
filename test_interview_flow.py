"""
Comprehensive Test Suite for AI Interview Flow
Tests the complete interview system based on the flow from interviewv1.html

Endpoints Tested:
1. GET /companies/ - Load companies
2. POST /companies/{company_id}/interview/session - Start interview
3. POST /companies/{company_id}/interview/session/{session_id}/next - Get next question
4. POST /companies/{company_id}/interview/answer - Submit candidate answer
5. GET /companies/{company_id}/interview/session/{session_id} - Get session status
"""

import requests
import json
import time
import uuid
from typing import Optional, Dict, Any

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class InterviewTestSuite:
    """Complete test suite for interview system flow"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.token = Colors
        self.results = {
            'passed': 0,
            'failed': 0,
            'tests': []
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log test results with colors"""
        prefix = {
            "PASS": self.token.GREEN,
            "FAIL": self.token.RED,
            "INFO": self.token.BLUE,
            "STEP": self.token.CYAN
        }.get(level, "")
        
        print(f"{prefix}[{level}]{self.token.ENDC} {message}")
    
    def test_get_companies(self):
        """Test 1: Load companies from API"""
        print(f"\n{self.token.BOLD}TEST 1: Load Companies{self.token.ENDC}")
        
        try:
            response = requests.get(f"{self.base_url}/companies/")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            data = response.json()
            assert isinstance(data, list), "Expected list of companies"
            
            companies = data
            print(f"✓ Successfully loaded {len(companies)} companies")
            
            if companies:
                return companies[0]['id']  # Return first company ID
            else:
                self.log("No companies found. Cannot proceed with tests.", "FAIL")
                self.results['failed'] += 1
                return None
                
        except Exception as e:
            self.log(f"Failed to load companies: {str(e)}", "FAIL")
            self.results['failed'] += 1
            return None
    
    def test_start_interview_session(self, company_id: int, job_role: str):
        """Test 2: Start a new interview session"""
        print(f"\n{self.token.BOLD}TEST 2: Start Interview Session{self.token.ENDC}")
        
        try:
            url = f"{self.base_url}/companies/{company_id}/interview/session"
            payload = {"job_role": job_role}
            
            self.log(f"Requesting session with job role: {job_role}", "STEP")
            response = requests.post(url, json=payload)
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            data = response.json()
            
            # Verify response structure
            assert "session_id" in data, "Session ID missing from response"
            assert "current_phase" in data, "Current phase missing from response"
            assert "question_number" in data, "Question number missing from response"
            assert "total_questions" in data, "Total questions missing from response"
            
            print(f"✓ Session created successfully")
            print(f"  Session ID: {data['session_id']}")
            print(f"  Phase: {data['current_phase']}")
            print(f"  Question: {data['question_number']}/ {data['total_questions']}")
            
            return data['session_id']
            
        except Exception as e:
            self.log(f"Failed to start interview session: {str(e)}", "FAIL")
            self.results['failed'] += 1
            return None
    
    def test_get_next_question(self, company_id: int, session_id: str):
        """Test 3: Get the next interview question"""
        print(f"\n{self.token.BOLD}TEST 3: Get Next Question{self.token.ENDC}")
        
        try:
            url = f"{self.base_url}/companies/{company_id}/interview/session/{session_id}/next"
            
            # Get current question number from session
            session_response = requests.get(
                f"{self.base_url}/companies/{company_id}/interview/session/{session_id}"
            )
            current_qn = session_response.json().get('question_number', 0)
            
            self.log(f"Requesting next question (question {current_qn + 1})", "STEP")
            response = requests.post(url, json={})
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            data = response.json()
            
            # Verify response structure
            assert "question" in data, "Question missing from response"
            assert "phase" in data, "Phase missing from response"
            assert "question_number" in data, "Question number missing from response"
            assert "difficulty_level" in data, "Difficulty level missing from response"
            assert "interview_status" in data, "Interview status missing from response"
            
            print(f"✓ Question retrieved successfully")
            print(f"  Question({data['question_number']}): {data['question'][:100]}...")
            print(f"  Phase: {data['phase']}")
            print(f"  Difficulty: {data['difficulty_level']}")
            print(f"  Status: {data['interview_status']}")
            
            return data
            
        except Exception as e:
            self.log(f"Failed to get next question: {str(e)}", "FAIL")
            if hasattr(e, 'response') and e.response:
                self.log(f"Response: {e.response.text}", "FAIL")
            self.results['failed'] += 1
            return None
    
    def test_submit_answer(self, company_id: int, session_id: str):
        """Test 4: Submit candidate answer (THE KEY FIX)"""
        print(f"\n{self.token.BOLD}TEST 4: Submit Candidate Answer{self.token.ENDC}")
        
        # Get current state
        session_response = requests.get(
            f"{self.base_url}/companies/{company_id}/interview/session/{session_id}"
        )
        session_data = session_response.json()
        
        try:
            url = f"{self.base_url}/companies/{company_id}/interview/answer"
            
            # Get current session state
            current_phase = session_data.get('current_phase', 'intro')
            question_number = session_data.get('current_question_number', 0)
            job_role = session_data.get('job_role', 'Backend Developer')
            
            # Prepare payload based on the fixed endpoint structure
            # Use defaults if fields are missing
            
            payload = {
                "session_id": session_id,
                "job_role": job_role,
                "question": "Tell me about yourself and your career background. Explain your experience with FastAPI, REST APIs, and backend development.",
                "candidate_answer": "I am a backend developer with experience in Python and FastAPI. I understand RESTful API design principles and can build scalable applications.",
                "conversation_history": "",
                "current_phase": current_phase,
                "difficulty_level": 1,
                "question_number": question_number
            }
            
            self.log("Testing the FIXED endpoint structure:", "STEP")
            self.log(f"Request URL: {url}", "INFO")
            self.log(f"Request Body Structure:", "INFO")
            self.log(json.dumps(payload, indent=2), "INFO")
            
            response = requests.post(url, json=payload)
            
            print(f"\n  Status Code: {response.status_code}")
            
            if response.status_code != 200:
                self.log(f"Response: {response.text}", "FAIL")
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            data = response.json()
            
            # Verify response structure
            assert "evaluation" in data, "Evaluation missing from response"
            assert "suggested_follow_up" in data, "Follow-up missing from response"
            assert "phase" in data, "Phase data missing from response"
            assert "question_number" in data, "Question number missing from response"
            assert "difficulty_level" in data, "Difficulty level missing from response"
            assert "interview_status" in data, "Interview status missing from response"
            assert "score" in data, "Score missing from response"
            
            print(f"\n✓ Answer submitted successfully!")
            print(f"  Score: {data['score']}/10")
            print(f"  Feedback: {data['evaluation'][:200]}...")
            print(f"  Suggested Follow-up: {data['suggested_follow_up'][:100]}...")
            print(f"  Next Phase: {data['phase']}")
            print(f"  Question Number: {data['question_number']}")
            print(f"  Difficulty Level: {data['difficulty_level']}")
            print(f"  Status: {data['interview_status']}")
            
            return data
            
        except Exception as e:
            self.log(f"Failed to submit answer: {str(e)}", "FAIL")
            self.results['failed'] += 1
            return None
    
    def test_get_session_status(self, company_id: int, session_id: str):
        """Test 5: Verify session was updated properly"""
        print(f"\n{self.token.BOLD}TEST 5: Verify Session Status{self.token.ENDC}")
        
        try:
            url = f"{self.base_url}/companies/{company_id}/interview/session/{session_id}"
            
            response = requests.get(url)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            data = response.json()
            
            print(f"✓ Session retrieved successfully")
            print(f"  Company ID: {data['company_id']}")
            print(f"  Job Role: {data['job_role']}")
            print(f"  Status: {data['status']}")
            print(f"  Current Phase: {data['current_phase']}")
            print(f"  Question Number: {data['current_question_number']}")
            print(f"  Total Questions: {data['total_questions']}")
            if 'final_score' in data:
                print(f"  Final Score: {data['final_score']}")
            
            return data
            
        except Exception as e:
            self.log(f"Failed to get session status: {str(e)}", "FAIL")
            self.results['failed'] += 1
            return None
    
    def run_full_test_flow(self):
        """Run the complete interview test flow"""
        print(f"\n{self.token.BOLD}{'='*60}")
        print(f"{self.token.BOLD}AI INTERVIEW SYSTEM - COMPREHENSIVE TEST FLOW{self.token.ENDC}")
        print(f"{self.token.BOLD}Testing the fixed /companies/{{company_id}}/interview/answer endpoint{self.token.ENDC}")
        print(f"{self.token.BOLD}{'='*60}{self.token.ENDC}")
        
        # Step 1: Load companies
        company_id = self.test_get_companies()
        if not company_id:
            return False
        
        # Step 2: Start interview session
        session_id = self.test_start_interview_session(company_id, "Backend Developer")
        if not session_id:
            return False
        
        # Step 3: Get first question
        if not self.test_get_next_question(company_id, session_id):
            return False
        
        # Step 4: Submit answer (THE KEY TEST)
        evaluation_data = self.test_submit_answer(company_id, session_id)
        if not evaluation_data:
            return False
        
        # Step 5: Verify session updated
        self.test_get_session_status(company_id, session_id)
        
        # Print summary
        print(f"\n{self.token.BOLD}{'='*60}")
        print(f"{self.token.BOLD}TEST SUMMARY{self.token.ENDC}")
        print(f"{self.token.BOLD}{'='*60}")
        print(f"{self.token.GREEN}Passed: {self.results['passed']}{self.token.ENDC}")
        print(f"{self.token.RED}Failed: {self.results['failed']}{self.token.ENDC}")
        print(f"{self.token.BOLD}Total: {self.results['passed'] + self.results['failed']}{self.token.ENDC}")
        print(f"{self.token.BOLD}{'='*60}{self.token.ENDC}")
        
        return self.results['failed'] == 0
    
    def run_individual_tests(self):
        """Run individual tests for debugging"""
        print(f"\n{self.token.BOLD}{'='*60}")
        print(f"{self.token.BOLD}RUNNING INDIVIDUAL TESTS{self.token.ENDC}")
        print(f"{self.token.BOLD}{'='*60}{self.token.ENDC}")
        
        while True:
            print(f"\n{self.token.CYAN}Available Tests:{self.token.ENDC}")
            print("1. Test Get Companies")
            print("2. Test Start Session")
            print("3. Test Get Next Question")
            print("4. Test Submit Answer (FIXED ENDPOINT)")
            print("5. Test Session Status")
            print("6. Run Full Test Flow")
            print("0. Exit")
            
            choice = input(f"\n{self.token.CYAN}Select test number: {self.token.ENDC}")
            
            if choice == "1":
                self.test_get_companies()
            elif choice == "2":
                company_id = int(input("Enter company ID: "))
                job_role = input("Enter job role (e.g., 'Backend Developer'): ")
                self.test_start_interview_session(company_id, job_role)
            elif choice == "3":
                company_id = int(input("Enter company ID: "))
                session_id = input("Enter session ID: ")
                self.test_get_next_question(company_id, session_id)
            elif choice == "4":
                company_id = int(input("Enter company ID: "))
                session_id = input("Enter session ID: ")
                self.test_submit_answer(company_id, session_id)
            elif choice == "5":
                company_id = int(input("Enter company ID: "))
                session_id = input("Enter session ID: ")
                self.test_get_session_status(company_id, session_id)
            elif choice == "6":
                self.run_full_test_flow()
            elif choice == "0":
                break
            else:
                print(f"{self.token.RED}Invalid choice{self.token.ENDC}")

def print_expected_request_format():
    """Print the expected request format for the fixed endpoint"""
    print(f"\n{Colors.BOLD}{'='*60}")
    print(f"{Colors.BOLD}EXPECTED REQUEST FORMAT FOR FIXED ENDPOINT{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*60}")
    
    request = {
        "session_id": "abc123-def456-ghi789",
        "job_role": "Backend Developer",
        "question": "Explain REST API",
        "candidate_answer": "My answer here",
        "conversation_history": "",
        "current_phase": "technical",
        "difficulty_level": 1,
        "question_number": 1
    }
    
    print(json.dumps(request, indent=2))
    
    print(f"\n{Colors.YELLOW}Key Note:{Colors.ENDC}")
    print("All fields including session_id are now inside the JSON body.")
    print("NOT sent as query parameter anymore.")

def main():
    """Main entry point"""
    print(f"\n{Colors.BOLD}{'='*60}")
    print(f"{Colors.BOLD}AI INTERVIEW FLOW TEST SUITE{Colors.ENDC}")
    print(f"Testing the fix for 422 Unprocessable Entity error")
    print(f"{Colors.BOLD}{'='*60}")
    
    # Print expected format
    print_expected_request_format()
    
    # Use default URL
    base_url = "http://127.0.0.1:8000"
    
    # Override if environment variable is set
    import os
    if os.getenv("API_URL"):
        base_url = os.getenv("API_URL")
    
    print(f"{Colors.CYAN}Using API URL: {base_url}{Colors.ENDC}")
    
    # Initialize test suite
    suite = InterviewTestSuite(base_url)
    suite.run_full_test_flow()

if __name__ == "__main__":
    main()