# 02 — Glossary and Abbreviations

> Rule: **define the meaning before using the short form**.
> If a term appears in a requirement, table, API, or diagram, it belongs here.
> Every acronym is expanded on first use in each document.

## How to read an entry

**Term (full form)** — plain-language meaning. *Where it appears / why it matters.*

## A

**ABAC (Attribute-Based Access Control)** — access control that decides from attributes such as
department, role, clearance, or resource label. *Used when role-based access is not granular enough.*

**AI (Artificial Intelligence)** — software that performs tasks associated with human intelligence,
such as reasoning, language understanding, or decision support. *The interview engine uses AI to
generate questions and evaluate answers.*

**Alembic** — a database migration tool for SQLAlchemy. *It applies versioned schema changes to
PostgreSQL.*

**API (Application Programming Interface)** — a defined contract that lets one program call another.
*The frontend calls the backend through REST and WebSocket APIs.*

**ATS (Applicant Tracking System)** — software used by recruiters to manage job applications and
hiring pipelines. *An ATS may receive interview results through an integration.*

**Audit log** — an append-only record of who did what, when, and to which resource. *Used for
security, compliance, and traceability.*

## B

**Backfill** — filling a new column or table with values derived from existing data. *Used when
mapping existing job roles to the IT role catalog.*

**Brain (company / candidate / interview)** — a persisted snapshot of reasoning context:
company/department knowledge, candidate profile, or the live interview reasoning state.
*Brains let the engine keep context across turns and recover after a restart.*

**Bucket / namespace (vector store)** — a logical partition inside a vector database. *Each
department document set uses a Pinecone namespace.*

## C

**Catalog (reference table)** — a controlled list of allowed values, such as IT roles, levels,
and competencies. *The catalog is how the system guarantees IT-only scope.*

**Cascade (ON DELETE CASCADE)** — a database rule that automatically deletes child rows when the
parent row is deleted. *Used for messages, evaluations, and other session-owned rows.*

**CCB (Change Control Board)** — the group of people who review, approve, reject, or defer
requirement and scope changes. *In this project, the CCB approves changes such as the decision to
restrict the system to the IT department only.*

**CD (Continuous Delivery / Continuous Deployment)** — a practice where every validated change can
be released automatically. *Part of the IT delivery context, not a database table.*

**CI (Continuous Integration)** — automatically building and testing every code change. *Runs
type checks, linting, and tests before merge.*

**Competency** — a measurable capability expected for a role, such as “System Design &
Architecture”. *Scores, evidence, and questions are tied to competencies.*

**Constraint (database)** — a rule the database enforces, such as `CHECK`, `UNIQUE`, or `FOREIGN KEY`.
*Constraints stop invalid IT-scope data even if application code has a bug.*

**Covering index** — an index that contains all columns needed by a query so the table is not read.
*Used for read-heavy listings and rankings.*

**CRUD (Create, Read, Update, Delete)** — the four basic data operations. *Most admin screens are
CRUD screens.*

**CSV (Comma-Separated Values)** — a plain-text table format. *Used for exports.*

**CTE (Common Table Expression)** — a named temporary query result inside a SQL statement.
*Used for readable analytics queries.*

## D

**DB (Database)** — the organized store of persistent data. *PostgreSQL in this project.*

**DBA (Database Administrator)** — the IT role responsible for database availability, backup,
performance, and access. *Also an IT role in the catalog.*

**DDL (Data Definition Language)** — SQL statements that define or change schema, such as
`CREATE TABLE` and `ALTER TABLE`. *`schema.sql` is DDL.*

**DevOps** — the practice of combining software development and IT operations to deliver changes
quickly and safely. *A role family in the IT catalog.*

**DML (Data Manipulation Language)** — SQL statements that read or change rows, such as `SELECT`,
`INSERT`, `UPDATE`, and `DELETE`. *Seed files use DML.*

**DTO (Data Transfer Object)** — an object shaped for moving data between layers or services.
*Usually a Pydantic schema in the backend.*

## E

**Embedding** — a numeric vector that represents text meaning. *Used by the RAG pipeline to find
relevant department documents.*

**Enum (enumeration)** — a fixed set of allowed values. *Implemented here as text plus a `CHECK`
constraint for easier migration.*

