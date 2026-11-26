import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { candidateService } from '../../services/candidateService';
import { Button } from '../../components/shared/Button';
import { Card } from '../../components/shared/Card';
import { Input } from '../../components/shared/Input';
import { Select } from '../../components/shared/Select';
import { Slider } from '../../components/shared/Slider';
import { PageHeader } from '../../components/shared/PageHeader';
import { useToast } from '../../components/shared/Toast';

const ROLES = ['Software Engineer', 'Frontend Developer', 'Backend Developer', 'Data Scientist', 'Product Manager', 'DevOps Engineer', 'ML Engineer', 'Designer'];
const DIFFICULTIES = [
  { value: 'junior', label: 'Junior' },
  { value: 'mid', label: 'Mid-level' },
  { value: 'senior', label: 'Senior' },
];

/** A labelled field row: the label and its help on the left, the control on the right (stacked on phones). */
function Field({ label, help, htmlFor, children }: { label: string; help?: string; htmlFor?: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-2 sm:grid-cols-[200px_minmax(0,1fr)] sm:gap-6 py-5 first:pt-0 last:pb-0">
      <div>
        <label htmlFor={htmlFor} className="block text-[13px] font-medium text-primary">{label}</label>
        {help && <p className="text-xs text-tertiary mt-0.5">{help}</p>}
      </div>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

export default function CandidatePractice() {
  const navigate = useNavigate();
  const [jobRole, setJobRole] = useState('Software Engineer');
  const [difficulty, setDifficulty] = useState('mid');
  const [techStack, setTechStack] = useState('');
  const [numQuestions, setNumQuestions] = useState(5);
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await candidateService.startPractice({
        job_role: jobRole,
        difficulty,
        tech_stack: techStack || undefined,
        num_questions: numQuestions,
      });
      navigate(`/interview/${res.session_id}`);
    } catch {
      toast.error('Could not start the practice interview. Try again in a moment.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Practice interview"
        description="A mock interview with AURA, to warm up for a real one and see feedback on every answer."
      />

      <form onSubmit={handleStart}>
        <Card padding="lg">
          <div className="divide-y divide-[var(--divider)]">
            <Field label="Role" help="The job you want to practise for.">
              <Select value={jobRole} onChange={setJobRole} options={ROLES.map(r => ({ value: r, label: r }))} />
            </Field>

            <Field label="Level" help="How senior the questions should be.">
              <div role="radiogroup" aria-label="Level" className="inline-grid grid-cols-3 gap-0.5 p-0.5 rounded-lg bg-hover w-full sm:w-auto">
                {DIFFICULTIES.map(d => (
                  <button
                    key={d.value}
                    type="button"
                    role="radio"
                    aria-checked={difficulty === d.value}
                    onClick={() => setDifficulty(d.value)}
                    className={`h-7 px-4 rounded-md text-[13px] font-medium transition-colors ${
                      difficulty === d.value ? 'bg-section text-primary shadow-sm' : 'text-secondary hover:text-primary'
                    }`}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </Field>

            <Field label="Tech stack" help="Optional. Questions lean towards these." htmlFor="tech-stack">
              <Input id="tech-stack" value={techStack} onChange={e => setTechStack(e.target.value)} placeholder="e.g. Python, React, AWS" />
            </Field>

            <Field label="Questions" help="More questions take longer but give a fuller picture.">
              <Slider value={numQuestions} onChange={setNumQuestions} min={3} max={20} step={1} />
            </Field>
          </div>
        </Card>

        <div className="mt-4 flex items-center justify-end gap-3">
          <p className="text-xs text-tertiary hidden sm:block">You can end a practice interview at any time.</p>
          <Button type="submit" size="lg" loading={loading}>Start practice interview</Button>
        </div>
      </form>
    </div>
  );
}
