# 01 — Scope Change: IT Department Only

> Decision: the AI Interview Agent interviews **only for IT (Information Technology) roles
> inside an IT department**. Everything outside the IT field is out of scope, even when the
> platform could technically do it.
>
> Read [`02-glossary.md`](02-glossary.md) first. Every term and abbreviation used here is
> defined there, including CCB (Change Control Board).

## 0. Change record

| Field | Value |
|---|---|
| Change ID | CR-IT-SCOPE-001 |
| Title | Restrict the system scope to the IT department only |
| Status | Proposed, pending CCB (Change Control Board) approval |
| Change type | Scope change and data-model change |
| Reason | The product must interview only for roles inside an IT department; non-IT departments and roles are outside the product boundary |
| Impacted areas | Requirements, database schema, role catalog, competency taxonomy, prompts, API validation, frontend role picker, demo data, documentation |
| Related documents | [`02-glossary.md`](02-glossary.md), [`03-database-schema.md`](03-database-schema.md), [`schema.sql`](schema.sql), [`seed-it-catalog.sql`](seed-it-catalog.sql) |
| Approval | CCB must approve before implementation starts |

## 1. Recommended approach: scope-lock, don't fork

Do **not** build a second product and do **not** delete non-IT code on day one.

Use a **scope lock** with one authoritative policy: `SYSTEM_SCOPE = IT`.

The policy is enforced at six layers, so the scope cannot drift back to “any department”:

| Layer | Enforcement |
|---|---|
| Requirements | This folder is the source of truth. A feature must name the IT role or IT function it serves. |
| Database | `organization_documents.org_id` scopes IT knowledge to the organization; `public_interviews.org_id` allows many interviews per organization; `interview_sessions.it_role_id` is a required foreign key. |
| Catalog | `it_roles`, `competencies`, and `role_competencies` contain IT-only entries; families and levels are checked values on `it_roles`. |
| Service/API | Reject requests without a valid `it_role_id`; reject non-IT roles; there is no department API. |
| Prompt/taxonomy | The competency resolver filters `competencies.scope = 'IT'`; non-IT prompt branches are removed from the active path. |
| Frontend/demo data | Organization-level IT documents and the IT role picker replace department creation; demo documents and sample candidates are IT-only. |

Why this is the best option:

- **Least destructive.** Existing sessions, evidence, and audit history stay readable.
- **One rule, many guardrails.** The scope is not a comment in a document; it is a database
  constraint plus a service check plus a catalog.
- **Reversible during migration.** Keep the old non-IT code behind a feature flag until the
  IT-only data migration passes acceptance, then remove it.
- **ERD-friendly.** The new catalog and foreign keys give a clean, drawable schema.

## 2. In scope

### 2.1 IT field and organization-level documents

- One organization has one IT knowledge base; documents belong to the organization, not a department.
- One organization can publish **many interviews** through `public_interviews`; no department table is needed.
- No Engineering, Marketing, Finance, HR, Sales, Operations, or other business departments.
- An optional free-text team label (for example `Platform`, `Security`, `Data`) is metadata only,
  not a separate table and not a scope escape hatch.
- IT-adjacent functions are allowed only when they serve IT delivery: UI/UX, product ownership,
  business analysis, project/program management, IT service management, IT governance/audit.

### 2.2 IT role catalog

All roles below are selectable from `it_roles`. The exact seed rows are in
[`seed-it-catalog.sql`](seed-it-catalog.sql). New IT roles can be added without code changes.

