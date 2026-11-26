import { Fragment } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, Search } from 'lucide-react';

const ACRONYMS: Record<string, string> = { llm: 'LLM', it: 'IT', api: 'API' };
const UUID_SEGMENT = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Each area's landing page. `/candidate` on its own has no page, so its crumb must go to the dashboard. */
const AREA_HOME: Record<string, string> = { candidate: '/candidate/dashboard', org: '/org', admin: '/admin' };
const AREA_LABEL: Record<string, string> = { candidate: 'Home', org: 'Dashboard', admin: 'Admin' };

/** A readable breadcrumb label for one URL segment: ids become "#1234abcd", known acronyms stay capitalised. */
function crumbLabel(segment: string): string {
  if (UUID_SEGMENT.test(segment)) return '#' + segment.slice(0, 8);
  const s = ACRONYMS[segment.toLowerCase()] ?? segment.replace(/-/g, ' ');
  return s.charAt(0).toUpperCase() + s.slice(1);
}

interface TopBarProps {
  onMenuToggle?: () => void;
  onOpenSearch?: () => void;
  /** Labels for known paths, taken from the nav, so a crumb reads "Candidates" rather than "candidates". */
  labels?: Record<string, string>;
}

/** The content panel's header: where you are, as a breadcrumb trail. The last crumb is the current page. */
export function TopBar({ onMenuToggle, onOpenSearch, labels = {} }: TopBarProps) {
  const segments = useLocation().pathname.split('/').filter(Boolean);
  // A report lives at /interview/:id/report, but /interview/:id is the live room: never link there from here.
  const isReport = segments[0] === 'interview' && segments[segments.length - 1] === 'report';
  const crumbs = isReport ? [{ to: '/sessions', label: labels['/sessions'] ?? 'Sessions' }, { to: '#report', label: 'Report' }] : segments.map((seg, i) => {
    const path = '/' + segments.slice(0, i + 1).join('/');
    const to = i === 0 ? AREA_HOME[seg] ?? path : path;
    const label = labels[path] ?? (i === 0 ? AREA_LABEL[seg] : undefined) ?? crumbLabel(seg);
    return { to, label };
  })
    // "/candidate" → "/candidate/dashboard" would read Home › Dashboard; keep one.
    .filter((c, i, all) => i === 0 || c.to !== all[i - 1].to);

  return (
    <header className="h-12 shrink-0 flex items-center gap-2 px-3 sm:px-5 border-b border-border">
      {onMenuToggle && (
        <button
          onClick={onMenuToggle}
          className="p-1.5 -ml-1 rounded-md text-tertiary hover:text-primary hover:bg-hover lg:hidden"
          aria-label="Open navigation"
        >
          <Menu className="w-4 h-4" />
        </button>
      )}
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 min-w-0 text-[13px]">
        {crumbs.map((c, i) => {
          const last = i === crumbs.length - 1;
          return (
            <Fragment key={c.to + i}>
              {i > 0 && <span className="text-border-strong select-none" aria-hidden>/</span>}
              {last
                ? <span className="font-medium text-primary truncate" aria-current="page">{c.label}</span>
                : <Link to={c.to} className="text-tertiary hover:text-primary transition-colors truncate shrink-0">{c.label}</Link>}
            </Fragment>
          );
        })}
      </nav>
      {onOpenSearch && (
        <button
          onClick={onOpenSearch}
          className="ml-auto p-1.5 rounded-md text-tertiary hover:text-primary hover:bg-hover lg:hidden"
          aria-label="Search"
        >
          <Search className="w-4 h-4" />
        </button>
      )}
    </header>
  );
}
