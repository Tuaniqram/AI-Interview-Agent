import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ListChecks } from 'lucide-react';
import { candidateService } from '../../services/candidateService';
import { Button } from '../../components/shared/Button';
import { Card } from '../../components/shared/Card';
import { PageHeader } from '../../components/shared/PageHeader';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { InterviewList } from '../../components/candidate/InterviewList';
import { useToast } from '../../components/shared/Toast';
import type { CandidateInterview } from '../../types/candidate';

const PAGE_SIZE = 10;

export default function CandidateInterviews() {
  const navigate = useNavigate();
  const [interviews, setInterviews] = useState<CandidateInterview[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const toast = useToast();

  useEffect(() => {
    candidateService.getInterviews()
      .then(setInterviews)
      .catch(() => toast.error('Could not load your interviews. Reload the page to try again.'))
      .finally(() => setLoading(false));
  }, []);

  const loadMore = useCallback(() => setPage(p => p + 1), []);

  if (loading) return <ContentSkeleton />;

  const visible = interviews.slice(0, (page + 1) * PAGE_SIZE);
  const hasMore = visible.length < interviews.length;

  return (
    <div>
      <PageHeader
        title="My interviews"
        description="Every interview you have taken, practice and real. Open one to see its score and feedback."
        actions={<Button variant="secondary" onClick={() => navigate('/candidate/practice')}>New practice interview</Button>}
      />

      {interviews.length === 0 ? (
        <Card>
          <EmptyState
            icon={<ListChecks />}
            title="No interviews yet"
            description="Take a practice interview, or apply to an open interview in the Opportunity Hub."
            action={<Button onClick={() => navigate('/candidate/practice')}>Start a practice interview</Button>}
          />
        </Card>
      ) : (
        <div className="space-y-4">
          <InterviewList interviews={visible} />
          {hasMore && (
            <div className="flex justify-center">
              <Button variant="secondary" onClick={loadMore}>Show more</Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
