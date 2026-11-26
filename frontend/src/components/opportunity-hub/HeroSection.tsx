import { Search } from 'lucide-react';

interface HeroSectionProps {
  search: string;
  onSearchChange: (value: string) => void;
}

const POPULAR_SKILLS = ['Python', 'React', 'TypeScript', 'Machine Learning', 'Data Science', 'Product Management', 'UI/UX', 'DevOps'];

/** The hub's opening: what this place is, and the search box that is its main tool. */
export function HeroSection({ search, onSearchChange }: HeroSectionProps) {
  return (
    <div className="pb-6 border-b border-border">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="min-w-0">
          <h1 className="text-[26px] leading-8 font-semibold tracking-[-0.02em] text-primary">Open interviews</h1>
          <p className="text-sm text-secondary mt-1 max-w-[60ch]">
            Roles from organizations hiring through AI interviews. Pick one, apply, and take the interview when it suits you.
          </p>
        </div>
        <div className="relative w-full md:w-80 shrink-0">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-tertiary pointer-events-none" />
          <input
            type="search"
            value={search}
            onChange={e => onSearchChange(e.target.value)}
            placeholder="Search by skill, role or organization"
            aria-label="Search open interviews"
            className="w-full h-9 pl-8 pr-3 text-[13px] bg-input text-primary rounded-md border border-[var(--border-strong)] shadow-sm focus:outline-none focus:ring-[3px] focus:ring-[var(--focus-ring)] focus:border-[var(--action-primary)] placeholder:text-tertiary"
          />
        </div>
      </div>

      <div className="mt-4 flex items-center gap-1.5 flex-wrap">
        <span className="text-[13px] text-tertiary mr-1">Popular</span>
        {POPULAR_SKILLS.map(skill => (
          <button
            key={skill}
            onClick={() => onSearchChange(skill)}
            aria-pressed={search === skill}
            className={`text-xs h-6 px-2.5 rounded-md border transition-colors ${
              search === skill
                ? 'bg-action-primary-soft border-transparent text-action-primary font-medium'
                : 'border-border text-secondary hover:border-border-strong hover:text-primary'
            }`}
          >
            {skill}
          </button>
        ))}
      </div>
    </div>
  );
}
