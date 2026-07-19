# Frontend Interview Flow Audit Report

> Scope: Frontend only. Backend API (`app/api/interview_agent.py`) confirmed working (`POST /interviews/{session_id}/questions/next` returns 200, `q#1 action=continue`). No backend changes were made.

---

## 1. Root Cause

The "Evaluate & Next" submit button in the interview UI **erased the user's answer instead of submitting it**. Clicking the button did nothing visibly — no API request was fired, no evaluation appeared, and the typed answer was wiped. This made the first intro question appear "stuck" with no way to proceed after it.

Two compounding frontend defects caused this:

| # | Defect | Severity | File | Line |
|---|--------|----------|------|------|
| A | Submit button `onClick` cleared input + called `updateAnswer('')` instead of `submitAnswer(input)` — no API request was ever sent on button click | **Critical (Root Cause)** | `frontend/src/components/interview.tsx` | 109–116 |
| B | `submitAnswer` in the store rejected any answer shorter than 50 characters with a hard error, blocking valid short intro answers even after A is fixed | High | `frontend/src/state/interviewStore.tsx` | 237–240 |

---

## 2. File Causing the Issue

**Primary:** `frontend/src/components/interview.tsx` — the submit button handler.

**Secondary:** `frontend/src/state/interviewStore.tsx` — the 50-character answer gate.

---

## 3. Line Numbers (Pre-Fix)

### Defect A — `frontend/src/components/interview.tsx` (lines 109–116)

**Before (broken):**
```tsx
<button
  onClick={() => {
    setInput('');
    actions.updateAnswer('');
  }}
  disabled={!state.currentQuestion || isSending}
  className="..."
>
```

This handler:
1. Calls `setInput('')` → wipes the local `input` state (the text the user just typed).
2. Calls `actions.updateAnswer('')` → dispatches `SET_USER_ANSWER` with an empty string to the global store.
3. **Never calls `actions.submitAnswer(input)`** → no `POST /interviews/{session_id}/answers` request is ever sent.

Only the textarea's `onKeyPress` / `handleSend()` path (Enter key) actually invoked `submitAnswer`. Mouse users clicking the button saw the answer vanish with no evaluation, so the interview appeared "stuck" on the first question.

### Defect B — `frontend/src/state/interviewStore.tsx` (lines 237–240)

**Before (broken):**
```tsx
if (!answer || answer.trim().length < 50) {
  dispatch({ type: 'SET_ERROR', payload: 'Please enter a longer answer (at least 50 characters)' });
  return;
}
```

A hard 50-character minimum on the client would reject legitimate short intro answers (e.g. "Yes", "Hi, I'm Tuaniqram", a name). The backend LLM evaluator is fully capable of scoring short answers — the frontend should not gate them.

---

## 4. Why the First Question Displays but Cannot Be Submitted

### What worked (so the question did appear)
- `startInterview` → controller creates session, calls `getNextQuestion`, returns `{ session, firstQuestion }`.
- Store dispatched `SET_SESSION` and `SET_QUESTION` → `state.currentQuestion` was populated.
- `interview.tsx` rendered the question via `state.currentQuestion.question` and `state.currentQuestion.question_number`.

### What was broken (so submission failed)
1. User types an answer into the textarea → stored only in local `input` state.
2. User clicks **"Evaluate & Next"**.
3. The button's `onClick` ran:
   - `setInput('')` → emptied the textarea visually.
   - `actions.updateAnswer('')` → set `state.userAnswer = ''`.
   - **No call to `submitAnswer`** → `POST /interviews/{session_id}/answers` never fired.
4. The UI returned to an empty textarea with the same question showing — the interview looked frozen.

Net effect: the question-render path was healthy, but the submit path was never wired to the button. There was no `disabled` condition blocking the click — the click simply did the wrong thing (clear instead of submit).

### State machine gap (Audit section 5)
The frontend implied state machine is:

```
INITIAL → STARTED → QUESTION_READY → ANSWERING → SUBMITTING → EVALUATED → NEXT_QUESTION
```

The bug caused a silent transition `ANSWERING → QUESTION_READY` (answer cleared, same question re-rendered) instead of `ANSWERING → SUBMITTING`. So the flow never left `QUESTION_READY` after the first question, which matches the observed symptom ("stuck at STARTED / first question").

