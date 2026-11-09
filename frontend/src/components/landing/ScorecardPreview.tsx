import { VerdictCard } from '../interview/VerdictCard';
import { CompetencyTable } from '../interview/CompetencyTable';
import { sampleCompetencies, sampleDecision } from './sampleInterview';

/**
 * The recruiter's report for the sample interview, rendered with the product's own components (the same
 * `VerdictCard` and `CompetencyTable` as the real report page) on a flat surface.
 */
export function ScorecardPreview() {
  return (
    <div>
      <VerdictCard flat decision={sampleDecision()} />
      <CompetencyTable flat summary={sampleCompetencies()} />
    </div>
  );
}