**ERD (Entity–Relationship Diagram)** — a diagram of entities, attributes, and relationships.
*The user will draw the ERD from `03-database-schema.md` and `schema.sql`.*

**ETL (Extract, Transform, Load)** — moving and reshaping data from sources into a target store.
*An IT data role and a data-engineering competency.*

## F

**Feature flag** — a switch that enables or disables a code path without redeploying. *Used to keep
the old non-IT path dormant during migration.*

**FK (Foreign Key)** — a column that references the primary key of another table. *`it_role_id` is
the foreign key that locks a session to the IT catalog.*

**FR (Functional Requirement)** — a requirement describing what the system must do. *Example:
“the recruiter must select an IT role from the catalog.”*

## G

**GDPR (General Data Protection Regulation)** — the European Union data-protection law. *Affects
candidate data retention and deletion.*

**GRC (Governance, Risk, and Compliance)** — the IT function that manages policy, risk, and
regulatory obligations. *A role family and competency area.*

## H

**HMAC (Hash-based Message Authentication Code)** — a keyed hash used to verify that a message was
not changed and came from a trusted sender. *Used for webhook signatures.*

## I

**IAM (Identity and Access Management)** — the IT function that manages users, identities, roles,
and permissions. *A cybersecurity role and competency.*

**Idempotent** — safe to run more than once with the same result. *Seed files use
`ON CONFLICT DO NOTHING` so re-running is safe.*

**Index (database)** — a structure that speeds up reads at the cost of extra writes and storage.
*Every foreign key and common filter gets an index.*

**IT (Information Technology)** — the department and field responsible for computing systems,
software, networks, infrastructure, data, security, and user support. *This is the only allowed
system scope.*

**ITIL (Information Technology Infrastructure Library)** — a widely used framework for IT service
management. *Informs incident, problem, change, and configuration management roles.*

## J

**JSON (JavaScript Object Notation)** — a text format for structured data. *Used in API payloads.*

**JSONB (Binary JSON)** — PostgreSQL’s binary JSON type, indexable and efficient. *Used for
snapshots, evidence metadata, and flexible bundles.*

**JWT (JSON Web Token)** — a signed token that carries claims such as user ID and role. *Used for
organization and candidate authentication.*

## K

**KPI (Key Performance Indicator)** — a measurable target used to judge success. *Used in
analytics and IT operations.*

## L

**LLM (Large Language Model)** — an AI model that generates and understands text. *Generates
questions and evaluates answers.*

**Lookup table** — a small reference table of allowed values. *In the lean schema, levels and families are `CHECK` values on `it_roles`, not separate lookup tables.*

## M

**MFA (Multi-Factor Authentication)** — authentication using two or more independent factors.
*Recommended for recruiter accounts.*

**ML (Machine Learning)** — a branch of AI where models learn patterns from data. *A role family
and competency area.*

**MLOps** — the practice of deploying, monitoring, and maintaining machine-learning models in
production. *An IT role.*

**MVP (Minimum Viable Product)** — the smallest release that delivers real value and can be tested.
*The IT-only scope is the MVP boundary.*

## N

**NFR (Non-Functional Requirement)** — a quality constraint such as performance, security,
availability, or usability. *Example: p95 question latency under two seconds.*

**NLP (Natural Language Processing)** — AI that processes human language. *Used in resume analysis
and answer evaluation.*

**Normalization** — organizing tables to reduce duplication and inconsistency. *The catalog tables
are normalized; snapshots are intentionally denormalized JSONB.*

## O

**ORM (Object–Relational Mapper)** — code that maps database tables to program objects.
*SQLAlchemy is the ORM here.*

**OWASP (Open Worldwide Application Security Project)** — a community that publishes application
security guidance, including the Top 10. *Used for security requirements.*

## P

**PII (Personally Identifiable Information)** — data that can identify a person, such as name,
email, phone, or resume. *Candidate data is PII and must be protected and retained carefully.*

**PK (Primary Key)** — the column or columns that uniquely identify a row. *Usually a UUID here.*

**PostgreSQL** — the open-source relational database used by the system. *All DDL in `schema.sql`
targets PostgreSQL 15+.*

**Prompt** — the instruction text sent to an LLM. *Prompts are versioned files under `prompts/`.*

