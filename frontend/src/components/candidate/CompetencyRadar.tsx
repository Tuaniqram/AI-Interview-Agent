import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Tooltip, ResponsiveContainer } from 'recharts';
import type { CompetencyScore } from '../../types/candidate';

interface CompetencyRadarProps {
  scores: CompetencyScore[];
}

export function CompetencyRadar({ scores }: CompetencyRadarProps) {
  const categories = [...new Set(scores.map(s => s.category))];
  const data = categories.map(cat => {
    const catScores = scores.filter(s => s.category === cat);
    const avg = catScores.length
      ? catScores.reduce((a, b) => a + b.average_score, 0) / catScores.length
      : 0;
    return { category: cat.charAt(0).toUpperCase() + cat.slice(1), score: Math.round(avg * 10) / 10 };
  });

  if (data.length === 0) return null;

  return (
    <div className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)]">
      <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4">Skill Breakdown</h3>
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={data}>
          <PolarGrid stroke="var(--border-color)" />
          <PolarAngleAxis dataKey="category" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
          <PolarRadiusAxis domain={[0, 10]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickCount={6} />
          <Radar name="Score" dataKey="score" stroke="#7C3AED" fill="#7C3AED" fillOpacity={0.15} strokeWidth={2} />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-section)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            formatter={(value: any) => [`${value}/10`, 'Score']}
          />
        </RadarChart>
      </ResponsiveContainer>
      <div className="grid grid-cols-2 gap-2 mt-4">
        {scores.slice(0, 6).map(s => (
          <div key={s.competency} className="flex items-center justify-between text-xs">
            <span className="text-[var(--text-secondary)] truncate mr-2">{s.name}</span>
            <span className="font-medium text-[var(--text-primary)] shrink-0">{s.average_score}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
