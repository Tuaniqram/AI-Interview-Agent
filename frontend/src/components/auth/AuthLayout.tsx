import { ReactNode } from 'react';
import { AuthBrandPanel } from './AuthBrandPanel';

interface AuthLayoutProps {
  role: 'org' | 'candidate';
  children: ReactNode;
}

export function AuthLayout({ role, children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen flex">
      <div className="hidden lg:flex lg:w-1/2 xl:w-[55%] flex-none">
        <AuthBrandPanel role={role} />
      </div>

      <div className="flex-1 min-h-screen flex items-center justify-center p-6 bg-[var(--bg-page)]">
        <div className="w-full max-w-md">
          {children}
        </div>
      </div>
    </div>
  );
}