**P95 (95th percentile)** — the value below which 95% of observations fall. *Used to state latency
requirements without hiding slow tails.*

## Q

**QA (Quality Assurance)** — the IT function that prevents defects through process and testing.
*A role family.*

## R

**RAG (Retrieval-Augmented Generation)** — an AI pattern that retrieves relevant documents first,
then gives them to an LLM to generate a grounded answer. *Used for department knowledge.*

**RBAC (Role-Based Access Control)** — access control based on assigned roles. *Organization roles
are owner, member, and viewer.*

**REST (Representational State Transfer)** — a style of HTTP API using resources and standard verbs.
*The backend exposes REST endpoints under `/api/v1/`.*

**RFP (Request for Proposal)** — a document that asks vendors to propose a solution. *An input
document, not a system entity.*

**Role (IT role)** — a job title from the IT catalog, such as “Backend Developer” or “SOC Analyst”.
*Not the same as an access role such as owner/member/viewer.*

**Row-Level Security (RLS)** — database enforcement that limits which rows a user can see.
*Optional hardening for multi-tenant data.*

## S

**Schema (database)** — the definition of tables, columns, keys, indexes, and constraints.
*This folder defines the target schema.*

**Scope lock** — the deliberate enforcement of one system scope across requirements, database,
services, and UI. *The chosen approach is `SYSTEM_SCOPE = IT`.*

**SDET (Software Development Engineer in Test)** — an engineer who builds test automation and
quality tooling. *An IT role.*

**Seed data** — initial reference or demo rows inserted into a database. *`seed-it-catalog.sql`
seeds the IT catalog.*

**SLA (Service Level Agreement)** — a committed service target, such as uptime or response time.
*Relevant to IT service management roles.*

**Snapshot** — a point-in-time copy of computed state stored for replay, audit, or display.
*Brain and bundle tables keep snapshots.*

**SOC (Security Operations Center)** — the team that monitors and responds to security incidents.
*A cybersecurity role family.*

**SRS (Software Requirements Specification)** — the document that states what the system must do
and the constraints it must satisfy. *This folder is the IT-only requirements source.*

**SSO (Single Sign-On)** — one login used across multiple applications. *An integration option for
organization users.*

**SRE (Site Reliability Engineer)** — an engineer who applies software engineering to operations,
reliability, and incident response. *An IT role.*

## T

**Tenant** — one isolated customer organization in a shared system. *Each organization is a tenant.*

**Text + CHECK enum** — using a text column plus a `CHECK` constraint instead of a PostgreSQL enum
type. *Chosen for easier, safer migrations.*

**Timestamptz (timestamp with time zone)** — PostgreSQL’s timezone-aware timestamp type. *All
timestamps use it.*

**TLS (Transport Layer Security)** — encryption for data in transit. *Required for all APIs.*

## U

**UAT (User Acceptance Testing)** — testing by the intended users against acceptance criteria.
*The IT-only acceptance checklist is in `01-scope-change.md`.*

**UI (User Interface)** — the visual and interactive part of the product. *Frontend screens.*

**UUID (Universally Unique Identifier)** — a 128-bit identifier that is effectively unique without
a central counter. *Most primary keys use UUIDs generated by `gen_random_uuid()`.*

**UX (User Experience)** — the overall experience of using the product. *An IT-adjacent design role.*

## V

**VAPT (Vulnerability Assessment and Penetration Testing)** — finding and exploiting weaknesses to
prove risk. *A cybersecurity role family.*

**Vector store** — a database optimized for similarity search over embeddings. *Pinecone is used
for department knowledge.*

## W

**WebSocket** — a persistent two-way connection between browser and server. *Used for live interview
turns and avatar speech events.*

**Workflow** — an orchestrated sequence of steps. *The interview engine runs question and evaluation
workflows.*

## X

**XSS (Cross-Site Scripting)** — injecting executable script into a page viewed by another user.
*A security requirement for rendered transcripts and documents.*

## Y

**YAML (YAML Ain’t Markup Language)** — a human-readable configuration format. *Used in deployment
and CI configuration.*

## Z

**Zero-downtime deploy** — releasing a new version without taking the service offline. *A
non-functional requirement for production.*
