-- ============================================================================
-- AI Interview Agent - Final 33-Table Schema (IT-Only Scope)
-- PostgreSQL 15+
--
-- Source of truth for the final table list:
--   docs/it-scope/04-final-table-list.md
--
-- Keeps marketplace/opportunity hub, candidate resumes, org documents,
-- evaluation, and accept/reject workflow.
-- Removes departments, scheduling, calibration, and 9 separate
-- evaluation/intelligence tables.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION set_last_updated()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.last_updated = now();
    RETURN NEW;
END;
$$;

-- ============================================================================
-- 1. Tenancy, users, and access
-- ============================================================================

CREATE TABLE organizations (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id uuid NOT NULL,
    name          text NOT NULL,
    slug          text NOT NULL UNIQUE,
    logo_url      text,
    description   text,
    website       text,
    settings      jsonb NOT NULL DEFAULT '{}'::jsonb,
    is_active     boolean NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email         text NOT NULL,
    password_hash text NOT NULL,
    name          text NOT NULL,
    avatar_url    text,
    is_admin      boolean NOT NULL DEFAULT false,
    is_active     boolean NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email));

ALTER TABLE organizations
    ADD CONSTRAINT organizations_owner_user_id_fkey
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE RESTRICT;

CREATE INDEX idx_organizations_owner_user_id ON organizations (owner_user_id);

