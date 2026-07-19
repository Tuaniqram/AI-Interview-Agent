/**
 * AI Interview Simulator - Alpine.js Application
 */

// Alpine.js App Container
document.addEventListener('alpine:init', () => {
    Alpine.data('interviewApp', () => ({
        // === State Variables ===
        currentView: 'start', // start, interview, question, evaluation, completion
        isLoading: false,
        isEvaluating: false,
        isWaitingForQuestion: false,
        errorMessage: null,
        
        // Session Data
        sessionId: null,
        companyId: null,
        jobRole: null,
        currentPhase: 'intro',
        questionCounter: 0,
        questionsAnswered: 0,
        difficultyLevel: 1,
        totalQuestions: 23,  // Will be set from backend
        interviewStatus: 'in_progress',
        
        // Current Question
        currentQuestion: '',
        
        // User Input
        userAnswer: '',
        
        // Evaluation Results
        evaluation: null,
        finalScore: null,
        finalFeedback: null,
        
        // API Configuration
        form: {
            companyId: null,
            jobRole: 'Software Engineer',
            apiUrl: 'http://localhost:8000',
            currentPhase: 'intro'  // Auto-set, no user selection needed
        },
        
        // Companies from API
        companies: [],
        
        // === Initialization ===
        init() {
            console.log('Alpine.js Interview App Initialized');
            this.fetchCompanies();
        },
        
        // === Company API Methods ===
        async fetchCompanies() {
            try {
                const response = await fetch(`${this.form.apiUrl}/companies/`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                this.companies = await response.json();
                // Auto-select first company
                if (this.companies.length > 0) {
                    this.form.companyId = this.companies[0].id;
                }
                console.log('Loaded companies:', this.companies.length);
            } catch (error) {
                console.warn('Could not fetch companies:', error);
                // Continue with default company ID
                this.form.companyId = 1001;
            }
        },
        
        // === API Methods ===
        async startInterview() {
            this.isLoading = true;
            this.errorMessage = null;
            
            try {
                const response = await fetch(`${this.form.apiUrl}/companies/${this.form.companyId}/interview/session`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        job_role: this.form.jobRole,
                        current_phase: this.form.currentPhase
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
                }
                
                const data = await response.json();
                
                // Initialize session state
                this.sessionId = data.session_id;
                this.companyId = this.form.companyId;
                this.jobRole = this.form.jobRole;
                this.currentPhase = data.current_phase;
                this.questionCounter = 0;
                this.questionsAnswered = 0;
                this.totalQuestions = data.total_questions || 23;  // Use actual total from backend
                this.difficultyLevel = 1;
                this.interviewStatus = 'in_progress';
                this.userAnswer = '';
                this.evaluation = null;
                this.finalScore = null;
                
                console.log('Session created:', data);
                
                // Auto-generate first question
                await this.fetchNextQuestion();
                
            } catch (error) {
                console.error('Failed to start interview:', error);
                this.errorMessage = `Error: ${error.message}`;
            } finally {
                this.isLoading = false;
            }
        },
        
        async fetchNextQuestion() {
            this.isWaitingForQuestion = true;
            this.isEvaluating = false;
            
            try {
                const response = await fetch(
                    `${this.form.apiUrl}/companies/${this.form.companyId}/interview/session/${this.sessionId}/next`,
                    {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            job_role: this.jobRole,
                            conversation_history: '',
                            current_phase: this.currentPhase,
                            question_number: this.questionCounter,
                            difficulty_level: this.difficultyLevel,
                            previous_scores: []
                        })
                    }
                );
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
                }
                
                const data = await response.json();
                
                // Update state with backend's decisions
                this.currentQuestion = data.question;
                this.currentPhase = data.phase;
                this.difficultyLevel = data.difficulty_level;
                this.interviewStatus = data.interview_status;
                
                console.log('Question fetched:', data);
                
                // Show question view
                this.currentView = 'question';
                
            } catch (error) {
                console.error('Failed to fetch question:', error);
                this.errorMessage = `Error fetching question: ${error.message}`;
            } finally {
                this.isWaitingForQuestion = false;
            }
        },
        
        async submitAnswer() {
            if (!this.userAnswer || this.userAnswer.length < 50) {
                alert('Please enter a longer answer (at least 50 characters)');
                return;
            }
            
            this.isEvaluating = true;
            this.errorMessage = null;
            
            try {
                const response = await fetch(
                    `${this.form.apiUrl}/companies/${this.form.companyId}/interview/answer`,
                    {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            job_role: this.jobRole,
                            session_id: this.sessionId,
                            question: this.currentQuestion,
                            candidate_answer: this.userAnswer,
                            conversation_history: '',
                            current_phase: this.currentPhase,
                            difficulty_level: this.difficultyLevel,
                            question_number: this.questionCounter
                        })
                    }
                );
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
                }
                
                const data = await response.json();
                
                // Update with evaluation results
                this.evaluation = data;
                this.difficultyLevel = data.difficulty_level;
                this.questionCounter++;
                this.questionsAnswered++;
                this.userAnswer = '';
                
                console.log('Answer evaluated:', data);
                
                // Show evaluation view
                this.currentView = 'evaluation';
                
                // Check if interview is complete
                if (data.interview_status === 'completed') {
                    await this.fetchSessionSummary();
                }
                
            } catch (error) {
                console.error('Failed to evaluate answer:', error);
                this.errorMessage = `Error evaluating answer: ${error.message}`;
            } finally {
                this.isEvaluating = false;
            }
        },
        
        async goToNextQuestion() {
            console.log('Go to next question clicked', {
                isEvaluating: this.isEvaluating,
                isLoading: this.isLoading,
                currentView: this.currentView
            });
            
            // Set loading state to prevent button clicks during transition
            this.isWaitingForQuestion = true;
            this.isEvaluating = false;
            
            try {
                await this.fetchNextQuestion();
                console.log('Successfully moved to next question');
            } catch (error) {
                console.error('Error going to next question:', error);
                this.isWaitingForQuestion = false;
            }
        },
        
        async fetchSessionSummary() {
            try {
                const response = await fetch(
                    `${this.form.apiUrl}/companies/${this.form.companyId}/interview/review`,
                    {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            session_id: this.sessionId
                        })
                    }
                );
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
                }
                
                const data = await response.json();
                
                // Final statistics
                this.finalScore = {
                    score: data.final_score,
                    total_questions: data.total_questions_answered
                };
                this.finalFeedback = data.evaluation;
                
                console.log('Session summarized:', data);
                
            } catch (error) {
                console.error('Failed to fetch session summary:', error);
                // Use fallback calculation
                const evals = this.evaluation;
                if (evals?.score) {
                    this.finalScore = {
                        score: Math.round(evals.score * 10) / 10,
                        total_questions: this.questionsAnswered
                    };
                }
            }
        },
        
        restartInterview() {
            this.currentView = 'start';
            this.sessionId = null;
            this.form.companyId = this.companyId || this.form.companyId;
            this.form.jobRole = this.jobRole || this.form.jobRole;
            this.form.currentPhase = this.form.currentPhase;
        },
        
        // === Utility Methods ===
        getPhaseColor(phase) {
            const colors = {
                intro: 'bg-blue-500',
                experience: 'bg-yellow-500',
                technical: 'bg-red-500',
                behavioral: 'bg-green-500',
                conclusion: 'bg-purple-500'
            };
            return colors[phase] || 'bg-gray-500';
        },
        
        getPhaseLabel(phase) {
            const labels = {
                intro: 'Intro',
                experience: 'Experience',
                technical: 'Technical',
                behavioral: 'Behavioral',
                conclusion: 'Conclusion'
            };
            return labels[phase] || phase;
        },
        
        getProgressWidth() {
            const total = this.totalQuestions || 23;  // Use dynamic total instead of hardcoded
            const progress = this.questionsAnswered;
            return (progress / total) * 100;
        },
        
        getScoreColorClass(score) {
            if (!score) return '';
            if (score >= 7) return 'text-green-500';
            if (score >= 5) return 'text-yellow-500';
            return 'text-red-500';
        },
        
        getScoreBadgeClass(score) {
            if (!score) return '';
            if (score >= 7) return 'bg-green-100 text-green-800';
            if (score >= 5) return 'bg-yellow-100 text-yellow-800';
            return 'bg-red-100 text-red-800';
        }
    }));
});