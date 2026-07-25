import { ReactNode } from 'react';
import { AuthBrandPanel } from './AuthBrandPanel';

interface AuthLayoutProps {
  role: 'org' | 'candidate';
  children: ReactNode;
}

export function AuthLayout({ role, children }: AuthLayoutProps) {
  return (
    <div className="h-screen grid lg:grid-cols-[1fr_500px]">
      <div className="hidden lg:block h-full overflow-hidden">
        <AuthBrandPanel role={role} />
      </div>

      <div className="flex items-center justify-center p-6 bg-[var(--bg-page)] h-full overflow-y-auto relative">
        <div className="absolute inset-0 bg-gradient-to-br from-[var(--action-primary)]/[0.04] to-transparent" />
        <div className="w-full max-w-[448px] py-8 relative">
          {children}
        </div>
      </div>
    </div>
  );
}
