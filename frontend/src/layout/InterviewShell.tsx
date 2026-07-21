import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';

export function InterviewShell() {
  useEffect(() => {
    const saved = localStorage.getItem('ai-interview-theme');
    if (!saved) {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  }, []);

  return (
    <div className="fixed inset-0 bg-page">
      <Outlet />
    </div>
  );
}