---

## 5. Button Disabled Conditions (Audit Section 3)

Pre-fix `disabled` predicates audited:

| Button | Condition | Blocked first question? |
|--------|-----------|--------------------------|
| Clear | `isSending \|\| !input` | No (correct) |
| Evaluate & Next (pre-fix) | `!state.currentQuestion \|\| isSending` | No — button was clickable; it just did nothing useful |
| Evaluate & Next (post-fix) | `!state.currentQuestion \|\| isSending \|\| !input.trim()` | No (correct — disables only while sending, with no question, or with empty input) |

None of the disabled conditions alone blocked the first question. The failure was behavioral (wrong handler), not a disabled gate. The corrected condition also adds `!input.trim()` to prevent submitting empty input.

---

## 6. API Integration Verification (Audit Section 1)

`frontend/src/services/interviewService.ts` — **matches backend contract. No changes needed.**

- `POST /interviews/{session_id}/questions/next` → returns `{ session_id, question, question_number, phase, difficulty_level, next_action, rag_context_available, nodes_executed }` → mapped to `Question` type ✅
- `POST /interviews/{session_id}/answers` → accepts `{ question_number, question, candidate_answer, conversation_history, candidate_profile, difficulty_level }` ✅
- Field names, `session_id` usage, and `interview_id` mapping all correct.

`frontend/src/controllers/interviewController.ts` — **maps answer response to frontend `AnswerEvaluation` correctly** (lines 212–223). Pulls `evaluation.score`, `evaluation.feedback` → `AnswerEvaluation.evaluation`, `next_phase` → `phase`, `next_difficulty` → `difficulty_level`, `next_action === 'complete'` → `interview_status: 'completed'`. ✅

---

## 7. State Management After Question API Returns (Audit Section 2)

After `getNextQuestion` resolves, the controller updated its internal copy (`this.currentQuestion`, `session.question_number`, `session.current_phase`, `session.difficulty_level`), and the store dispatched `SET_QUESTION` (which sets `currentQuestion` and clears `isLoading`). ✅

Post-fix additions:
- `goToNextQuestion` now also dispatches `SET_USER_ANSWER` with `''` so the previous answer is cleared before the next question renders.
- `startInterview` now logs `QUESTION RECEIVED` for tracing.

---

## 8. Exact Fix Applied

### Fix A — `frontend/src/components/interview.tsx`

Wired the submit button to the real submit path and added the requested debug logs.

```tsx
// Render-time debug log (Audit section 6)
console.log('[InterviewLayout] render state:', {
  sessionId: state.session?.session_id,
  currentQuestion: state.currentQuestion?.question_number,
  questionNumber: state.currentQuestion?.question_number,
  answer: input,
  isLoading: state.isLoading,
  isEvaluating: state.isEvaluating,
  evaluation: state.evaluation,
});

// Submit button now actually submits
<button
  onClick={() => {
    console.log('[InterviewLayout] SUBMIT ANSWER clicked', {
      answer: input,
      questionNumber: state.currentQuestion?.question_number,
    });
    handleSend(); // ← calls actions.submitAnswer(input) via the existing handler
  }}
  disabled={!state.currentQuestion || isSending || !input.trim()}
  className="..."
>
```

`handleSend()` already does the right thing:
```tsx
const handleSend = async () => {
  if (!input.trim() || !state.currentQuestion || isSending) return;
  setIsSending(true);
  try {
    await actions.submitAnswer(input); // → POST /interviews/{id}/answers
    setInput('');
    textareaRef.current?.focus();
  } catch (error) {
    console.error('Failed to send answer:', error);
  } finally {
    setIsSending(false);
  }
};
```

So the button now:
1. Logs the payload being submitted (`SUBMIT ANSWER`).
2. Calls `handleSend()` → `actions.submitAnswer(input)`.
3. `submitAnswer` → controller → `interviewService.submitAnswer` → `POST /interviews/{session_id}/answers`.
4. Receives `evaluation`, dispatches `SET_EVALUATION` (UI shows feedback), then auto-fetches the next question (UI advances).

### Fix B — `frontend/src/state/interviewStore.tsx`

Replaced the hard 50-character gate with an empty-only check, and added the requested debug logs.