| Family | Roles included (seed) |
|---|---|
| Software Engineering | Software Engineer, Senior Software Engineer, Software Architect, Technical Lead, Principal Engineer, Engineering Manager, API Developer, Integration Engineer, SDK Developer, Systems Software Engineer |
| Frontend | Frontend Developer, Senior Frontend Developer, UI Engineer, React Developer, Angular Developer, Vue Developer, Web Developer, Accessibility Engineer |
| Backend | Backend Developer, Senior Backend Developer, Java Developer, Python Developer, Node.js Developer, .NET Developer, Go Developer, PHP Developer, API Backend Engineer, Microservices Engineer, Blockchain Developer |
| Full Stack | Full Stack Developer, Senior Full Stack Developer, Web Application Developer |
| Mobile | Mobile Developer, iOS Developer, Android Developer, React Native Developer, Flutter Developer, Mobile Lead |
| Game Development | Game Developer, Unity Developer, Unreal Engine Developer, Graphics Programmer, Gameplay Programmer, XR Developer |
| Embedded & IoT | Embedded Software Engineer, Firmware Engineer, IoT Engineer, Robotics Software Engineer |
| QA & Testing | QA Engineer, QA Automation Engineer, SDET, Test Analyst, Performance Test Engineer, Security Test Engineer, QA Manager, QA Lead, Test Manager, Manual Tester |
| DevOps & Release | DevOps Engineer, Site Reliability Engineer, Platform Engineer, Release Manager, Build Engineer, Automation Engineer, DevSecOps Engineer |
| Cloud | Cloud Engineer, AWS Engineer, Azure Engineer, GCP Engineer, Cloud Architect, Cloud Security Engineer, Cloud Operations Engineer, Cloud Solutions Architect |
| Infrastructure & Systems | Infrastructure Engineer, Systems Engineer, Systems Administrator, Linux Administrator, Windows Administrator, Virtualization Engineer, Storage Engineer, Data Center Engineer, End-User Computing Engineer |
| Network | Network Engineer, Network Administrator, Network Architect, Network Security Engineer, NOC Engineer, Telecom Engineer |
| Cybersecurity | Cybersecurity Analyst, Security Engineer, Application Security Engineer, Penetration Tester, SOC Analyst, Incident Responder, GRC Analyst, IAM Engineer, Security Architect, Security Manager, Forensics Analyst, Threat Intelligence Analyst |
| Data & Analytics | Data Analyst, Data Engineer, Data Scientist, Business Intelligence Analyst, Analytics Engineer, Data Architect, Database Developer, ETL Developer, Big Data Engineer, Data Governance Analyst, Data Platform Engineer |
| AI & Machine Learning | Machine Learning Engineer, AI Engineer, MLOps Engineer, NLP Engineer, Computer Vision Engineer, Deep Learning Engineer, AI Research Engineer, AI Solutions Architect, LLM Engineer, Prompt Engineer |
| Database | Database Administrator, Database Engineer, Database Architect, Database Optimization Specialist, Data Warehouse Engineer, Database Reliability Engineer |
| IT Support & Service Management | IT Support Specialist, Helpdesk Technician, Service Desk Analyst, Desktop Support Engineer, Application Support Analyst, IT Operations Analyst, IT Asset Manager, IT Service Manager, Incident Manager, Problem Manager, Change Manager, Configuration Manager, Service Delivery Manager |
| Architecture | Enterprise Architect, Solutions Architect, Technical Architect, Integration Architect, IT Architect, Systems Architect |
| IT Management & Governance | IT Manager, IT Director, IT Project Manager, IT Program Manager, IT Governance Manager, IT Risk Manager, IT Compliance Manager, IT Auditor, IT Consultant, IT Trainer, IT Procurement Specialist, Technical Program Manager |
| IT Business Analysis | IT Business Analyst, Systems Analyst, Functional Analyst, IT Product Owner, IT Scrum Master, Requirements Engineer |
| UI/UX Design | UI Designer, UX Designer, Product Designer, Interaction Designer, UX Researcher |
| ERP/CRM & Enterprise Apps | ERP Administrator, CRM Administrator, Salesforce Developer, SAP Consultant, Workday Consultant, ServiceNow Developer, Dynamics 365 Developer, Oracle ERP Consultant |
| Technical Writing | Technical Writer, Documentation Engineer |

The 23 family names and 8 levels are `CHECK` values on `it_roles`; the lean schema does not need
separate family or level tables.

> The catalog is intentionally broad. “All IT roles available” means **any role in this catalog can
> be selected**, and the catalog can be extended by adding a row, not by changing the schema.

### 2.3 Functional scope

- Organization and user accounts, one owner user per organization, password reset, and audit log.
- The organization-level IT knowledge documents (RAG).
- IT role selection from the catalog, with level (intern → director).
- Interview templates, scorecard templates, invite-link sessions, and practice sessions - **for IT roles only**.
- The interview engine: questions, evaluations, evidence, hypotheses, brain snapshots, and timeline.
- Reports and analytics scoped to IT roles and IT sessions.

## 3. Out of scope

