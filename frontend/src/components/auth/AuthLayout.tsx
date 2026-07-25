import { ReactNode } from 'react';
import { AuthBrandPanel } from './AuthBrandPanel';

interface AuthLayoutProps {
  role: 'org' | 'candidate';
  children: ReactNode;
}

export function AuthLayout({ role, children }: AuthLayoutProps) {
  return (
    <div className="h-screen grid lg:grid-cols-[1fr_3fr]">
      <div className="hidden lg:block h-full overflow-hidden">
        <AuthBrandPanel role={role} />
      </div>

      <div className="flex items-center justify-center p-6 bg-[var(--bg-page)] h-full overflow-y-auto">
        <div className="w-full max-w-md py-8">
          {children}
        </div>
      </div>
    </div>
  );
}
