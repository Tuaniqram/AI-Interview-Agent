import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Calendar, Briefcase, Mail, User, TrendingUp, TrendingDown } from 'lucide-react';
import { apiClient } from '../services/apiClient';
import { Card } from '../components/shared/Card';
import { StatusBadge } from '../components/shared/StatusBadge';
import { CardSkeleton } from '../components/shared/Skeleton';
import type { InterviewReport as InterviewReportType } from '../types/interview';

interface Message {
  id: string;
  role: string;
  message_type: string;
  content: string;
  question_number: number;
  phase: string;
  score: number | null;
  created_at: string;
}

interface Evaluation {
  id: string;
  message_id: string;
  technical_score: number | null;
  communication_score: number | null;
  strengths: string | null;
  weaknesses: string | null;
  feedback: string | null;
  overall_score: number | null;
}

export function InterviewReportPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<InterviewReportType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiClient.get<InterviewReportType>(`/interviews/${id}/summary`);
        if (!cancelled) setReport(data);
      } catch (err: any) {
        if (!cancelled) setError('Failed to load interview report.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [id]);

  if (loading) {
    return (
      <div>
        <div className="h-8 w-32 mb-6"><CardSkeleton /></div>
        <CardSkeleton />
        <div className="mt-4"><CardSkeleton /></div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div>
        <button onClick={() => navigate(-1)} className="flex items-center gap-1.5 text-xs text-muted hover:text-secondary mb-4 transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" /> Back
        </button>
        <Card>
          <div className="py-8 text-center text-sm text-secondary">{error || 'Report not found.'}</div>
        </Card>
      </div>
    );
  }

  const messages = (report.messages || []) as unknown as Message[];
  const evaluations = (report.evaluations || []) as unknown as Evaluation[];

  // Pair questions with answers
  const questions = messages.filter(m => m.role === 'interviewer' || m.message_type === 'question');
  const answers = messages.filter(m => m.role === 'candidate' || m.message_type === 'candidate_answer');

  const scoreColor = (score: number | null) => {
    if (score === null || score === undefined) return 'text-muted';
    if (score >= 7) return 'text-success-text';
    if (score >= 5) return 'text-warning-text';
    return 'text-error-text';
  };

  return (
    <div className="max-w-4xl">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1.5 text-xs text-muted hover:text-secondary mb-4 transition-colors">
        <ArrowLeft className="w-3.5 h-3.5" /> Back
      </button>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-xl font-bold text-primary mb-1">Interview Report</h1>
        <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
          {report.candidate_name && (
            <span className="flex items-center gap-1"><User className="w-3.5 h-3.5" /> {report.candidate_name}</span>
          )}
          {report.candidate_email && (
            <span className="flex items-center gap-1"><Mail className="w-3.5 h-3.5" /> {report.candidate_email}</span>
          )}
          {report.job_role && (
            <span className="flex items-center gap-1"><Briefcase className="w-3.5 h-3.5" /> {report.job_role}</span>
          )}
          {report.started_at && (
            <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> {new Date(report.started_at).toLocaleDateString()}</span>
          )}
          <StatusBadge status={report.status} />
        </div>
      </div>

      {/* Score Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <Card>
          <div className="text-center">
            <p className="text-xs text-muted mb-1">Overall Score</p>
            <p className={`text-3xl font-bold ${scoreColor(report.final_score)}`}>
              {report.final_score !== null ? report.final_score.toFixed(1) : '—'}
            </p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <p className="text-xs text-muted mb-1">Technical</p>
            <p className={`text-3xl font-bold ${scoreColor(report.technical_score ?? null)}`}>
              {report.technical_score != null ? Number(report.technical_score).toFixed(1) : '—'}
            </p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <p className="text-xs text-muted mb-1">Communication</p>
            <p className={`text-3xl font-bold ${scoreColor(report.communication_score ?? null)}`}>
              {report.communication_score != null ? Number(report.communication_score).toFixed(1) : '—'}
            </p>
          </div>
        </Card>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <Card padding="sm">
          <p className="text-xs text-muted">Questions</p>
          <p className="text-lg font-semibold text-primary">{report.total_questions_answered} / {report.total_questions}</p>
        </Card>
        <Card padding="sm">
          <p className="text-xs text-muted">Answered</p>
          <p className="text-lg font-semibold text-primary">{Math.round(report.answered_ratio * 100)}%</p>
        </Card>
        <Card padding="sm">
          <p className="text-xs text-muted">Messages</p>
          <p className="text-lg font-semibold text-primary">{report.messages_count}</p>
        </Card>
        <Card padding="sm">
          <p className="text-xs text-muted">Status</p>
          <p className="text-lg font-semibold text-primary">{report.interview_complete ? 'Complete' : 'Incomplete'}</p>
        </Card>
      </div>

      {/* Strengths & Weaknesses */}
      {(report.strengths?.length || report.weaknesses?.length) ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          {report.strengths && report.strengths.length > 0 && (
            <Card>
              <h3 className="text-sm font-medium text-success-text mb-2 flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4" /> Strengths
              </h3>
              <ul className="space-y-1">
                {report.strengths.map((s, i) => (
                  <li key={i} className="text-xs text-secondary">{s}</li>
                ))}
              </ul>
            </Card>
          )}
          {report.weaknesses && report.weaknesses.length > 0 && (
            <Card>
              <h3 className="text-sm font-medium text-warning-text mb-2 flex items-center gap-1.5">
                <TrendingDown className="w-4 h-4" /> Areas for Improvement
              </h3>
              <ul className="space-y-1">
                {report.weaknesses.map((w, i) => (
                  <li key={i} className="text-xs text-secondary">{w}</li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      ) : null}

      {/* Conversation Timeline */}
      <Card>
        <h3 className="text-sm font-medium text-primary mb-4">Conversation</h3>
        {questions.length === 0 ? (
          <p className="text-xs text-muted py-4 text-center">No conversation data available.</p>
        ) : (
          <div className="space-y-4">
            {questions.map((q, i) => {
              const matchingAnswer = answers.find(a => a.question_number === q.question_number);
              const evalData = evaluations.find(e => e.message_id === matchingAnswer?.id);
              return (
                <div key={q.id || i} className="-l-2 -action-primary/30 pl-4">
                  <div className="mb-2">
                    <span className="text-[10px] font-medium text-action-primary uppercase">Q{q.question_number}</span>
                    <p className="text-sm text-primary mt-0.5">{q.content}</p>
                  </div>
                  {matchingAnswer && (
                    <div className="mb-2 ml-2">
                      <span className="text-[10px] font-medium text-muted uppercase">Answer</span>
                      <p className="text-xs text-secondary mt-0.5">{matchingAnswer.content}</p>
                    </div>
                  )}
                  {evalData && (
                    <div className="flex items-center gap-3 text-[10px] text-muted">
                      {evalData.overall_score != null && (
                        <span className={scoreColor(evalData.overall_score)}>Score: {evalData.overall_score}</span>
                      )}
                      {evalData.technical_score != null && (
                        <span>Tech: {evalData.technical_score}</span>
                      )}
                      {evalData.communication_score != null && (
                        <span>Comm: {evalData.communication_score}</span>
                      )}
                    </div>
                  )}
                  {evalData?.feedback && (
                    <p className="text-[10px] text-muted mt-1 italic">{evalData.feedback}</p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