| Removed / disabled | Reason |
|---|---|
| Non-IT roles and competency families | The system is IT-only. |
| Free-text job roles | They allow non-IT values and break the catalog guarantee. |
| Commerce, marketing, HR, finance, supply-chain, and general customer-success competencies | Outside the IT field. |
| Non-IT demo data (for example the PetroCore Energy oil-and-gas knowledge base) | Misleading demo scope. |
| Public marketplace and scheduling | Deferred from the lean IT scope; add only with a separate approved requirement. |
| Non-IT prompt branches in the active prompt path | Prompts must not ask non-IT questions. |

Kept as IT-adjacent (allowed):

- UI/UX and product design.
- IT product ownership, business analysis, and requirements engineering.
- IT project/program management and IT service management.
- IT governance, risk, compliance, and audit.
- Data, AI/ML, security, cloud, network, infrastructure, QA, DevOps, support, and architecture.

## 4. Impact map

| Area | Change |
|---|---|
| `app/data/competency_taxonomy.py` | Keep IT, design, IT-product, and IT-operations competencies; remove commerce, marketing, HR, finance, supply chain, and non-IT customer success. Add `scope='IT'`. |
| `app/data/competency_resolver.py` | Resolve only from IT competencies; unknown role → reject, not fall back to a generic non-IT taxonomy. |
| `app/intelligence/role_competency_profiler.py` | Restrict job families to IT families; validate the chosen role against `it_roles`. |
| `app/api/v1/departments.py` | Remove; knowledge documents become organization-level. |
| `app/auth/service.py` | Do not create a department on organization registration. |
| `app/models/db.py` | Add catalog FKs (`it_role_id`, `level_code`), `invite_token`, and organization-level document relations. |
| `prompts/` | Remove or archive non-IT role branches; all prompts assume an IT role and IT context. |
| `frontend/` | Remove department creation; use organization documents and the IT role picker; hide non-IT taxonomies. |
| `documents/` + `resumes/` | Replace non-IT demo documents with IT-only samples. |
| `docs/` | This folder is authoritative; old docs move to `docs/archive/`. |

## 5. Migration sequence (recommended)

1. **Freeze requirements** in this folder and approve the ERD.
2. **Create the IT catalog** and seed all IT roles and competencies.
3. **Add the IT scope columns**: `it_role_id`, `level_code`, and `invite_token`; move documents to `organization_documents`; keep `public_interviews.org_id` for many interviews per organization.
4. **Backfill existing rows**:
   - Map existing `job_role` text to the nearest `it_roles.slug`.
   - Rows that cannot be mapped are marked `legacy_unmapped` and are read-only; they are not
     deleted and do not accept new interviews.
   - Move existing department documents to the organization-level documents table.
   - Do not keep a department table; multiple interviews are separate `public_interviews` rows.
5. **Enable service guards** behind `SYSTEM_SCOPE=IT`; run shadow validation before enforcing.
6. **Replace demo data** with IT-only documents, resumes, and templates.
7. **Remove non-IT prompt/code branches** after one clean release.
8. **Archive old docs** and update links.

## 6. Acceptance criteria

- [ ] An organization can publish many interviews; knowledge documents are organization-scoped.
- [ ] `interview_sessions.it_role_id` is required and references an active `it_roles` row.
- [ ] No API accepts a free-text `job_role` as the source of truth.
- [ ] Every active competency has `scope = 'IT'`.
- [ ] No selectable role belongs to a non-IT family.
- [ ] The role picker returns the full IT catalog, including all families in §2.2.
- [ ] A non-IT role or competency cannot be created through the API or seeded by mistake.
- [ ] Legacy sessions remain readable; unmapped legacy roles are visibly flagged.
- [ ] Every acronym in this folder is defined in [`02-glossary.md`](02-glossary.md).

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| “IT” is interpreted too narrowly and excludes UI/UX, product, or IT service management | The explicit in-scope list in §2.1 and §2.2 is the authority. |
| Existing non-IT sessions become unreadable | Keep legacy rows; flag unmapped roles instead of deleting. |
| Role catalog becomes a bottleneck | Adding a role is a data insert, not a schema change; `is_active` retires roles without deleting history. |
| Scope creeps back through free-text roles | Database FK + service validation + UI picker; no free-text path. |
| Archived docs are mistaken for current requirements | `docs/archive/README.md` and a banner on every archived doc state “reference only”. |
