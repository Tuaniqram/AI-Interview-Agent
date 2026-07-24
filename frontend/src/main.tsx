import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { GoogleOAuthProvider } from '@react-oauth/google'
import { App } from './App'
import './assets/tailwind.css'
import { InterviewProvider } from './state/interviewStore'
import { AuthProvider } from './contexts/AuthContext'
import { OrgProvider } from './contexts/OrgContext'
import { CandidateAuthProvider } from './contexts/CandidateAuthContext'
import { ToastProvider } from './components/shared/Toast'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
        <AuthProvider>
          <OrgProvider>
            <CandidateAuthProvider>
              <InterviewProvider>
                <ToastProvider>
                  <App />
                </ToastProvider>
              </InterviewProvider>
            </CandidateAuthProvider>
          </OrgProvider>
        </AuthProvider>
      </GoogleOAuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
