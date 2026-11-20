import type { ReactNode } from 'react';

/**
 * Proof. There are no real customers, measurements or quotes in the code base, so every item here is a clearly
 * marked placeholder to be replaced with a real, permissioned one. Nothing on this section is invented.
 */
function Placeholder({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-ui-lg border border-dashed border-border-strong p-5">
      <p className="mb-3 font-mono text-[11px] uppercase tracking-wide text-warning-text">Placeholder · {label}</p>
      {children}
    </div>
  );
}

export function ProofSection() {
  return (
    <section id="proof" className="border-t border-border">
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 md:py-24">
        <p className="font-mono text-xs uppercase tracking-wide text-muted">Proof</p>
        <h2 className="font-display mt-3 max-w-3xl text-3xl text-primary md:text-4xl">
          What teams and candidates say.
        </h2>
        <p className="mt-3 max-w-2xl text-sm text-secondary">
          Replace each box below with a real customer, a measured result or a quote you have permission to use.
        </p>

        <div className="mt-10 grid gap-4 md:grid-cols-3">
          <Placeholder label="customer names">
            <p className="text-sm text-secondary">Name the teams that use AURA, with their permission.</p>
          </Placeholder>
          <Placeholder label="measured result">
            <p className="font-mono text-2xl text-primary">[ metric ]</p>
            <p className="mt-1 text-sm text-secondary">For example: time from application to a first-round result. Say how it was measured.</p>
          </Placeholder>
          <Placeholder label="recruiter quote">
            <p className="text-sm text-secondary">“[Quote about being able to check a recommendation.]”</p>
            <p className="mt-2 font-mono text-xs text-muted">Name, role, company</p>
          </Placeholder>
          <Placeholder label="candidate quote">
            <p className="text-sm text-secondary">“[Quote about how the interview felt.]”</p>
            <p className="mt-2 font-mono text-xs text-muted">Name or first name, role applied for</p>
          </Placeholder>
        </div>
      </div>
    </section>
  );
}
