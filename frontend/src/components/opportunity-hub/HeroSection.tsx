import { Search, TrendingUp, Sparkles } from 'lucide-react';

interface HeroSectionProps {
  search: string;
  onSearchChange: (value: string) => void;
}

const POPULAR_SKILLS = ['Python', 'React', 'TypeScript', 'Machine Learning', 'Data Science', 'Product Management', 'UI/UX', 'DevOps'];

export function HeroSection({ search, onSearchChange }: HeroSectionProps) {
  return (
    <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-[#4C1D95] via-[#5B21B6] to-[#6D28D9] px-6 py-6 sm:px-8 sm:py-7">
      <div className="absolute top-0 right-0 w-72 h-72 bg-[#7C3AED]/20 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
      <div className="absolute bottom-0 left-0 w-56 h-56 bg-[#A78BFA]/10 rounded-full blur-3xl translate-y-1/3 -translate-x-1/4" />

      <div className="relative z-10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="w-4 h-4 text-[#C4B5FD]" />
            <span className="text-[11px] font-semibold uppercase tracking-widest text-[#A78BFA]">Opportunity Hub</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white leading-tight" style={{ textShadow: '0 1px 8px rgba(0,0,0,0.25)' }}>
            Find your next <span className="text-[#DDD6FE]">career opportunity</span>
          </h1>
          <p className="text-sm text-[#E9D5FF] mt-1 max-w-xl font-medium">
            Browse open interview positions from top organizations and apply with one click.
          </p>
        </div>

        <div className="relative w-full sm:w-72 shrink-0">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#C4B5FD]" />
          <input
            type="text"
            value={search}
            onChange={e => onSearchChange(e.target.value)}
            placeholder="Search by skill, role, or org..."
            className="w-full pl-9 pr-3 py-2.5 text-sm bg-white/15 backdrop-blur-sm text-white rounded-lg border border-white/20 focus:outline-none focus:ring-2 focus:ring-[#A78BFA]/50 focus:border-[#C4B5FD]/60 placeholder:text-[#C4B5FD]/60 transition-all"
          />
        </div>
      </div>

      <div className="relative z-10 mt-4 flex items-center gap-2 flex-wrap">
        <TrendingUp className="w-3.5 h-3.5 text-[#A78BFA]" />
        <span className="text-xs text-[#C4B5FD] font-semibold">Popular:</span>
        {POPULAR_SKILLS.map(skill => (
          <button
            key={skill}
            onClick={() => onSearchChange(skill)}
            className="text-xs px-2.5 py-0.5 rounded-full bg-white/12 text-[#E9D5FF] hover:bg-white/25 hover:text-white transition-all font-medium"
          >
            {skill}
          </button>
        ))}
      </div>
    </div>
  );
}