```tsx
submitAnswer: async (answer) => {
  // Only block truly empty answers. The backend LLM evaluator handles
  // short/long answers appropriately. A hard 50-char client gate would
  // reject valid intro-question responses (e.g. "Yes" / "Hi" / short name).
  if (!answer || !answer.trim()) {
    dispatch({ type: 'SET_ERROR', payload: 'Please enter an answer before submitting.' });
    return;
  }

  const payload = {
    answer: answer.substring(0, 100),
    sessionId: state.session?.session_id,
    questionNumber: state.currentQuestion?.question_number,
  };
  console.log('[Store] SUBMIT ANSWER:', payload);

  dispatch({ type: 'SET_EVALUATING', payload: true });
  dispatch({ type: 'SET_USER_ANSWER', payload: answer });
  try {
    const evaluation = await controller.submitAnswer({ answer });
    console.log('[Store] EVALUATION RESULT:', evaluation);
    dispatch({ type: 'SET_EVALUATION', payload: evaluation });

    if (evaluation.interview_status === 'completed') {
      console.log('[Store] Interview completed, fetching final report...');
      await actions.fetchFinalReport();
    } else {
      console.log('[Store] Fetching next question...');
      await actions.goToNextQuestion();
    }
  } catch (error: any) {
    console.error('[Store] submitAnswer error:', error);
    dispatch({ type: 'SET_ERROR', payload: error.message });
  }
},
```

`goToNextQuestion` now clears the previous answer and logs the new question:

```tsx
goToNextQuestion: async () => {
  dispatch({ type: 'SET_LOADING', payload: true });
  try {
    const nextQuestion = await controller.goToNextQuestion();
    console.log('[Store] QUESTION RECEIVED:', nextQuestion);
    dispatch({ type: 'SET_USER_ANSWER', payload: '' });
    dispatch({ type: 'SET_QUESTION', payload: nextQuestion });
  } catch (error: any) {
    dispatch({ type: 'SET_ERROR', payload: error.message });
  }
},
```

---

## 9. Debug Logs Added (Audit Section 6)

| Event | Log | Location |
|-------|-----|----------|
| Question rendered (component) | `console.log('[InterviewLayout] render state:', {...})` | `interview.tsx` (render body) |
| Submit clicked | `console.log('[InterviewLayout] SUBMIT ANSWER clicked', {...})` | `interview.tsx` (button onClick) |
| Question received (store) | `console.log('[Store] QUESTION RECEIVED:', nextQuestion)` | `interviewStore.tsx` — `startInterview` & `goToNextQuestion` |
| Submit payload | `console.log('[Store] SUBMIT ANSWER:', payload)` | `interviewStore.tsx` — `submitAnswer` |
| Evaluation result | `console.log('[Store] EVALUATION RESULT:', evaluation)` | `interviewStore.tsx` — `submitAnswer` |

The controller and service already logged `submitAnswer` response details, so the full chain (UI → Store → Controller → Service → API) is now observable in the console.

---

## 10. Files Changed

| File | Change |
|------|--------|
| `frontend/src/components/interview.tsx` | Submit button onClick now calls `handleSend()` (real submit); added `!input.trim()` to disabled; added render + click debug logs |
| `frontend/src/state/interviewStore.tsx` | Removed 50-char answer gate (replaced with empty-only check); added `SUBMIT ANSWER` / `EVALUATION RESULT` / `QUESTION RECEIVED` logs; `goToNextQuestion` clears `userAnswer` before setting next question |

## Files Inspected (No Changes Needed)

- `frontend/src/services/interviewService.ts` — endpoints & payloads match backend.
- `frontend/src/controllers/interviewController.ts` — response → `AnswerEvaluation` mapping correct.
- `frontend/src/types/interview.ts` — types align with backend contract.

## Files NOT Changed

- All backend files (`app/**`) — untouched per task constraint.

---

## 11. How to Verify the Fix

1. Start backend: `uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Open the interview UI, start a session.
4. First intro question appears.
5. Type any answer (even short, e.g. "Yes").
6. Click **Evaluate & Next**.
   - Console prints: `SUBMIT ANSWER clicked`, then `SUBMIT ANSWER:`, then `EVALUATION RESULT:`, then `QUESTION RECEIVED:`.
   - UI shows the analysis feedback (score + feedback text).
   - UI then advances to the next question with a cleared answer field.