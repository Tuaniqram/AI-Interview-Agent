import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Building2 } from 'lucide-react';
import { apiClient } from '../services/apiClient';
import { Card } from '../components/shared/Card';
import { MetricCard } from '../components/shared/MetricCard';
import { DocumentCard } from '../components/company/DocumentCard';
import { DocumentUploader } from '../components/company/DocumentUploader';
import { InterviewHistoryTable } from '../components/company/InterviewHistoryTable';
import { CardSkeleton } from '../components/shared/Skeleton';
import { FileText, ListChecks, AlertCircle } from 'lucide-react';

type Tab = 'overview' | 'documents' | 'history';

interface Company {
  id: number;
  name: string;
  website?: string | null;
  description?: string | null;
  created_at: string;
}

interface Document {
  id: string;
  filename: string;
  document_type: string;
  created_at: string;
}

interface SessionRecord {
  id: string;
  candidate_id?: string;
  job_role: string;
  status: string;
  final_score: number | null;
  started_at: string;
}

export function CompanyDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>('overview');
  const [company, setCompany] = useState<Company | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const c = await apiClient.get<Company>(`/companies/${id}`);
        if (cancelled) return;
        setCompany(c);
      } catch (err: any) {
        if (cancelled) return;
        if (err?.response?.status === 404) {
          navigate('/companies');
          return;
        }
        setError('Failed to load company details.');
        setLoading(false);
        return;
      }

      const docPromise = apiClient.get<Document[]>(`/companies/${id}/knowledge`)
        .then(data => { if (!cancelled) setDocuments(data); })
        .catch(() => {});

      const sessionPromise = apiClient.get<SessionRecord[]>(`/companies/${id}/sessions`)
        .then(data => { if (!cancelled) setSessions(data); })
        .catch(() => {});

      await Promise.allSettled([docPromise, sessionPromise]);
      if (!cancelled) setLoading(false);
    }

    load();
    return () => { cancelled = true; };
  }, [id, navigate]);

  const tabs: { key: Tab; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'documents', label: `Documents (${documents.length})` },
    { key: 'history', label: `History (${sessions.length})` },
  ];

  const avgScore = sessions.length > 0
    ? sessions.reduce((a, b) => a + (b.final_score || 0), 0) / sessions.length
    : null;

  if (loading) {
    return (
      <div>
        <div className="h-8 w-32 mb-6"><CardSkeleton /></div>
        <CardSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <button onClick={() => navigate('/companies')} className="flex items-center gap-1.5 text-xs text-muted hover:text-secondary mb-4 transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Companies
        </button>
        <Card>
          <div className="flex flex-col items-center py-8 text-center">
            <AlertCircle className="w-8 h-8 text-error mb-3" />
            <p className="text-sm text-primary font-medium mb-1">{error}</p>
            <button onClick={() => navigate('/companies')} className="mt-3 text-sm text-action-primary hover:text-action-primary-hover transition-colors">
              Back to Companies
            </button>
          </div>
        </Card>
      </div>
    );
  }

  if (!company) return null;

  return (
    <div>
      <button onClick={() => navigate('/companies')} className="flex items-center gap-1.5 text-xs text-muted hover:text-secondary mb-4 transition-colors">
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Companies
      </button>

      <Card className="mb-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-action-primary/15 flex items-center justify-center shrink-0">
            <Building2 className="w-6 h-6 text-action-primary" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-primary">{company.name}</h1>
            {company.website && <p className="text-sm text-muted mt-0.5">{company.website}</p>}
            {company.description && <p className="text-sm text-secondary mt-1 max-w-xl">{company.description}</p>}
          </div>
        </div>
      </Card>

      <div className="flex gap-4 mb-6">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-1 py-2 text-sm font-medium transition-colors relative ${
              tab === t.key
                ? 'text-action-primary'
                : 'text-secondary hover:text-primary'
            }`}
          >
            {t.label}
            {tab === t.key && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-action-primary rounded-full" />
            )}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <MetricCard label="Total Sessions" value={sessions.length} icon={<ListChecks className="w-4 h-4" />} />
            <MetricCard label="Documents" value={documents.length} icon={<FileText className="w-4 h-4" />} />
            <MetricCard
              label="Avg Score"
              value={avgScore !== null ? avgScore.toFixed(1) : '—'}
              trend={avgScore !== null && avgScore >= 6 ? 'up' : avgScore !== null ? 'down' : undefined}
            />
          </div>
          <Card>
            <h3 className="text-sm font-medium text-primary mb-1">Company Info</h3>
            <p className="text-xs text-muted">Created {new Date(company.created_at).toLocaleDateString()}</p>
            {company.description && <p className="text-sm text-secondary mt-2">{company.description}</p>}
          </Card>
          {sessions.length > 0 && (
            <Card>
              <h3 className="text-sm font-medium text-primary mb-3">Recent Sessions</h3>
              <InterviewHistoryTable sessions={sessions.slice(0, 5)} />
            </Card>
          )}
        </div>
      )}

      {tab === 'documents' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <DocumentUploader companyId={company.id} onUploaded={() => {
              apiClient.get<Document[]>(`/companies/${id}/knowledge`).then(setDocuments);
            }} />
          </div>
          {documents.length === 0 ? (
            <Card>
              <p className="text-sm text-secondary py-8 text-center">No documents uploaded yet. Upload a PDF to add company knowledge.</p>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {documents.map(d => (
                <DocumentCard key={d.id} document={d} onDelete={async (docId) => {
                  try {
                    await apiClient.delete(`/companies/${id}/knowledge/${docId}`);
                    setDocuments(prev => prev.filter(x => x.id !== docId));
                  } catch {}
                }} />
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'history' && (
        <Card>
          <InterviewHistoryTable sessions={sessions} />
        </Card>
      )}
    </div>
  );
}
