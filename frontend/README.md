# 🎯 AI Interview Agent - Frontend v2.0

## Overview

Production-ready React + TypeScript frontend for the AI Interview Agent backend architecture. This frontend is designed to support multiple interview modes:
- ✅ **Typing Mode** - Traditional text-based interviews
- 🚧 **Voice Mode** - Speech-to-text evaluation (extension point)
- 🚧 **Avatar Mode** - AI avatar interviewer (extension point) 
- 🚧 **Real-time Mode** - Live conversation (extension point)

## 🚀 Technology Stack

- **React 18** - UI Framework
- **TypeScript 5** - Type Safety
- **Vite 5** - Build Tool (Fast development)
- **Tailwind CSS 3** - Utility-first styling
- **Axios 1.6** - HTTP Client
- **Lucide React** - Icon Library

## 📁 Architecture

### Layers

```
frontend/
├── src/
│   ├── components/          # React UI Components
│   │   ├── interview/      # Interview mode components
│   │   ├── avatar/         # Avatar mode components
│   │   ├── voice/          # Voice mode components
│   │   └── shared/         # Reusable components
│   ├── services/           # API Service Layer
│   │   ├── apiClient.ts    # Axios wrapper + error handling
│   │   ├── interviewService.ts
│   │   ├── avatarService.ts
│   │   └── speechService.ts (placeholder)
│   ├── controllers/        # Business Logic Layer
│   │   └── interviewController.ts
│   ├── state/              # State Management
│   │   └── interviewStore.tsx
│   ├── types/              # TypeScript Type Definitions
│   │   ├── interview.ts    # Core types
│   │   ├── avatar.ts       # Avatar-specific types
│   │   ├── voice.ts        # Voice-specific types
│   │   ├── api.ts          # API types
│   │   └── common.ts       # Shared types
│   ├── utils/              # Utilities
│   ├── hooks/              # Custom hooks
│   ├── App.tsx             # Root component
│   └── main.tsx            # Entry point
```

## 🔑 Key Principles

### 1. Backend-Driven Everything

**NO HARDCODED VALUES:**

```typescript
// ❌ BAD (old approach)
Question {questionNumber} of 23

// ✅ GOOD (new approach)
Question {state.currentQuestion?.question_number} / {state.session?.total_questions}
```

All interview flow is controlled by backend:
- `total_questions` - from backend
- `phase` - from backend
- `difficulty` - from backend
- `question numbering` - from backend
- `phase transitions` - from backend

### 2. Three-Layer Architecture

```
UI Component (QuestionCard.tsx)
    ↓
Controller (InterviewController.ts)
    ↓
Service (InterviewService.ts)
    ↓
API Client (apiClient.ts)
    ↓
Backend API
```

### 3. Full TypeScript Coverage

All types defined in `src/types/` for type safety across the stack.

## 🏃 Quick Start

### Install Dependencies

```bash
cd frontend
npm install
```

### Start Development Server

```bash
npm run dev
```

Server runs at: `http://localhost:3000`

### Build for Production

```bash
npm run build
npm run preview
```

## 📊 API Integration

### Service Layer

All API calls go through services, not direct fetch:

```typescript
// ❌ DON'T DO THIS
const response = await fetch('/api/interviews');

// ✅ DO THIS
import { interviewService } from '../services/interviewService';
const session = await interviewService.startSession({ company_id, job_role });
```

### Supported Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/companies/{id}/interviews` | Start interview |
| POST | `/interviews/{id}/questions/next` | Get next question |
| POST | `/interviews/{id}/answers` | Submit answer |
| GET | `/interviews/{id}` | Get status |
| GET | `/interviews/{id}/report` | Get final report |

## 🎨 Mode Selector

### Typing Mode
Traditional text-based interview. The core functionality.

```typescript
// In App.tsx
<ModeButton id="typing">📝 Typing Mode</ModeButton>
```

### Voice Mode
Extension point for speech recognition:
```typescript
import { SpeechService } from '../services/speechService';

async function startVoiceInterview() {
  await speechService.startListening();
  // ... handle transcript ...
  await interviewService.submitAnswer({ 
    interview_id,
    question_id,
    answer: transcript,
    source: 'voice'
  });
}
```

### Avatar Mode
Extension point for avatar visualization:
```typescript
// Future API interactions
await avatarService.loadAvatar('avatar_123');
await avatarService.updateAvatarState({
  session_id,
  emotion: 'neutral',
  isSpeaking: true
});
```

### Real-time Mode
Future WebSocket-based real-time conversation.

## 🔧 Configuration

