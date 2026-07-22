import { useState } from 'react';
import { ChevronLeft, ChevronRight, ChevronDown, ChevronRight as ChevronRightIcon, X } from 'lucide-react';
import { useInterviewStore } from '../../state/interviewStore';

type Section = 'strengths' | 'weaknesses' | 'feedback';

const sectionMeta: Record<Section, { label: string; icon: string; color: string; dotColor: string }> = {
  strengths:   { label: 'Strengths',   icon: '✦', color: 'text-success',      dotColor: 'text-success' },
  weaknesses:  { label: 'Weaknesses',  icon: '⚠', color: 'text-warning',      dotColor: 'text-warning' },
  feedback:    { label: 'Feedback',    icon: '💬', color: 'text-action-primary', dotColor: 'text-action-primary' },
};

export function PastEvaluationCard() {
  const { state, actions } = useInterviewStore();
  const { evaluationHistory, historyIndex } = state;
  const [openSections, setOpenSections] = useState<Set<Section>>(new Set());

  const toggleSection = (s: Section) => {
    setOpenSections((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  };

  if (evaluationHistory.length === 0) {
    return (
      <div className="bg-section shadow-lg rounded-xl p-4 w-72 fade-in">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-muted tracking-wider">EVALUATIONS</span>
          <button onClick={actions.toggleCard} className="text-muted hover:text-primary transition-colors p-0.5">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
        <p className="text-muted text-xs text-center py-8">No evaluations yet</p>
      </div>
    );
  }

  const entry = evaluationHistory[historyIndex];
  if (!entry) return null;

  const scoreColor = entry.score >= 7 ? 'text-success' : entry.score >= 5 ? 'text-warning' : 'text-error';
  const sections: Section[] = ['strengths', 'weaknesses', 'feedback'];
  const hasContent = (s: Section) => {
    if (s === 'strengths') return entry.strengths.length > 0;
    if (s === 'weaknesses') return entry.weaknesses.length > 0;
    return !!entry.feedback;
  };

  return (
    <div className="bg-section shadow-lg rounded-xl w-72 overflow-hidden fade-in">
      <div className="h-0.5 bg-gradient-to-r from-action-primary/60 to-action-primary/20" />

      <div className="flex items-center justify-between px-4 pt-3 pb-2">
        <span className="text-[10px] font-semibold text-muted tracking-widest">EVALUATIONS</span>
        <div className="flex items-center gap-0.5">
          <span className="text-[10px] text-muted font-medium mr-0.5">Q{entry.questionNumber}/{evaluationHistory.length}</span>
          <button
            onClick={actions.goToPrevEvaluation}
            disabled={historyIndex === 0}
            className="text-muted hover:text-primary disabled:opacity-20 disabled:cursor-not-allowed transition-colors p-0.5"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={actions.goToNextEvaluation}
            disabled={historyIndex === evaluationHistory.length - 1}
            className="text-muted hover:text-primary disabled:opacity-20 disabled:cursor-not-allowed transition-colors p-0.5"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
          <button onClick={actions.toggleCard} className="text-muted hover:text-primary transition-colors p-0.5 ml-0.5">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="px-4 pb-3">
        <div className="flex items-end gap-3 mb-3">
          <div className="flex items-baseline gap-0.5">
            <span className={`text-2xl font-bold ${scoreColor}`}>{entry.score}</span>
            <span className="text-[10px] text-muted font-medium">/10</span>
          </div>
          <div className="flex gap-1.5 pb-0.5">
            {entry.technicalScore !== undefined && (
              <span className="text-[9px] bg-action-primary/10 text-action-primary px-1.5 py-0.5 rounded font-medium">T {entry.technicalScore}</span>
            )}
            {entry.communicationScore !== undefined && (
              <span className="text-[9px] bg-info/10 text-info px-1.5 py-0.5 rounded font-medium">C {entry.communicationScore}</span>
            )}
          </div>
        </div>

        <div className="space-y-0.5">
          {sections.filter(hasContent).map((s) => {
            const meta = sectionMeta[s];
            const isOpen = openSections.has(s);

            return (
              <div key={s} className="rounded-lg overflow-hidden">
                <button
                  onClick={() => toggleSection(s)}
                  className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg hover:bg-hover/50 transition-colors text-left"
                >
                  <span className={`text-[10px] font-semibold tracking-wider ${meta.color}`}>
                    {meta.label}
                  </span>
                  {isOpen ? <ChevronDown className="w-3 h-3 text-muted" /> : <ChevronRightIcon className="w-3 h-3 text-muted" />}
                </button>

                {isOpen && (
                  <div className="px-2.5 pb-2 pt-0.5 fade-in">
                    {s === 'strengths' && (
                      <ul className="space-y-1">
                        {entry.strengths.map((item, i) => (
                          <li key={i} className="text-[11px] text-secondary flex items-start gap-1.5 leading-snug">
                            <span className="text-success shrink-0 mt-0.5">✦</span> {item}
                          </li>
                        ))}
                      </ul>
                    )}
                    {s === 'weaknesses' && (
                      <ul className="space-y-1">
                        {entry.weaknesses.map((item, i) => (
                          <li key={i} className="text-[11px] text-secondary flex items-start gap-1.5 leading-snug">
                            <span className="text-warning shrink-0 mt-0.5">⚠</span> {item}
                          </li>
                        ))}
                      </ul>
                    )}
                    {s === 'feedback' && (
                      <p className="text-[11px] text-secondary leading-relaxed">{entry.feedback}</p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