CREATE TABLE refresh_tokens (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  text NOT NULL,
    expires_at  timestamptz NOT NULL,
    revoked     boolean NOT NULL DEFAULT false,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE user_password_reset_tokens (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  text NOT NULL,
    expires_at  timestamptz NOT NULL,
    used        boolean NOT NULL DEFAULT false,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens (user_id);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens (token_hash);
CREATE INDEX idx_user_reset_tokens_user ON user_password_reset_tokens (user_id);
CREATE INDEX idx_user_reset_tokens_hash ON user_password_reset_tokens (token_hash);

-- ============================================================================
-- 2. IT documents and catalog
-- ============================================================================

CREATE TABLE organization_documents (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id             uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    filename           text NOT NULL,
    document_type      text NOT NULL DEFAULT 'pdf',
    storage_path       text,
    content_hash       text,
    pinecone_namespace text NOT NULL,
    created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE it_roles (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        text NOT NULL UNIQUE,
    family      text NOT NULL
                CHECK (family IN (
                    'software_engineering', 'frontend', 'backend', 'fullstack',
                    'mobile', 'game', 'embedded', 'qa', 'devops', 'cloud',
                    'infrastructure', 'network', 'security', 'data', 'ai_ml',
                    'database', 'it_support', 'architecture', 'it_management',
                    'business_analysis', 'design', 'erp_crm', 'technical_writing'
                )),
    name        text NOT NULL,
    description text,
    level_min   text NOT NULL DEFAULT 'junior'
                CHECK (level_min IN ('intern', 'junior', 'mid', 'senior', 'lead', 'principal', 'manager', 'director')),
    level_max   text NOT NULL DEFAULT 'principal'
                CHECK (level_max IN ('intern', 'junior', 'mid', 'senior', 'lead', 'principal', 'manager', 'director')),
    is_active   boolean NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT it_roles_slug_format
        CHECK (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$')
);

CREATE TABLE competencies (
    id                   text PRIMARY KEY,
    name                 text NOT NULL,
    category             text NOT NULL
                         CHECK (category IN (
                             'technical', 'behavioral', 'cognitive',
                             'experience', 'design', 'product',
                             'operations', 'general'
                         )),
    primary_dimension    text NOT NULL
                         CHECK (primary_dimension IN (
                             'technical', 'communication', 'behavioral',
                             'reasoning', 'confidence', 'completeness', 'domain'
                         )),
    evidence_dimensions  text[] NOT NULL DEFAULT '{}'::text[],
    default_min_evidence smallint NOT NULL DEFAULT 1
                         CHECK (default_min_evidence BETWEEN 0 AND 10),
    description          text,
    scope                text NOT NULL DEFAULT 'IT' CHECK (scope = 'IT'),
    is_active            boolean NOT NULL DEFAULT true,
    created_at           timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT competencies_evidence_dimensions_valid
        CHECK (evidence_dimensions <@ ARRAY[
            'technical', 'communication', 'behavioral', 'reasoning',
            'confidence', 'completeness', 'domain'
        ]::text[])
);

CREATE TABLE role_competencies (
    role_id        uuid NOT NULL REFERENCES it_roles(id) ON DELETE CASCADE,
    competency_id  text NOT NULL REFERENCES competencies(id) ON DELETE CASCADE,
    weight         numeric(5,2) NOT NULL DEFAULT 1.00
                   CHECK (weight > 0 AND weight <= 100),
    required_level text
                   CHECK (required_level IS NULL OR required_level IN (
                       'intern', 'junior', 'mid', 'senior',
                       'lead', 'principal', 'manager', 'director'
                   )),
    is_core        boolean NOT NULL DEFAULT true,
    PRIMARY KEY (role_id, competency_id)
);

CREATE INDEX idx_organization_documents_org ON organization_documents (org_id);
CREATE INDEX idx_organization_documents_namespace ON organization_documents (pinecone_namespace);
CREATE INDEX idx_it_roles_family ON it_roles (family) WHERE is_active;
CREATE INDEX idx_it_roles_name_lower ON it_roles (lower(name));
CREATE INDEX idx_role_competencies_competency ON role_competencies (competency_id);

-- ============================================================================
-- 3. Candidates and resumes
-- ============================================================================

CREATE TABLE candidate_profiles (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email                   text NOT NULL,
    name                    text NOT NULL,
    phone                   text,
    resume_url              text,
    password_hash           text,
    google_id               text,
    is_registered           boolean NOT NULL DEFAULT false,
    is_verified             boolean NOT NULL DEFAULT false,
    verified_at             timestamptz,
    verification_token_hash text,
    verification_sent_at    timestamptz,
    skills                  text,
    profile_data            jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX uq_candidate_profiles_email_lower
    ON candidate_profiles (lower(email));
CREATE INDEX idx_candidate_profiles_verified ON candidate_profiles (is_verified);

CREATE TABLE candidate_refresh_tokens (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id uuid NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    token_hash   text NOT NULL,
    expires_at   timestamptz NOT NULL,
    revoked      boolean NOT NULL DEFAULT false,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE candidate_password_reset_tokens (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id uuid NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    token_hash   text NOT NULL,
    expires_at   timestamptz NOT NULL,
    used         boolean NOT NULL DEFAULT false,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE candidate_documents (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id      uuid REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    session_id        uuid,
    filename          text NOT NULL,
    document_type     text NOT NULL DEFAULT 'resume',
    content_hash      text,
    extracted_text    text,
    document_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE candidate_invitations (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id            uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    candidate_email   text NOT NULL,
    candidate_name    text NOT NULL,
    it_role_id        uuid NOT NULL REFERENCES it_roles(id) ON DELETE RESTRICT,
    level_code        text
                      CHECK (level_code IS NULL OR level_code IN (
                          'intern', 'junior', 'mid', 'senior',
                          'lead', 'principal', 'manager', 'director'
                      )),
    job_role_snapshot text NOT NULL,
    token             text NOT NULL UNIQUE,
    interview_config  jsonb NOT NULL DEFAULT '{}'::jsonb,
    status            text NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'accepted', 'completed', 'expired', 'revoked')),
    expires_at        timestamptz NOT NULL,
    created_by        uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_candidate_refresh_tokens_candidate ON candidate_refresh_tokens (candidate_id);
CREATE INDEX idx_candidate_refresh_tokens_hash ON candidate_refresh_tokens (token_hash);
CREATE INDEX idx_candidate_reset_tokens_candidate ON candidate_password_reset_tokens (candidate_id);
CREATE INDEX idx_candidate_reset_tokens_hash ON candidate_password_reset_tokens (token_hash);
CREATE INDEX idx_candidate_documents_candidate ON candidate_documents (candidate_id);
CREATE INDEX idx_candidate_documents_session ON candidate_documents (session_id);
CREATE INDEX idx_candidate_invitations_org ON candidate_invitations (org_id);
CREATE INDEX idx_candidate_invitations_role ON candidate_invitations (it_role_id);
CREATE INDEX idx_candidate_invitations_status ON candidate_invitations (status);

-- ============================================================================
-- 4. Templates and marketplace
-- ============================================================================

CREATE TABLE scorecard_templates (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name         text NOT NULL,
    competencies jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE interview_templates (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                 uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    it_role_id             uuid NOT NULL REFERENCES it_roles(id) ON DELETE RESTRICT,
    level_code             text
                           CHECK (level_code IS NULL OR level_code IN (
                               'intern', 'junior', 'mid', 'senior',
                               'lead', 'principal', 'manager', 'director'
                           )),
    name                   text NOT NULL,
    job_role_snapshot      text NOT NULL,
    description            text,
    interview_style        text NOT NULL DEFAULT 'STANDARD',
    competencies           jsonb NOT NULL DEFAULT '[]'::jsonb,
    suggested_competencies jsonb,
    total_questions        integer NOT NULL DEFAULT 10
                           CHECK (total_questions BETWEEN 1 AND 100),
    scorecard_template_id  uuid REFERENCES scorecard_templates(id) ON DELETE SET NULL,
    created_at             timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public_interviews (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id             uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    it_role_id         uuid NOT NULL REFERENCES it_roles(id) ON DELETE RESTRICT,
    level_code         text
                       CHECK (level_code IS NULL OR level_code IN (
                           'intern', 'junior', 'mid', 'senior',
                           'lead', 'principal', 'manager', 'director'
                       )),
    template_id        uuid REFERENCES interview_templates(id) ON DELETE SET NULL,
    title              text NOT NULL,
    description        text,
    rich_description   text,
    interview_mode     text NOT NULL DEFAULT 'typing'
                       CHECK (interview_mode IN ('typing', 'voice', 'avatar')),
    is_open            boolean NOT NULL DEFAULT true,
    verification_method text NOT NULL DEFAULT 'none'
                       CHECK (verification_method IN ('none', 'email', 'token')),
    token              text NOT NULL UNIQUE,
    token_expires_at   timestamptz,
    max_candidates     integer CHECK (max_candidates IS NULL OR max_candidates > 0),
    skills_required    text,
    style_name         text NOT NULL DEFAULT 'STANDARD',
    starts_at          timestamptz,
    expires_at         timestamptz,
    created_at         timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT public_interviews_window_valid
        CHECK (expires_at IS NULL OR starts_at IS NULL OR expires_at > starts_at)
);

CREATE TABLE candidate_saved_listings (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id uuid NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    listing_id   uuid NOT NULL REFERENCES public_interviews(id) ON DELETE CASCADE,
    created_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (candidate_id, listing_id)
);

CREATE INDEX idx_scorecard_templates_org ON scorecard_templates (org_id);
CREATE INDEX idx_interview_templates_org ON interview_templates (org_id);
CREATE INDEX idx_interview_templates_role ON interview_templates (it_role_id);
CREATE INDEX idx_interview_templates_scorecard ON interview_templates (scorecard_template_id);
CREATE INDEX idx_public_interviews_org ON public_interviews (org_id);
CREATE INDEX idx_public_interviews_role ON public_interviews (it_role_id);
CREATE INDEX idx_public_interviews_open ON public_interviews (is_open) WHERE is_open;
CREATE INDEX idx_public_interviews_template ON public_interviews (template_id);
CREATE INDEX idx_saved_listings_candidate ON candidate_saved_listings (candidate_id);
CREATE INDEX idx_saved_listings_listing ON candidate_saved_listings (listing_id);

-- ============================================================================
-- 5. Interview runtime
-- ============================================================================

CREATE TABLE interview_sessions (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                  uuid REFERENCES organizations(id) ON DELETE CASCADE,
    candidate_profile_id    uuid REFERENCES candidate_profiles(id) ON DELETE SET NULL,
    it_role_id              uuid NOT NULL REFERENCES it_roles(id) ON DELETE RESTRICT,
    level_code              text
                            CHECK (level_code IS NULL OR level_code IN (
                                'intern', 'junior', 'mid', 'senior',
                                'lead', 'principal', 'manager', 'director'
                            )),
    job_role_snapshot       text NOT NULL,
    session_type            text NOT NULL DEFAULT 'organization'
                            CHECK (session_type IN ('organization', 'invitation', 'practice', 'public')),
    interaction_mode        text
                            CHECK (interaction_mode IS NULL OR interaction_mode IN ('typing', 'voice', 'avatar')),
    status                  text NOT NULL DEFAULT 'initiating'
                            CHECK (status IN ('initiating', 'active', 'completed', 'cancelled', 'expired')),
    current_phase           text NOT NULL DEFAULT 'intro'
                            CHECK (current_phase IN ('intro', 'experience', 'technical', 'behavioral', 'conclusion')),
    current_question_number integer NOT NULL DEFAULT 0 CHECK (current_question_number >= 0),
    total_questions         integer CHECK (total_questions IS NULL OR total_questions BETWEEN 1 AND 100),
    scorecard_template_id   uuid REFERENCES scorecard_templates(id) ON DELETE SET NULL,
    invite_token            text UNIQUE,
    invite_expires_at       timestamptz,
    started_at              timestamptz NOT NULL DEFAULT now(),
    ended_at                timestamptz,
    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now(),
    final_score             numeric(5,2)
                            CHECK (final_score IS NULL OR (final_score >= 0 AND final_score <= 10)),
    final_feedback          text,
    engine_version          text NOT NULL DEFAULT 'v5',
    CONSTRAINT interview_sessions_end_after_start
        CHECK (ended_at IS NULL OR ended_at >= started_at)
);

CREATE TABLE interview_messages (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id         uuid NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    role               text NOT NULL CHECK (role IN ('assistant', 'user', 'system')),
    message_type       text NOT NULL,
    content            text NOT NULL,
    question_number    integer NOT NULL DEFAULT 0 CHECK (question_number >= 0),
    phase              text,
    score              numeric(5,2) CHECK (score IS NULL OR (score >= 0 AND score <= 10)),
    follow_up_question text,
    evaluated_at       timestamptz,
    created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE interview_evaluations (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          uuid NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    message_id          uuid NOT NULL REFERENCES interview_messages(id) ON DELETE CASCADE,
    score               numeric(5,2) CHECK (score IS NULL OR (score >= 0 AND score <= 10)),
    technical_score     numeric(5,2) CHECK (technical_score IS NULL OR (technical_score >= 0 AND technical_score <= 10)),
    communication_score numeric(5,2) CHECK (communication_score IS NULL OR (communication_score >= 0 AND communication_score <= 10)),
    strengths           text,
    weaknesses          text,
    feedback_detail     text,
    evaluated_at        timestamptz NOT NULL DEFAULT now(),
    created_at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (message_id)
);

CREATE INDEX idx_sessions_org ON interview_sessions (org_id);
CREATE INDEX idx_sessions_candidate ON interview_sessions (candidate_profile_id);
CREATE INDEX idx_sessions_role ON interview_sessions (it_role_id);
CREATE INDEX idx_sessions_status ON interview_sessions (status);
CREATE INDEX idx_sessions_started_at ON interview_sessions (started_at DESC);
CREATE INDEX idx_sessions_final_score ON interview_sessions (final_score)
    WHERE final_score IS NOT NULL;
CREATE INDEX idx_sessions_scorecard_template ON interview_sessions (scorecard_template_id);
CREATE INDEX idx_sessions_invite_token ON interview_sessions (invite_token)
    WHERE invite_token IS NOT NULL;
CREATE INDEX idx_messages_session_question ON interview_messages (session_id, question_number);
CREATE INDEX idx_messages_session_created ON interview_messages (session_id, created_at);
CREATE INDEX idx_evaluations_session ON interview_evaluations (session_id);
CREATE INDEX idx_evaluations_message ON interview_evaluations (message_id);

-- ============================================================================
-- 6. Evaluation and reasoning
-- ============================================================================

CREATE TABLE hypotheses (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id             uuid NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    statement              text NOT NULL,
    competency_id          text REFERENCES competencies(id) ON DELETE SET NULL,
    direction              text NOT NULL CHECK (direction IN ('positive', 'negative')),
    confidence             numeric(5,4) NOT NULL DEFAULT 0
                           CHECK (confidence >= 0 AND confidence <= 1),
    supporting_evidence    uuid[] NOT NULL DEFAULT '{}'::uuid[],
    contradicting_evidence uuid[] NOT NULL DEFAULT '{}'::uuid[],
    status                 text NOT NULL DEFAULT 'untested'
                           CHECK (status IN ('untested', 'testing', 'confirmed', 'refuted')),
    created_at             timestamptz NOT NULL DEFAULT now(),
    last_updated           timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE evidence_store (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id           uuid NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    competency_id        text NOT NULL REFERENCES competencies(id) ON DELETE RESTRICT,
    dimension            text NOT NULL
                         CHECK (dimension IN (
                             'technical', 'communication', 'reasoning',
                             'behavioral', 'confidence', 'completeness', 'domain'
                         )),
    score                numeric(5,2) NOT NULL CHECK (score >= 0 AND score <= 10),
    confidence           numeric(5,4) NOT NULL DEFAULT 1
                         CHECK (confidence >= 0 AND confidence <= 1),
    evidence_text        text NOT NULL,
    source_question      text NOT NULL,
    question_number      integer NOT NULL CHECK (question_number >= 0),
    hypothesis_id        uuid REFERENCES hypotheses(id) ON DELETE SET NULL,
    hypothesis_relevance numeric(5,4)
                         CHECK (hypothesis_relevance IS NULL OR (hypothesis_relevance >= 0 AND hypothesis_relevance <= 1)),
    evidence_metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at           timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE interview_brain (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id         uuid NOT NULL UNIQUE REFERENCES interview_sessions(id) ON DELETE CASCADE,
    version            integer NOT NULL DEFAULT 1 CHECK (version >= 1),
    current_hypotheses jsonb NOT NULL DEFAULT '[]'::jsonb,
    evidence_summary   jsonb NOT NULL DEFAULT '{}'::jsonb,
    competency_scores  jsonb NOT NULL DEFAULT '{}'::jsonb,
    difficulty_profile jsonb,
    decision_state     jsonb,
    brain_metadata     jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE interview_timeline (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      uuid NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    event_type      text NOT NULL,
    question_number integer CHECK (question_number IS NULL OR question_number >= 0),
    event_data      jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE interview_intelligence (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id            uuid NOT NULL UNIQUE REFERENCES interview_sessions(id) ON DELETE CASCADE,
    company_context       jsonb NOT NULL DEFAULT '{}'::jsonb,
    candidate_context     jsonb NOT NULL DEFAULT '{}'::jsonb,
    blueprint             jsonb NOT NULL DEFAULT '{}'::jsonb,
    scorecard             jsonb NOT NULL DEFAULT '{}'::jsonb,
    evidence_requirements jsonb NOT NULL DEFAULT '[]'::jsonb,
    objectives            jsonb NOT NULL DEFAULT '[]'::jsonb,
    consistency_checks    jsonb NOT NULL DEFAULT '[]'::jsonb,
    observations          jsonb NOT NULL DEFAULT '[]'::jsonb,
    evidence_graph        jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE scorecard_results (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id     uuid NOT NULL UNIQUE REFERENCES interview_sessions(id) ON DELETE CASCADE,
    template_id    uuid REFERENCES scorecard_templates(id) ON DELETE SET NULL,
    scores         jsonb NOT NULL DEFAULT '{}'::jsonb,
    weighted_score numeric(5,2),
    created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_hypotheses_session_status ON hypotheses (session_id, status);
CREATE INDEX idx_hypotheses_competency ON hypotheses (competency_id);
CREATE INDEX idx_evidence_session ON evidence_store (session_id);
CREATE INDEX idx_evidence_session_competency ON evidence_store (session_id, competency_id);
CREATE INDEX idx_evidence_session_dimension ON evidence_store (session_id, dimension);
CREATE INDEX idx_evidence_hypothesis ON evidence_store (hypothesis_id);
CREATE INDEX idx_interview_brain_session ON interview_brain (session_id);
CREATE INDEX idx_timeline_session_type ON interview_timeline (session_id, event_type);
CREATE INDEX idx_timeline_session_created ON interview_timeline (session_id, created_at);
CREATE INDEX idx_interview_intelligence_session ON interview_intelligence (session_id);
CREATE INDEX idx_scorecard_results_session ON scorecard_results (session_id);
CREATE INDEX idx_scorecard_results_template ON scorecard_results (template_id);

ALTER TABLE candidate_documents
    ADD CONSTRAINT fk_candidate_documents_session
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE SET NULL;

-- ============================================================================
-- 7. Applications, links, engine durability, audit
-- ============================================================================

CREATE TABLE public_interview_submissions (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id           uuid NOT NULL REFERENCES public_interviews(id) ON DELETE CASCADE,
    session_id          uuid REFERENCES interview_sessions(id) ON DELETE SET NULL,
    candidate_profile_id uuid REFERENCES candidate_profiles(id) ON DELETE SET NULL,
    resume_document_id  uuid REFERENCES candidate_documents(id) ON DELETE SET NULL,
    candidate_email     text NOT NULL,
    candidate_name      text NOT NULL,
    status              text NOT NULL DEFAULT 'applied'
                        CHECK (status IN (
                            'applied', 'screening', 'evaluated', 'interview_offered',
                            'interview_accepted', 'interview_declined',
                            'interviewed', 'hired', 'rejected', 'withdrawn'
                        )),
    fit_score           numeric(5,2)
                        CHECK (fit_score IS NULL OR (fit_score >= 0 AND fit_score <= 10)),
    fit_summary         text,
    fit_status          text NOT NULL DEFAULT 'pending'
                        CHECK (fit_status IN ('pending', 'running', 'completed', 'failed')),
    fit_breakdown       jsonb,
    fit_evaluated_at    timestamptz,
    fit_error           text,
    org_decision        text NOT NULL DEFAULT 'pending'
                        CHECK (org_decision IN ('pending', 'invited', 'rejected')),
    org_decided_by      uuid REFERENCES users(id) ON DELETE SET NULL,
    org_decided_at      timestamptz,
    candidate_response  text NOT NULL DEFAULT 'pending'
                        CHECK (candidate_response IN ('pending', 'accepted', 'declined')),
    candidate_responded_at timestamptz,
    invited_at          timestamptz,
    outcome             text NOT NULL DEFAULT 'pending'
                        CHECK (outcome IN ('pending', 'hired', 'rejected')),
    outcome_decided_by  uuid REFERENCES users(id) ON DELETE SET NULL,
    outcome_decided_at  timestamptz,
    started_at          timestamptz,
    completed_at        timestamptz,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (public_id, candidate_profile_id)
);

CREATE TABLE interview_events (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id uuid NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    seq        integer NOT NULL CHECK (seq >= 0),
    event_type text NOT NULL,
    payload    jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (session_id, seq)
);

CREATE TABLE v4_session_state (
    session_id    uuid PRIMARY KEY REFERENCES interview_sessions(id) ON DELETE CASCADE,
    state         jsonb NOT NULL,
    state_version integer NOT NULL DEFAULT 1 CHECK (state_version >= 1),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id        uuid REFERENCES organizations(id) ON DELETE SET NULL,
    user_id       uuid REFERENCES users(id) ON DELETE SET NULL,
    action        text NOT NULL,
    resource_type text,
    resource_id   text,
    details       jsonb NOT NULL DEFAULT '{}'::jsonb,
    ip_address    text,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_public_submissions_public ON public_interview_submissions (public_id);
CREATE INDEX idx_public_submissions_session ON public_interview_submissions (session_id);
CREATE INDEX idx_public_submissions_candidate ON public_interview_submissions (candidate_profile_id);
CREATE INDEX idx_public_submissions_status ON public_interview_submissions (status);
CREATE INDEX idx_public_submissions_org_decision ON public_interview_submissions (org_decision);
CREATE INDEX idx_public_submissions_candidate_response ON public_interview_submissions (candidate_response);
CREATE INDEX idx_public_submissions_outcome ON public_interview_submissions (outcome);
CREATE INDEX idx_interview_events_session_seq ON interview_events (session_id, seq);
CREATE INDEX idx_interview_events_type ON interview_events (event_type);
CREATE INDEX idx_interview_events_created ON interview_events (created_at);
CREATE INDEX idx_v4_session_state_updated ON v4_session_state (updated_at);
CREATE INDEX idx_audit_org ON audit_log (org_id);
CREATE INDEX idx_audit_user ON audit_log (user_id);
CREATE INDEX idx_audit_action ON audit_log (action);
CREATE INDEX idx_audit_created ON audit_log (created_at);

-- ============================================================================
-- 8. Updated_at triggers
-- ============================================================================

CREATE TRIGGER trg_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_it_roles_updated_at
    BEFORE UPDATE ON it_roles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_candidate_profiles_updated_at
    BEFORE UPDATE ON candidate_profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_scorecard_templates_updated_at
    BEFORE UPDATE ON scorecard_templates
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_interview_sessions_updated_at
    BEFORE UPDATE ON interview_sessions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_hypotheses_updated_at
    BEFORE UPDATE ON hypotheses
    FOR EACH ROW EXECUTE FUNCTION set_last_updated();

CREATE TRIGGER trg_interview_brain_updated_at
    BEFORE UPDATE ON interview_brain
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_interview_intelligence_updated_at
    BEFORE UPDATE ON interview_intelligence
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_public_interview_submissions_updated_at
    BEFORE UPDATE ON public_interview_submissions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================================
-- 9. Comments
-- ============================================================================

COMMENT ON TABLE organization_documents IS
    'IT knowledge documents for the organization; no department table.';
COMMENT ON TABLE public_interviews IS
    'Opportunity hub listing. One organization can publish many listings.';
COMMENT ON TABLE public_interview_submissions IS
    'Candidate application, fit score, org decision, and optional interview session.';
COMMENT ON COLUMN interview_sessions.it_role_id IS
    'Required FK to the IT role catalog; this is the scope lock for sessions.';
COMMENT ON COLUMN competencies.scope IS
    'Always IT. Non-IT competencies are not allowed in this schema.';
COMMENT ON TABLE interview_intelligence IS
    'Consolidated JSONB for company, candidate, blueprint, scorecard, evidence requirements, objectives, consistency, observations, and evidence graph.';

-- ============================================================================
-- End of schema
-- ============================================================================
