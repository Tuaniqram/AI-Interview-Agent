import { Link } from 'react-router-dom';
import { Home, Search, Mail } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[var(--bg-page)] flex flex-col">
      <header className="border-b border-[var(--border-color)] bg-[var(--bg-section)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center">
          <Link to="/" className="flex items-center gap-2">
            <img src="/favicon.svg" className="w-7 h-7" alt="" />
            <span className="text-xl font-bold text-[var(--text-primary)]">AI Interview Agent</span>
          </Link>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center p-6">
        <div className="text-center max-w-md">
          <div className="text-8xl font-bold text-[var(--action-primary)]/20 mb-4">404</div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Page Not Found</h1>
          <p className="text-[var(--text-secondary)] mb-8">
            The page you're looking for doesn't exist or has been moved.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              to="/"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[var(--action-primary)] text-white text-sm font-medium hover:opacity-90 transition-opacity"
            >
              <Home className="w-4 h-4" />
              Go Home
            </Link>
            <Link
              to="/opportunity-hub"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-[var(--border-color)] text-[var(--text-primary)] text-sm font-medium hover:bg-[var(--bg-section)] transition-colors"
            >
              <Search className="w-4 h-4" />
              Browse Opportunities
            </Link>
            <Link
              to="/contact"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-[var(--border-color)] text-[var(--text-primary)] text-sm font-medium hover:bg-[var(--bg-section)] transition-colors"
            >
              <Mail className="w-4 h-4" />
              Contact Us
            </Link>
          </div>
        </div>
      </main>

      <footer className="border-t border-[var(--border-color)] py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-[var(--text-secondary)]">
          AI Interview Agent. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
