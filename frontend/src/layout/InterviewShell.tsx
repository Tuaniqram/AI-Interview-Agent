import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';

export function InterviewShell() {
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'dark');
  }, []);

  return (
    <div className="fixed inset-0 bg-page">
      <Outlet />
    </div>
  );
}