### API URL (In `App.tsx`)

```typescript
const [modeConfig, setModeConfig] = useState({
  apiURL: 'http://localhost:8000',  // Change this
  companyId: 1001,
  jobRole: 'Software Engineer'
});
```

### Environment Variables

Create `.env.local`:

```env
VITE_API_URL=http://localhost:8000
VITE_COMPANY_ID=1001
```

Then use in code:
```typescript
const apiUrl = import.meta.env.VITE_API_URL;
```

## 🐛 Error Handling

Built-in error handling with retries:

- **401** - Session expired (not implemented yet)
- **403** - Permission denied  
- **404** - Resource not found
- **422** - Validation errors
- **429** - Rate limiting
- **500+** - Server errors with retry logic (3 attempts, exponential backoff)

Errors displayed in `state.error` and shown to user.

## 📦 Components

### Shared Components

- `LoadingSpinner` - Loading indicators
- `StatusIndicator` - Phase/status badges
- `ProgressBar` - Progress bars

### Interview Mode Components

- `InterviewLayout` - Main container
- `StartView` - Session initiation
- `QuestionCard` - Question display
- `AnswerInput` - Text input
- `EvaluationPanel` - Score and feedback

## 🔄 Data Flow

```
User Clicks "Start Interview"
    ↓
App.tsx → StartView
    ↓
Actions.startInterview()
    ↓
InterviewController.startInterview()
    ↓
InterviewService.startSession()
    ↓
API Client → POST /companies/{id}/interviews
    ↓
Backend returns: InterviewSession
    ↓
Dispatch: SET_SESSION to Store
    ↓
트 InterviewLayout propagates state to child components
    ↓
User reads question from backend response
    ↓
User types answer
    ↓
Actions.submitAnswer('typing')
    ↓
InterviewController.submitAnswer()
    ↓
InterviewService.submitAnswer()
    ↓
API Client → POST /interviews/{id}/answers
    ↓
Backend returns: Evaluation (with next_phase, next_difficulty, etc.)
    ↓
Store updates with evaluation
    ↓
UI re-renders: Shows score, feedback (backend-driven styling)
```

## 🎯 Future Features

### Voice Mode

Required components:
- `MicrophoneButton` - Recording trigger
- `TranscriptDisplay` - Processed transcript
- `WaveformVisualizer` - Audio visualization

Implemented as placeholders now.

### Avatar Mode

Required components:
- `AvatarContainer` - Avatar display wrapper
- `AvatarState` - Emotion/loading states
- `AvatarControls` - Avatar interaction

Implemented as placeholders now.

### Real-time Mode

Required:
- WebSocket connection handling
- Real-time message display
- Instant feedback UI

Planned implementation.

## 📝 Type System

### Core Types

See `src/types/interview.ts`:

```typescript
interface InterviewSession {
  session_id: string;
  company_id: number;
  job_role: string;
  status: InterviewStatus;
  current_phase: string;      // Dynamic from backend
  total_questions: number;    // Dynamic from backend
  current_question_number: number;
}

interface Question {
  question_id: string;
  question: string;
  phase: string;              // Dynamic from backend
  question_number: number;
  total_questions: number;    // Dynamic from backend
  difficulty: number;         // Dynamic from backend
  category?: string;
}
```

### Service Types

See `src/services/*.ts` for comprehensive API type coverage.

## 🔐 Security

### CORS Configuration

Backend should allow:
```
Origin: http://localhost:3000
Methods: GET, POST, PUT, DELETE
Headers: Content-Type, Authorization
```

## 📈 Performance

- **Vite** - Fast HMR (Hot Module Replacement)
- **React 18** - Concurrent rendering
- **TypeScript** - Early error detection
- **Code Splitting** - Only load needed components

## 🧪 Testing

Build system ready for:
- Unit tests
- Integration tests  
- E2E tests with Playwright/Cypress

## 📚 Further Reading

- [Backend API Design](../../../docs/api-design.md)
- [DB Schema](../../../database_schema.sql)
- [Architecture Overview](../../../docs/architecture.md)
- [Error Handling](../../../docs/error-handling.md)

## 🤝 Contributing

When adding new features:

1. Define types in `src/types/`
2. Create service methods in `src/services/`
3. Implement controller logic in `src/controllers/`
4. Build React components with TypeScript
5. Test backend-driven behavior (ensure no hardcoded values)

## 📄 License

Same as main project.

---

**Last Updated:** 7/18/2026  
**Version:** 2.0.0  
**Tech Stack:** React 18 + TypeScript 5 + Vite 5 + Tailwind CSS 3