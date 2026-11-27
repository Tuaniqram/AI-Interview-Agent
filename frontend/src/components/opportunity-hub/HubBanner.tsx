import { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';

/** Fine dot grid: gives the band some texture without gradients or glow. */
const DOTS = "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16'%3E%3Ccircle cx='1' cy='1' r='1' fill='%23ffffff' fill-opacity='0.07'/%3E%3C/svg%3E\")";

interface HubBannerProps {
  back?: { to: string; label: string };
  eyebrow?: ReactNode;
  title: ReactNode;
  children?: ReactNode;
  /** Shown on the right on wide screens (the search box, for example). */
  aside?: ReactNode;
  leading?: ReactNode;
}

/** The full-width band that opens every hub page: deep pine with white text. */
export function HubBanner({ back, eyebrow, title, children, aside, leading }: HubBannerProps) {
  return (
    <div className="bg-[var(--hub-banner)] text-white" style={{ backgroundImage: DOTS }}>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-6 pb-8 sm:pt-7 sm:pb-10">
        {back && (
          <Link to={back.to} className="inline-flex items-center gap-1 text-[13px] text-white/70 hover:text-white mb-5 rounded">
            <ChevronLeft className="w-4 h-4" /> {back.label}
          </Link>
        )}
        <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div className="flex items-start gap-4 min-w-0">
            {leading}
            <div className="min-w-0">
              {eyebrow && <div className="text-[13px] text-white/70 mb-0.5">{eyebrow}</div>}
              <h1 className="text-[26px] sm:text-[30px] leading-tight font-semibold tracking-[-0.02em]">{title}</h1>
              {children && <div className="mt-2 text-sm text-white/75 max-w-[62ch]">{children}</div>}
            </div>
          </div>
          {aside && <div className="w-full md:w-auto shrink-0">{aside}</div>}
        </div>
      </div>
    </div>
  );
}

/** The page body under the banner. */
export function HubBody({ children }: { children: ReactNode }) {
  return <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">{children}</div>;
}
