import { Link } from 'react-router-dom';
import { Mail, MessageSquare, ArrowLeft } from 'lucide-react';

export default function ContactUs() {
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
        <div className="w-full max-w-lg">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] mb-6 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Home
          </Link>

          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">Contact Us</h1>
            <p className="text-[var(--text-secondary)] mt-1">Have a question or need help? We'd love to hear from you.</p>
          </div>

          <div className="space-y-4">
            <a
              href="mailto:support@aiinterviewagent.com"
              className="flex items-center gap-4 p-4 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)] hover:border-[var(--action-primary)] transition-colors group"
            >
              <div className="w-10 h-10 rounded-lg bg-[var(--action-primary)]/10 flex items-center justify-center shrink-0">
                <Mail className="w-5 h-5 text-[var(--action-primary)]" />
              </div>
              <div>
                <p className="text-sm font-medium text-[var(--text-primary)] group-hover:text-[var(--action-primary)] transition-colors">Email Us</p>
                <p className="text-xs text-[var(--text-secondary)]">support@aiinterviewagent.com</p>
              </div>
            </a>

            <a
              href="mailto:support@aiinterviewagent.com?subject=Support Request"
              className="flex items-center gap-4 p-4 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)] hover:border-[var(--action-primary)] transition-colors group"
            >
              <div className="w-10 h-10 rounded-lg bg-[var(--action-primary)]/10 flex items-center justify-center shrink-0">
                <MessageSquare className="w-5 h-5 text-[var(--action-primary)]" />
              </div>
              <div>
                <p className="text-sm font-medium text-[var(--text-primary)] group-hover:text-[var(--action-primary)] transition-colors">Send a Message</p>
                <p className="text-xs text-[var(--text-secondary)]">We typically respond within 24 hours</p>
              </div>
            </a>
          </div>

          <div className="mt-8 p-4 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)]">
            <p className="text-xs text-[var(--text-secondary)] text-center">
              Prefer not to email? Check out our{' '}
              <Link to="/opportunity-hub" className="text-[var(--action-primary)] hover:underline">
                Opportunity Hub
              </Link>{' '}
              or head back{' '}
              <Link to="/" className="text-[var(--action-primary)] hover:underline">
                home
              </Link>.
            </p>
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
