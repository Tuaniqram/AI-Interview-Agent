import React from 'react'
import ReactDOM from 'react-dom/client'
import { App } from './App'
import './assets/tailwind.css'
import { InterviewProvider } from './state/interviewStore'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <InterviewProvider>
      <App />
    </InterviewProvider>
  </React.StrictMode>,
)