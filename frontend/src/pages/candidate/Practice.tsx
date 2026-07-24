import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { candidateService } from '../../services/candidateService';
import { Button } from '../../components/shared/Button';
import { PageHeader } from '../../components/shared/PageHeader';

const ROLES = ['Software Engineer', 'Frontend Developer', 'Backend Developer', 'Data Scientist', 'Product Manager', 'DevOps Engineer', 'ML Engineer', 'Designer'];
const DIFFICULTIES = [
  { value: 'junior', label: 'Junior' },
  { value: 'mid', label: 'Mid-Level' },
  { value: 'senior', label: 'Senior' },
];

export default function CandidatePractice() {
  const navigate = useNavigate();
  const [jobRole, setJobRole] = useState('Software Engineer');
  const [difficulty, setDifficulty] = useState('mid');
  const [techStack, setTechStack] = useState('');
  const [numQuestions, setNumQuestions] = useState(5);
  const [loading, setLoading] = useState(false);

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
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <PageHeader
        title="Practice Interview"
        description="Create a mock interview to practice with AI"
      />

      <form onSubmit={handleStart} className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)] space-y-5">
        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">Job Role</label>
          <select
            value={jobRole}
            onChange={(e) => setJobRole(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]"
          >
            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">Difficulty</label>
          <div className="flex gap-2">
            {DIFFICULTIES.map((d) => (
              <button
                key={d.value}
                type="button"
                onClick={() => setDifficulty(d.value)}
                className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
                  difficulty === d.value
                    ? 'bg-[var(--action-primary)] text-white border-[var(--action-primary)]'
                    : 'border-[var(--border-color)] text-[var(--text-secondary)] hover:border-[var(--action-primary)]'
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Tech Stack (optional)</label>
          <input
            type="text"
            value={techStack}
            onChange={(e) => setTechStack(e.target.value)}
            placeholder="e.g. Python, React, AWS"
            className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Number of Questions</label>
          <input
            type="number"
            value={numQuestions}
            onChange={(e) => setNumQuestions(Number(e.target.value))}
            min={3}
            max={20}
            className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]"
          />
        </div>

        <Button type="submit" loading={loading} className="w-full">
          Start Practice Interview
        </Button>
      </form>
    </div>
  );
}
