-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.companies (
  id bigint NOT NULL DEFAULT nextval('companies_id_seq'::regclass),
  name text NOT NULL,
  website text,
  description text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT companies_pkey PRIMARY KEY (id)
);
CREATE TABLE public.company_documents (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  company_id bigint NOT NULL,
  filename text NOT NULL,
  document_type text NOT NULL DEFAULT 'pdf'::text,
  pinecone_namespace text NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT company_documents_pkey PRIMARY KEY (id),
  CONSTRAINT company_documents_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id)
);
CREATE TABLE public.interview_sessions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  company_id bigint NOT NULL,
  candidate_id text,
  job_role text NOT NULL,
  interview_type text DEFAULT 'company'::text,
  status text DEFAULT 'active'::text,
  current_phase text DEFAULT 'intro'::text,
  current_question_number integer DEFAULT 0,
  total_questions integer,
  started_at timestamp with time zone DEFAULT now(),
  ended_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  final_score numeric,
  final_feedback text,
  CONSTRAINT interview_sessions_pkey PRIMARY KEY (id),
  CONSTRAINT interview_sessions_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id)
);
CREATE TABLE public.interview_messages (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL,
  role text NOT NULL,
  message_type text NOT NULL,
  content text NOT NULL,
  question_number integer DEFAULT 0,
  phase text,
  score numeric,
  follow_up_question text,
  evaluated_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT interview_messages_pkey PRIMARY KEY (id),
  CONSTRAINT interview_messages_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.interview_sessions(id)
);
CREATE TABLE public.interview_evaluations (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL,
  message_id uuid NOT NULL,
  score numeric CHECK (score >= 0::numeric AND score <= 10::numeric),
  technical_score numeric,
  communication_score numeric,
  strengths text,
  weaknesses text,
  feedback_detail text,
  evaluated_at timestamp with time zone DEFAULT now(),
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT interview_evaluations_pkey PRIMARY KEY (id),
  CONSTRAINT interview_evaluations_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.interview_sessions(id),
  CONSTRAINT interview_evaluations_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.interview_messages(id)
);
CREATE TABLE public.user_progress (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  session_id uuid,
  candidate_identifier text,
  average_score numeric,
  total_questions_answered integer,
  questions_correct integer,
  strengths_improvement_count integer,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT user_progress_pkey PRIMARY KEY (id),
  CONSTRAINT user_progress_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.interview_sessions(id)
);