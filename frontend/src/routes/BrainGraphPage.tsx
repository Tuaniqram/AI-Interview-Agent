import { Link, useSearchParams } from "react-router-dom";
import BrainGraph from "../components/graph/BrainGraph";

const DEFAULT_SID = "9f025266-26b8-4cbe-8b8c-b883c5436eea";

export function BrainGraphPage() {
  const [params] = useSearchParams();
  const sid = params.get("sid") || DEFAULT_SID;

  return (
    <div className="min-h-screen bg-[#05070f] text-slate-200">
      <header className="sticky top-0 z-20 border-b border-white/10 bg-[#05070f]/85 backdrop-blur">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between gap-4 px-5 py-3">
          <div className="flex items-center gap-3 min-w-0">
            <Link to="/" className="flex-none text-sm text-slate-400 hover:text-white transition-colors">
              ← landing
            </Link>
            <span className="h-4 w-px bg-white/15" />
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold text-white">AURA Brain · the 13 layers</div>
              <div className="truncate text-[11px] text-slate-500">
                how this interview reached its hiring summary — one graph, thirteen views
              </div>
            </div>
          </div>
          <div className="hidden font-mono text-[11px] text-slate-500 sm:block">{sid}</div>
        </div>
      </header>
      <main className="mx-auto max-w-[1440px] p-4 md:p-6">
        <BrainGraph sid={sid} title="AURA Brain · 13 Layers" />
        <p className="mt-4 text-center text-xs text-slate-500">
          drag nodes · scrub or play the timeline · click any of the 13 layers to isolate what fed the verdict
        </p>
      </main>
    </div>
  );
}
