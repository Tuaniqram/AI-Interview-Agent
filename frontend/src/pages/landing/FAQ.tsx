import { useState } from 'react';
import { ChevronDown } from 'lucide-react';

const faqs = [
  {
    q: 'How does the AI conduct interviews?',
    a: 'The AI uses two LangGraph workflows — one generates adaptive questions based on the candidate\'s answers and company context, another evaluates responses in real time. Each interview is a structured conversation with adjustable difficulty.',
  },
  {
    q: 'Can I customize questions for my company?',
    a: 'Yes. Upload your company documents (tech specs, job descriptions, culture docs) and the RAG pipeline indexes them into Pinecone. Every question is grounded in your specific requirements.',
  },
  {
    q: 'What interview modes are available?',
    a: 'Three modes: Typing (text-based chat), Voice (speech-to-text dictation), and Avatar (3D AI interviewer with lip-sync and expressions). You can switch modes between interviews.',
  },
  {
    q: 'How accurate is the evaluation?',
    a: 'The system scores candidates on technical skills, communication, and problem-solving using LLM-based analysis. Scores are 0–10 with detailed strengths/weaknesses breakdowns. Most teams validate against their own rubric.',
  },
  {
    q: 'Is my data secure?',
    a: 'Yes. Session-scoped data isolation ensures no candidate data leaks between interviews. All data is stored in Supabase with row-level security. Company documents are encrypted at rest in Pinecone.',
  },
  {
    q: 'How long does it take to set up?',
    a: 'Under 5 minutes. Create a company, upload your knowledge base, pick a template, and start your first interview. The system pre-generates questions using your company context automatically.',
  },
];

export function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section className="py-24 px-6 bg-[#0a0a0b]">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold text-[#f2f2f5] mb-4">Frequently asked questions</h2>
          <p className="text-[#a8a8b3] text-lg">
            Everything you need to know about the platform.
          </p>
        </div>

        <div className="space-y-2">
          {faqs.map((faq, i) => {
            const isOpen = openIndex === i;
            return (
              <div
                key={i}
                className="rounded-xl overflow-hidden transition-all duration-200"
                style={{
                  background: isOpen ? 'rgba(28,28,31,0.8)' : 'rgba(28,28,31,0.4)',
                  boxShadow: '0 0 0 1px rgba(255,255,255,0.04)',
                }}
              >
                <button
                  onClick={() => setOpenIndex(isOpen ? null : i)}
                  className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left"
                >
                  <span className="text-sm font-medium text-[#f2f2f5]">{faq.q}</span>
                  <ChevronDown
                    className={`w-4 h-4 text-[#6f6f7a] shrink-0 transition-transform duration-200 ${
                      isOpen ? 'rotate-180' : ''
                    }`}
                  />
                </button>
                {isOpen && (
                  <div className="px-5 pb-4">
                    <p className="text-sm text-[#a8a8b3] leading-relaxed">{faq.a}</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
