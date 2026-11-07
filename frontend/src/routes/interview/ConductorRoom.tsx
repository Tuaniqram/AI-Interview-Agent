import { getCandidateToken } from '../../utils/candidateToken';
import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Mic, MicOff, Sparkles, Volume2, VolumeX } from 'lucide-react';
import { useInterviewStore } from '../../state/interviewStore';
import { useVoice } from '../../hooks/useVoice';
import { useAntiCheatTelemetry } from '../../utils/antiCheatTelemetry';
import { InterviewRulesGate } from '../../components/integrity/InterviewRulesGate';
import { FlagGauge } from '../../components/integrity/FlagGauge';
import { AuraCore } from '../../components/AuraCore';
import { useAuraState } from '../../components/AuraCore/useAuraState';
import { VoiceWaveform } from '../../components/VoiceWaveform';
import { ConversationThread, InputBar, LoadingScreen } from './shared';

export function ConductorRoom() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { state, actions } = useInterviewStore();
  const voice = useVoice();
  const auraState = useAuraState();
  const telemetry = useAntiCheatTelemetry(state.currentQuestion?.question_number);

  const [input, setInput] = React.useState('');
  const [isSending, setIsSending] = React.useState(false);
  const [rulesAccepted, setRulesAccepted] = React.useState(false);
  const [voiceEnabled, setVoiceEnabled] = React.useState(() => {
    try {
      return localStorage.getItem('aura_voice_enabled') !== 'off';
    } catch {
      return true;
    }
  });
  const lastSpokenRef = React.useRef('');

  const session = state.session;
  const isPractice = !session?.org_id && !session?.department_id;
  const isCompleted = session?.status === 'completed';

  // ── Answer time-box (contract §4.7): hard per-question window from the
  // integrity policy. Expiry auto-submits what is typed, or skips the question.
  const answerLimitS = state.integrityPolicy?.enabled ? state.integrityPolicy?.answer_time_limit_s ?? 0 : 0;
  const [remaining, setRemaining] = React.useState(answerLimitS);
  const handleSendRef = React.useRef<() => void>(() => {});
  handleSendRef.current = () => {
    void handleSend();
  };
  const questionNumberKey = state.currentQuestion?.question_number;

  React.useEffect(() => {
    setRemaining(answerLimitS);
    if (!answerLimitS) return;
    const id = window.setInterval(() => {
      setRemaining((r) => (r > 0 ? r - 1 : 0));
    }, 1000);
    return () => window.clearInterval(id);
  }, [answerLimitS, questionNumberKey]);

  React.useEffect(() => {
    if (!answerLimitS || remaining > 0) return;
    if (voice.interimText || input.trim()) {
      handleSendRef.current();
    } else {
      void actions.goToNextQuestion();
    }
  }, [remaining, answerLimitS]);

  React.useEffect(() => {
    if (!sessionId || !rulesAccepted) return;
    // Always (re)connect + reconcile engine state for this session:
    // idempotent — resumes when the engine already has state, starts otherwise.
    actions.startInterview({ sessionId });
  }, [sessionId, rulesAccepted]);

  // AURA speaks each conductor turn (ack + bridge + question) when voice is on.
  React.useEffect(() => {
    if (!voiceEnabled) return;
    if (state.session?.status === 'completed') return;
    const turn = state.conversationTurn;
    if (!turn || lastSpokenRef.current === turn) return;
    lastSpokenRef.current = turn;
    voice.speakText(turn);
  }, [voiceEnabled, state.conversationTurn, state.session?.status]);

  React.useEffect(() => {
    if (voice.transcript) {
      telemetry.current.answer_source = 'voice';
      setInput(voice.transcript);
    }
  }, [voice.transcript]);

  React.useEffect(() => {
    if (isCompleted) {
      voice.stopSpeaking();
    }
  }, [isCompleted]);

  const toggleVoice = () => {
    setVoiceEnabled((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('aura_voice_enabled', next ? 'on' : 'off');
      } catch {
        // ignore
      }
      if (!next) voice.stopSpeaking();
      return next;
    });
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || !state.currentQuestion || isSending) return;
    setIsSending(true);
    voice.stopVoice();
    voice.stopSpeaking();
    try {
      await actions.submitAnswer(text, telemetry.current);
      setInput('');
      voice.resetTranscript();
    } catch {
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleMicToggle = () => {
    if (voice.isListening) {
      voice.stopVoice();
    } else {
      voice.startVoice();
    }
  };

  if (state.isLoading && !state.currentQuestion) {
    return <LoadingScreen label="Waking AURA..." />;
  }

  if (state.error && !state.currentQuestion) {
    const accessDenied = /denied/i.test(state.error);
    const loggedIn = !!getCandidateToken();
    return (
      <div className="flex-1 h-full bg-page flex items-center justify-center" data-theme="dark" role="alert">
        <div className="text-center space-y-4 max-w-sm px-4">
          <p className="text-primary text-base font-semibold">
            {accessDenied ? "You don't have access to this interview" : "We couldn't start your interview"}
          </p>
          <p className="text-secondary text-sm">
            {accessDenied
              ? 'Open the invitation link from your email, or sign in with the account that was invited.'
              : state.error}
          </p>
          <button
            onClick={() => navigate(loggedIn ? '/candidate/applications' : '/opportunity-hub')}
            className="px-4 py-2 rounded-lg bg-action-primary text-inverse text-xs hover:bg-action-primary-hover transition-colors"
          >
            {loggedIn ? 'Back to my applications' : 'Back to opportunities'}
          </button>
        </div>
      </div>
    );
  }

  // ── Integrity conduct gate (shown before the session starts) ──
  if (!rulesAccepted) {
    return (
      <InterviewRulesGate
        maxFlags={state.integrityPolicy?.enabled ? state.integrityPolicy?.max_flags ?? 0 : 0}
        integrityEnabled={state.integrityPolicy?.enabled ?? false}
        starting={state.isLoading}
        onStart={() => setRulesAccepted(true)}
      />
    );
  }

  // ── Completion ──
  if (isCompleted) {
    return (
      <div className="flex-1 h-full bg-page flex items-center justify-center" data-theme="dark">
        <div className="text-center space-y-6 px-4">
          <AuraCore state="idle" size={220} className="mx-auto" />
          <div>
            <h2 className="text-xl font-semibold text-primary">
              {state.integrityTerminated ? 'Session terminated' : 'Interview complete'}
            </h2>
            <p className="text-secondary text-sm mt-2 max-w-sm mx-auto">
              {state.integrityTerminated
                ? state.integrityTerminationReason ||
                  'This session was stopped because repeated integrity violations were detected. Contact the interviewer to discuss next steps.'
                : isPractice
                  ? 'Nice work. Review your performance or try another practice round.'
                  : 'AURA has finished evaluating your interview. Your results are ready.'}
            </p>
          </div>
          <div className="flex items-center justify-center gap-3">
            {isPractice ? (
              <button
                onClick={() => navigate('/candidate/practice')}
                className="px-4 py-2 rounded-lg bg-action-primary text-inverse text-xs hover:bg-action-primary-hover transition-colors"
              >
                Try another practice
              </button>
            ) : (
              <button
                onClick={() => session && navigate(`/interview/${session.session_id}/report`)}
                className="px-4 py-2 rounded-lg bg-action-primary text-inverse text-xs hover:bg-action-primary-hover transition-colors"
              >
                View report
              </button>
            )}
            <button
              onClick={() => navigate(isPractice ? '/candidate/dashboard' : '/opportunity-hub')}
              className="px-4 py-2 rounded-lg bg-overlay text-secondary text-xs hover:bg-hover transition-colors"
            >
              {isPractice ? 'Back to dashboard' : 'Back to opportunities'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 h-full bg-page flex flex-col min-h-0" data-theme="dark">
      {/* AURA stage */}
      <div className="shrink-0 flex flex-col items-center justify-center px-6 pt-8 pb-4 min-h-0">
        <AuraCore state={auraState} size={300} />
        <div className="mt-4 flex items-center gap-3">
          <p className="text-[11px] uppercase tracking-[0.2em] text-muted flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-action-primary" />
            {state.wsPhase === 'reconnecting'
              ? 'Reconnecting...'
              : auraState === 'thinking'
                ? 'AURA is evaluating...'
                : voice.isSpeaking
                  ? 'AURA is speaking...'
                  : 'AURA Conductor'}
          </p>
          <button
            onClick={toggleVoice}
            title={voiceEnabled ? 'Mute AURA voice' : 'Enable AURA voice'}
            className={`w-8 h-8 rounded-full flex items-center justify-center transition-all shrink-0 ${
              voiceEnabled ? 'bg-action-primary/10 text-action-primary hover:bg-action-primary/20' : 'bg-input text-muted hover:bg-hover'
            }`}
          >
            {voiceEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          </button>
          <FlagGauge
            count={state.flaggedCount}
            max={state.integrityPolicy?.enabled ? state.integrityPolicy?.max_flags ?? 0 : 0}
            className="ml-2"
          />
        </div>
      </div>

      {/* Conversation */}
      <ConversationThread showEvaluation={isPractice} />

      <InputBar
        input={voice.interimText || input}
        onInputChange={(value) => {
          telemetry.current.answer_source = 'typing';
          setInput(value);
        }}
        onSend={handleSend}
        onKeyDown={handleKeyDown}
        isSending={isSending}
        placeholder={voice.isListening ? 'Listening...' : 'Type your answer...'}
        statusIndicator={
          <>
            {answerLimitS > 0 && (
              <span
                className={`font-mono tabular-nums ${
                  remaining <= 15 ? 'text-error font-semibold' : remaining <= 30 ? 'text-warning' : 'text-muted'
                }`}
                title={`Time remaining for this answer (${answerLimitS}s window)`}
              >
                {remaining > 0 ? `${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, '0')}` : 'Time\'s up'}
              </span>
            )}
            {voice.isListening && (
              <span className="flex items-center gap-2 text-success">
                <VoiceWaveform isListening={true} className="h-6" />
                Recording...
              </span>
            )}
            {!voice.isSupported && <span className="text-warning">Voice not supported</span>}
          </>
        }
      >
        <button
          onClick={handleMicToggle}
          disabled={isSending || !voice.isSupported}
          className={`w-11 h-11 rounded-full flex items-center justify-center transition-all shrink-0 ${
            voice.isListening
              ? 'bg-error text-inverse pulse-ring'
              : 'bg-input text-muted hover:bg-hover'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {voice.isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
        </button>
      </InputBar>
    </div>
  );
}
