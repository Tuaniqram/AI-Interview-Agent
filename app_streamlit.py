#!/usr/bin/env python3
"""
Streamlit app for AI Interview Agent - Works perfectly in Google Colab!
Run: streamlit run app_streamlit.py
"""

import streamlit as st
import requests
import json
from datetime import datetime

# Page config
st.set_page_config(
    page_title="AI Interview Agent",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stButton > button {
        width: 100%;
        padding: 10px;
        font-size: 16px;
    }
    .message-box {
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .interviewer-msg {
        background-color: #e8e8ff;
        border-left: 4px solid #667eea;
    }
    .candidate-msg {
        background-color: #667eea;
        color: white;
        border-right: 4px solid #764ba2;
    }
    .feedback-msg {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
    }
    .score-badge {
        display: inline-block;
        background: #667eea;
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("# 🎯 AI Interview Agent")
st.markdown("### Real-time Conversational Technical Interview")

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Settings")
    
    api_url = st.text_input(
        "API URL",
        value="http://localhost:8000",
        help="Enter your API endpoint (local or ngrok URL)"
    )
    
    job_role = st.selectbox(
        "Job Role",
        [
            "Backend Developer",
            "Frontend Engineer",
            "DevOps Engineer",
            "Data Scientist",
            "Full Stack Developer",
            "Mobile Developer",
            "QA Engineer"
        ]
    )
    
    company_context = st.text_area(
        "Company Context (Optional)",
        height=100,
        help="Provide company-specific context for better questions"
    )
    
    st.divider()
    
    if st.button("🔄 Reset Interview", use_container_width=True):
        st.session_state.messages = []
        st.session_state.scores = []
        st.session_state.interview_started = False
        st.session_state.current_question = ""
        st.rerun()
    
    st.divider()
    
    # Stats
    if st.session_state.get('interview_started', False):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Turns", len(st.session_state.get('messages', [])) // 2)
        with col2:
            if st.session_state.get('scores', []):
                avg_score = sum(st.session_state.scores) / len(st.session_state.scores)
                st.metric("Avg Score", f"{avg_score:.1f}/10")

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'interview_started' not in st.session_state:
    st.session_state.interview_started = False
if 'current_question' not in st.session_state:
    st.session_state.current_question = ""
if 'scores' not in st.session_state:
    st.session_state.scores = []

# Main content area
col1, col2 = st.columns([3, 1])

with col2:
    start_btn = st.button("🚀 Start Interview", use_container_width=True, type="primary")

if start_btn:
    if not job_role:
        st.error("Please select a job role!")
    else:
        st.session_state.interview_started = True
        st.session_state.messages = []
        st.session_state.scores = []
        st.session_state.current_question = ""

# Chat display area
chat_container = st.container()

with chat_container:
    if not st.session_state.interview_started:
        st.info("👋 Select a job role and click 'Start Interview' to begin")
    else:
        # Display all messages
        for i, msg in enumerate(st.session_state.messages):
            if msg['type'] == 'interviewer':
                st.markdown(f"""
                <div class="message-box interviewer-msg">
                    <b>🎤 Interviewer:</b><br>
                    {msg['content']}
                </div>
                """, unsafe_allow_html=True)
            elif msg['type'] == 'candidate':
                st.markdown(f"""
                <div class="message-box candidate-msg">
                    <b>You:</b><br>
                    {msg['content']}
                </div>
                """, unsafe_allow_html=True)
            elif msg['type'] == 'feedback':
                st.markdown(f"""
                <div class="message-box feedback-msg">
                    <b>📋 Feedback:</b><br>
                    {msg['content']}
                </div>
                """, unsafe_allow_html=True)

# Get first question if interview just started
if st.session_state.interview_started and not st.session_state.current_question:
    with st.spinner("Interviewer is preparing the first question..."):
        try:
            response = requests.post(
                f"{api_url}/interview",
                json={
                    "job_role": job_role,
                    "candidate_answer": ""
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'error' in data:
                    st.error(f"❌ Error: {data['error']}")
                else:
                    st.session_state.current_question = data.get('question', '')
                    st.session_state.messages.append({
                        'type': 'interviewer',
                        'content': st.session_state.current_question
                    })
                    st.rerun()
            else:
                st.error(f"❌ API Error: {response.status_code}")
                st.error(f"Response: {response.text}")
        except requests.exceptions.ConnectionError:
            st.error("❌ Connection failed! Make sure:")
            st.error("1. API server is running: `uvicorn app.main:app --reload`")
            st.error(f"2. API URL is correct: {api_url}")
            st.error("3. ngrok tunnel is active (if using ngrok)")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Input area
if st.session_state.interview_started and st.session_state.current_question:
    st.divider()
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        user_answer = st.text_area(
            "Your Answer",
            height=120,
            placeholder="Type your answer here...",
            key="answer_input"
        )
    
    with col2:
        st.write("")  # Spacing
        submit_btn = st.button("📤 Send", use_container_width=True, type="primary")
    
    if submit_btn and user_answer.strip():
        # Add user message
        st.session_state.messages.append({
            'type': 'candidate',
            'content': user_answer
        })
        
        with st.spinner("Interviewer is evaluating your answer..."):
            try:
                response = requests.post(
                    f"{api_url}/interview/evaluate-with-followup",
                    json={
                        "job_role": job_role,
                        "question": st.session_state.current_question,
                        "candidate_answer": user_answer,
                        "company_context": company_context or ""
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'error' in data:
                        st.error(f"❌ Error: {data['error']}")
                    else:
                        # Add feedback
                        if 'evaluation' in data:
                            st.session_state.messages.append({
                                'type': 'feedback',
                                'content': data['evaluation']
                            })
                            
                            # Extract score
                            eval_text = data['evaluation']
                            if 'Score:' in eval_text:
                                try:
                                    score_str = eval_text.split('Score:')[1].split('/')[0].strip()
                                    score = int(score_str)
                                    st.session_state.scores.append(score)
                                except:
                                    pass
                        
                        # Add next question
                        if 'suggested_follow_up' in data:
                            st.session_state.current_question = data['suggested_follow_up']
                            st.session_state.messages.append({
                                'type': 'interviewer',
                                'content': st.session_state.current_question
                            })
                        
                        st.rerun()
                else:
                    st.error(f"❌ API Error: {response.status_code}")
                    st.error(f"Response: {response.text}")
            except requests.exceptions.ConnectionError:
                st.error("❌ Connection failed!")
                st.error(f"Make sure API is running at: {api_url}")
            except requests.exceptions.Timeout:
                st.error("❌ Request timeout! API is taking too long to respond.")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# Footer
st.divider()
st.markdown("""
---
**How to use:**
1. Select a job role from the sidebar
2. (Optional) Add company context
3. Click "Start Interview"
4. Answer questions naturally
5. Get instant feedback and follow-up questions

**Tips:**
- Be specific with examples
- Share real project experiences
- Ask clarifying questions if needed
""")
