-- ============================================================================
-- AI Interview Agent — IT Catalog Seed
-- PostgreSQL 15+
--
-- Run after docs/it-scope/schema.sql.
-- Idempotent: every insert uses ON CONFLICT DO NOTHING.
--
-- Scope rule: this file seeds ONLY IT roles and IT-relevant competencies.
-- Adding an IT role later is a data insert, not a schema change.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Roles (all IT roles available; family and level are checked values)
-- ----------------------------------------------------------------------------

INSERT INTO it_roles (slug, family, name, description, level_min, level_max) VALUES
    -- Software Engineering
    ('software-engineer', 'software_engineering', 'Software Engineer', 'Builds and maintains software systems', 'junior', 'senior'),
    ('senior-software-engineer', 'software_engineering', 'Senior Software Engineer', 'Owns complex software delivery and mentors engineers', 'senior', 'principal'),
    ('software-architect', 'software_engineering', 'Software Architect', 'Defines software structure, standards, and trade-offs', 'senior', 'principal'),
    ('technical-lead', 'software_engineering', 'Technical Lead', 'Leads technical direction and delivery for a team', 'senior', 'lead'),
    ('principal-engineer', 'software_engineering', 'Principal Engineer', 'Sets engineering direction across multiple teams', 'principal', 'principal'),
    ('engineering-manager', 'software_engineering', 'Engineering Manager', 'Manages engineers, delivery, and team health', 'manager', 'director'),
    ('api-developer', 'software_engineering', 'API Developer', 'Designs and builds APIs and integration contracts', 'junior', 'senior'),
    ('integration-engineer', 'software_engineering', 'Integration Engineer', 'Connects systems, data, and third-party services', 'junior', 'senior'),
    ('sdk-developer', 'software_engineering', 'SDK Developer', 'Builds client libraries and developer-facing SDKs', 'mid', 'senior'),
    ('systems-software-engineer', 'software_engineering', 'Systems Software Engineer', 'Builds low-level system software and tooling', 'mid', 'senior'),

    -- Frontend
    ('frontend-developer', 'frontend', 'Frontend Developer', 'Builds browser-based user interfaces', 'junior', 'senior'),
    ('senior-frontend-developer', 'frontend', 'Senior Frontend Developer', 'Owns complex frontend architecture and delivery', 'senior', 'principal'),
    ('ui-engineer', 'frontend', 'UI Engineer', 'Implements accessible, high-quality UI components', 'junior', 'senior'),
    ('react-developer', 'frontend', 'React Developer', 'Builds React applications and component systems', 'junior', 'senior'),
    ('angular-developer', 'frontend', 'Angular Developer', 'Builds Angular applications and enterprise UI', 'junior', 'senior'),
    ('vue-developer', 'frontend', 'Vue Developer', 'Builds Vue applications and components', 'junior', 'senior'),
    ('web-developer', 'frontend', 'Web Developer', 'Builds and maintains websites and web apps', 'intern', 'senior'),
    ('accessibility-engineer', 'frontend', 'Accessibility Engineer', 'Ensures WCAG-compliant and inclusive interfaces', 'mid', 'senior'),

    -- Backend
    ('backend-developer', 'backend', 'Backend Developer', 'Builds server-side services and business logic', 'junior', 'senior'),
    ('senior-backend-developer', 'backend', 'Senior Backend Developer', 'Owns complex backend systems and reliability', 'senior', 'principal'),
    ('java-developer', 'backend', 'Java Developer', 'Builds Java services and applications', 'junior', 'senior'),
    ('python-developer', 'backend', 'Python Developer', 'Builds Python services, tools, and APIs', 'junior', 'senior'),
    ('nodejs-developer', 'backend', 'Node.js Developer', 'Builds Node.js services and APIs', 'junior', 'senior'),
    ('dotnet-developer', 'backend', '.NET Developer', 'Builds .NET services and applications', 'junior', 'senior'),
    ('go-developer', 'backend', 'Go Developer', 'Builds Go services and infrastructure tooling', 'mid', 'senior'),
    ('php-developer', 'backend', 'PHP Developer', 'Builds PHP applications and APIs', 'junior', 'senior'),
    ('api-backend-engineer', 'backend', 'API Backend Engineer', 'Owns backend API design and performance', 'mid', 'senior'),
    ('microservices-engineer', 'backend', 'Microservices Engineer', 'Designs and operates microservice systems', 'mid', 'senior'),
    ('blockchain-developer', 'backend', 'Blockchain Developer', 'Builds distributed-ledger applications and contracts', 'mid', 'senior'),

    -- Full Stack
    ('fullstack-developer', 'fullstack', 'Full Stack Developer', 'Builds both frontend and backend features', 'junior', 'senior'),
    ('senior-fullstack-developer', 'fullstack', 'Senior Full Stack Developer', 'Owns end-to-end application delivery', 'senior', 'principal'),
    ('web-application-developer', 'fullstack', 'Web Application Developer', 'Builds complete web applications', 'junior', 'senior'),

    -- Mobile
    ('mobile-developer', 'mobile', 'Mobile Developer', 'Builds mobile applications', 'junior', 'senior'),
    ('ios-developer', 'mobile', 'iOS Developer', 'Builds iOS applications', 'junior', 'senior'),
    ('android-developer', 'mobile', 'Android Developer', 'Builds Android applications', 'junior', 'senior'),
    ('react-native-developer', 'mobile', 'React Native Developer', 'Builds cross-platform apps with React Native', 'junior', 'senior'),
    ('flutter-developer', 'mobile', 'Flutter Developer', 'Builds cross-platform apps with Flutter', 'junior', 'senior'),
    ('mobile-lead', 'mobile', 'Mobile Lead', 'Leads mobile engineering and release strategy', 'lead', 'manager'),

    -- Game Development
    ('game-developer', 'game', 'Game Developer', 'Builds gameplay systems and game features', 'junior', 'senior'),
    ('unity-developer', 'game', 'Unity Developer', 'Builds games and simulations in Unity', 'junior', 'senior'),
    ('unreal-engine-developer', 'game', 'Unreal Engine Developer', 'Builds games and simulations in Unreal', 'mid', 'senior'),
    ('graphics-programmer', 'game', 'Graphics Programmer', 'Builds rendering and visual systems', 'mid', 'senior'),
    ('gameplay-programmer', 'game', 'Gameplay Programmer', 'Builds gameplay mechanics and controls', 'mid', 'senior'),
    ('xr-developer', 'game', 'XR Developer', 'Builds AR/VR/XR applications and experiences', 'mid', 'senior'),

    -- Embedded & IoT
    ('embedded-software-engineer', 'embedded', 'Embedded Software Engineer', 'Builds embedded software for devices', 'mid', 'senior'),
    ('firmware-engineer', 'embedded', 'Firmware Engineer', 'Develops firmware and hardware interfaces', 'mid', 'senior'),
    ('iot-engineer', 'embedded', 'IoT Engineer', 'Connects devices, sensors, and cloud services', 'mid', 'senior'),
    ('robotics-software-engineer', 'embedded', 'Robotics Software Engineer', 'Builds software for robotic systems', 'mid', 'senior'),

    -- QA & Testing
    ('qa-engineer', 'qa', 'QA Engineer', 'Plans and executes quality assurance activities', 'junior', 'senior'),
    ('qa-automation-engineer', 'qa', 'QA Automation Engineer', 'Builds automated test suites', 'junior', 'senior'),
    ('sdet', 'qa', 'SDET', 'Builds test automation and quality tooling as an engineer', 'mid', 'senior'),
    ('test-analyst', 'qa', 'Test Analyst', 'Analyzes requirements and designs test coverage', 'junior', 'senior'),
    ('performance-test-engineer', 'qa', 'Performance Test Engineer', 'Tests throughput, latency, and scalability', 'mid', 'senior'),
    ('security-test-engineer', 'qa', 'Security Test Engineer', 'Tests applications for security weaknesses', 'mid', 'senior'),
    ('qa-lead', 'qa', 'QA Lead', 'Leads quality strategy and QA teams', 'lead', 'manager'),
    ('test-manager', 'qa', 'Test Manager', 'Manages test programs and quality governance', 'manager', 'director'),
    ('qa-manager', 'qa', 'QA Manager', 'Manages QA teams and quality governance', 'manager', 'director'),
    ('manual-tester', 'qa', 'Manual Tester', 'Executes manual test cases and reports defects', 'intern', 'mid'),

    -- DevOps & Release
    ('devops-engineer', 'devops', 'DevOps Engineer', 'Automates build, deploy, and operations', 'mid', 'senior'),
    ('site-reliability-engineer', 'devops', 'Site Reliability Engineer', 'Owns reliability, observability, and incident response', 'mid', 'senior'),
    ('platform-engineer', 'devops', 'Platform Engineer', 'Builds internal developer and delivery platforms', 'mid', 'senior'),
    ('release-manager', 'devops', 'Release Manager', 'Coordinates release planning and change control', 'mid', 'manager'),
    ('build-engineer', 'devops', 'Build Engineer', 'Owns build systems and artifact pipelines', 'mid', 'senior'),
    ('automation-engineer', 'devops', 'Automation Engineer', 'Automates infrastructure and repetitive operations', 'mid', 'senior'),
    ('devsecops-engineer', 'devops', 'DevSecOps Engineer', 'Embeds security into delivery pipelines', 'mid', 'senior'),

    -- Cloud
    ('cloud-engineer', 'cloud', 'Cloud Engineer', 'Builds and operates cloud infrastructure', 'mid', 'senior'),
    ('aws-engineer', 'cloud', 'AWS Engineer', 'Designs and operates AWS workloads', 'mid', 'senior'),
    ('azure-engineer', 'cloud', 'Azure Engineer', 'Designs and operates Azure workloads', 'mid', 'senior'),
    ('gcp-engineer', 'cloud', 'GCP Engineer', 'Designs and operates Google Cloud workloads', 'mid', 'senior'),
    ('cloud-architect', 'cloud', 'Cloud Architect', 'Defines cloud architecture and standards', 'senior', 'principal'),
    ('cloud-security-engineer', 'cloud', 'Cloud Security Engineer', 'Secures cloud identity, network, and data', 'mid', 'senior'),
    ('cloud-operations-engineer', 'cloud', 'Cloud Operations Engineer', 'Runs cloud operations, cost, and reliability', 'junior', 'senior'),
    ('cloud-solutions-architect', 'cloud', 'Cloud Solutions Architect', 'Designs cloud solutions for business needs', 'senior', 'principal'),

    -- Infrastructure & Systems
    ('infrastructure-engineer', 'infrastructure', 'Infrastructure Engineer', 'Builds and maintains IT infrastructure', 'mid', 'senior'),
    ('systems-engineer', 'infrastructure', 'Systems Engineer', 'Designs and operates system platforms', 'mid', 'senior'),
    ('systems-administrator', 'infrastructure', 'Systems Administrator', 'Administers servers and system services', 'junior', 'senior'),
    ('linux-administrator', 'infrastructure', 'Linux Administrator', 'Administers Linux systems', 'junior', 'senior'),
    ('windows-administrator', 'infrastructure', 'Windows Administrator', 'Administers Windows systems', 'junior', 'senior'),
    ('virtualization-engineer', 'infrastructure', 'Virtualization Engineer', 'Runs hypervisors, containers, and virtual platforms', 'mid', 'senior'),
    ('storage-engineer', 'infrastructure', 'Storage Engineer', 'Designs and operates storage systems', 'mid', 'senior'),
    ('data-center-engineer', 'infrastructure', 'Data Center Engineer', 'Operates data center facilities and hardware', 'junior', 'senior'),
    ('end-user-computing-engineer', 'infrastructure', 'End-User Computing Engineer', 'Manages desktops, devices, and endpoint platforms', 'junior', 'senior'),

    -- Network
    ('network-engineer', 'network', 'Network Engineer', 'Designs and operates networks', 'junior', 'senior'),
    ('network-administrator', 'network', 'Network Administrator', 'Administers routers, switches, and firewalls', 'junior', 'senior'),
    ('network-architect', 'network', 'Network Architect', 'Defines network architecture and standards', 'senior', 'principal'),
    ('network-security-engineer', 'network', 'Network Security Engineer', 'Secures network paths and perimeter controls', 'mid', 'senior'),
    ('noc-engineer', 'network', 'NOC Engineer', 'Monitors and responds to network operations events', 'junior', 'mid'),
    ('telecom-engineer', 'network', 'Telecom Engineer', 'Manages telephony and communication systems', 'mid', 'senior'),

    -- Cybersecurity
    ('cybersecurity-analyst', 'security', 'Cybersecurity Analyst', 'Monitors, analyzes, and reports security risk', 'junior', 'senior'),
    ('security-engineer', 'security', 'Security Engineer', 'Builds and operates security controls', 'mid', 'senior'),
    ('application-security-engineer', 'security', 'Application Security Engineer', 'Secures software design and delivery', 'mid', 'senior'),
    ('penetration-tester', 'security', 'Penetration Tester', 'Tests systems by simulating attacks', 'mid', 'senior'),
    ('soc-analyst', 'security', 'SOC Analyst', 'Monitors and triages security events', 'junior', 'senior'),
    ('incident-responder', 'security', 'Incident Responder', 'Leads containment and recovery for incidents', 'mid', 'senior'),
    ('grc-analyst', 'security', 'GRC Analyst', 'Manages governance, risk, and compliance evidence', 'junior', 'senior'),
    ('iam-engineer', 'security', 'IAM Engineer', 'Builds identity and access management controls', 'mid', 'senior'),
    ('security-architect', 'security', 'Security Architect', 'Defines security architecture and control models', 'senior', 'principal'),
    ('security-manager', 'security', 'Security Manager', 'Leads security operations and strategy', 'manager', 'director'),
    ('forensics-analyst', 'security', 'Forensics Analyst', 'Investigates digital evidence and incidents', 'mid', 'senior'),
    ('threat-intelligence-analyst', 'security', 'Threat Intelligence Analyst', 'Tracks threats and adversary behavior', 'mid', 'senior'),

    -- Data & Analytics
    ('data-analyst', 'data', 'Data Analyst', 'Analyzes data and produces decision support', 'junior', 'senior'),
    ('data-engineer', 'data', 'Data Engineer', 'Builds data pipelines and storage layers', 'mid', 'senior'),
    ('data-scientist', 'data', 'Data Scientist', 'Builds models and experiments from data', 'mid', 'senior'),
    ('business-intelligence-analyst', 'data', 'Business Intelligence Analyst', 'Builds dashboards and reporting models', 'junior', 'senior'),
    ('analytics-engineer', 'data', 'Analytics Engineer', 'Models data for analytics and reporting', 'mid', 'senior'),
    ('data-architect', 'data', 'Data Architect', 'Defines data architecture and governance', 'senior', 'principal'),
    ('database-developer', 'data', 'Database Developer', 'Builds database logic and queries', 'junior', 'senior'),
    ('etl-developer', 'data', 'ETL Developer', 'Builds extract, transform, and load pipelines', 'mid', 'senior'),
    ('big-data-engineer', 'data', 'Big Data Engineer', 'Builds large-scale data processing systems', 'mid', 'senior'),
    ('data-governance-analyst', 'data', 'Data Governance Analyst', 'Defines data quality, lineage, and policy', 'mid', 'senior'),
    ('data-platform-engineer', 'data', 'Data Platform Engineer', 'Builds shared data platforms and services', 'mid', 'senior'),

    -- AI & Machine Learning
    ('machine-learning-engineer', 'ai_ml', 'Machine Learning Engineer', 'Builds and deploys ML models', 'mid', 'senior'),
    ('ai-engineer', 'ai_ml', 'AI Engineer', 'Builds AI-powered applications and services', 'mid', 'senior'),
    ('mlops-engineer', 'ai_ml', 'MLOps Engineer', 'Operates ML pipelines and model lifecycle', 'mid', 'senior'),
    ('nlp-engineer', 'ai_ml', 'NLP Engineer', 'Builds natural language processing systems', 'mid', 'senior'),
    ('computer-vision-engineer', 'ai_ml', 'Computer Vision Engineer', 'Builds image and video understanding systems', 'mid', 'senior'),
    ('deep-learning-engineer', 'ai_ml', 'Deep Learning Engineer', 'Builds neural network models', 'mid', 'senior'),
    ('ai-research-engineer', 'ai_ml', 'AI Research Engineer', 'Researches and prototypes AI techniques', 'senior', 'principal'),
    ('ai-solutions-architect', 'ai_ml', 'AI Solutions Architect', 'Designs AI solutions for business problems', 'senior', 'principal'),
    ('llm-engineer', 'ai_ml', 'LLM Engineer', 'Builds production systems around large language models', 'mid', 'senior'),
    ('prompt-engineer', 'ai_ml', 'Prompt Engineer', 'Designs, evaluates, and maintains prompts', 'mid', 'senior'),

    -- Database
    ('database-administrator', 'database', 'Database Administrator', 'Runs database availability, backup, and access', 'junior', 'senior'),
    ('database-engineer', 'database', 'Database Engineer', 'Builds and tunes database platforms', 'mid', 'senior'),
    ('database-architect', 'database', 'Database Architect', 'Defines database architecture and standards', 'senior', 'principal'),
    ('database-optimization-specialist', 'database', 'Database Optimization Specialist', 'Tunes queries, indexes, and performance', 'mid', 'senior'),
    ('data-warehouse-engineer', 'database', 'Data Warehouse Engineer', 'Builds and operates data warehouse platforms', 'mid', 'senior'),
    ('database-reliability-engineer', 'database', 'Database Reliability Engineer', 'Runs database reliability and automation', 'mid', 'senior'),

    -- IT Support & Service Management
    ('it-support-specialist', 'it_support', 'IT Support Specialist', 'Resolves end-user IT issues', 'intern', 'senior'),
    ('helpdesk-technician', 'it_support', 'Helpdesk Technician', 'Handles first-line support requests', 'intern', 'mid'),
    ('service-desk-analyst', 'it_support', 'Service Desk Analyst', 'Triages and resolves service desk tickets', 'junior', 'mid'),
    ('desktop-support-engineer', 'it_support', 'Desktop Support Engineer', 'Supports desktops, devices, and end-user software', 'junior', 'senior'),
    ('application-support-analyst', 'it_support', 'Application Support Analyst', 'Supports production applications and users', 'junior', 'senior'),
    ('it-operations-analyst', 'it_support', 'IT Operations Analyst', 'Runs day-to-day IT operations and monitoring', 'junior', 'senior'),
    ('it-asset-manager', 'it_support', 'IT Asset Manager', 'Manages hardware, software, and license inventory', 'mid', 'senior'),
    ('it-service-manager', 'it_support', 'IT Service Manager', 'Owns IT service levels and service catalog', 'manager', 'director'),
    ('incident-manager', 'it_support', 'Incident Manager', 'Coordinates major incident response', 'mid', 'manager'),
    ('problem-manager', 'it_support', 'Problem Manager', 'Finds and removes root causes of incidents', 'mid', 'manager'),
    ('change-manager', 'it_support', 'Change Manager', 'Runs change control and release approval', 'mid', 'manager'),
    ('configuration-manager', 'it_support', 'Configuration Manager', 'Maintains the configuration management database', 'mid', 'senior'),
    ('service-delivery-manager', 'it_support', 'Service Delivery Manager', 'Owns service delivery and customer outcomes', 'manager', 'director'),

    -- Architecture
    ('enterprise-architect', 'architecture', 'Enterprise Architect', 'Aligns IT architecture with business strategy', 'senior', 'principal'),
    ('solutions-architect', 'architecture', 'Solutions Architect', 'Designs end-to-end solutions for requirements', 'senior', 'principal'),
    ('technical-architect', 'architecture', 'Technical Architect', 'Defines technical architecture for a domain', 'senior', 'principal'),
    ('integration-architect', 'architecture', 'Integration Architect', 'Designs integration and API landscapes', 'senior', 'principal'),
    ('it-architect', 'architecture', 'IT Architect', 'Designs IT systems and platforms', 'senior', 'principal'),
    ('systems-architect', 'architecture', 'Systems Architect', 'Designs system platforms and integration architecture', 'senior', 'principal'),

    -- IT Management & Governance
    ('it-manager', 'it_management', 'IT Manager', 'Manages IT teams and service delivery', 'manager', 'director'),
    ('it-director', 'it_management', 'IT Director', 'Owns IT strategy, budget, and portfolio', 'director', 'director'),
    ('it-project-manager', 'it_management', 'IT Project Manager', 'Delivers IT projects on scope, time, and budget', 'mid', 'senior'),
    ('it-program-manager', 'it_management', 'IT Program Manager', 'Manages related IT projects and outcomes', 'senior', 'director'),
    ('it-governance-manager', 'it_management', 'IT Governance Manager', 'Owns IT policy, controls, and decision rights', 'manager', 'director'),
    ('it-risk-manager', 'it_management', 'IT Risk Manager', 'Identifies and manages IT risk', 'mid', 'senior'),
    ('it-compliance-manager', 'it_management', 'IT Compliance Manager', 'Ensures IT meets regulatory obligations', 'mid', 'senior'),
    ('it-auditor', 'it_management', 'IT Auditor', 'Audits IT controls and evidence', 'mid', 'senior'),
    ('it-consultant', 'it_management', 'IT Consultant', 'Advises on IT problems and improvements', 'mid', 'senior'),
    ('it-trainer', 'it_management', 'IT Trainer', 'Trains users and staff on IT systems', 'junior', 'senior'),
    ('it-procurement-specialist', 'it_management', 'IT Procurement Specialist', 'Buys IT hardware, software, and services', 'mid', 'senior'),
    ('technical-program-manager', 'it_management', 'Technical Program Manager', 'Leads cross-team technical programs', 'senior', 'director'),

    -- IT Business Analysis
    ('it-business-analyst', 'business_analysis', 'IT Business Analyst', 'Translates IT needs into requirements', 'junior', 'senior'),
    ('systems-analyst', 'business_analysis', 'Systems Analyst', 'Analyzes systems and designs changes', 'mid', 'senior'),
    ('functional-analyst', 'business_analysis', 'Functional Analyst', 'Specifies functional behavior of IT systems', 'junior', 'senior'),
    ('it-product-owner', 'business_analysis', 'IT Product Owner', 'Owns the IT product backlog and value', 'mid', 'senior'),
    ('it-scrum-master', 'business_analysis', 'IT Scrum Master', 'Facilitates agile delivery for IT teams', 'mid', 'senior'),
    ('requirements-engineer', 'business_analysis', 'Requirements Engineer', 'Elicits, specifies, and validates requirements', 'mid', 'senior'),

    -- UI/UX Design
    ('ui-designer', 'design', 'UI Designer', 'Designs visual interfaces', 'junior', 'senior'),
    ('ux-designer', 'design', 'UX Designer', 'Designs user flows and experiences', 'mid', 'senior'),
    ('product-designer', 'design', 'Product Designer', 'Designs end-to-end product experiences', 'mid', 'senior'),
    ('interaction-designer', 'design', 'Interaction Designer', 'Designs interaction behavior and prototypes', 'mid', 'senior'),
    ('ux-researcher', 'design', 'UX Researcher', 'Researches user needs and validates designs', 'mid', 'senior'),

    -- ERP/CRM & Enterprise Apps
    ('erp-administrator', 'erp_crm', 'ERP Administrator', 'Administers ERP platforms and users', 'mid', 'senior'),
    ('crm-administrator', 'erp_crm', 'CRM Administrator', 'Administers CRM platforms and data', 'mid', 'senior'),
    ('salesforce-developer', 'erp_crm', 'Salesforce Developer', 'Builds Salesforce customizations and integrations', 'mid', 'senior'),
    ('sap-consultant', 'erp_crm', 'SAP Consultant', 'Configures and supports SAP processes', 'mid', 'senior'),
    ('workday-consultant', 'erp_crm', 'Workday Consultant', 'Configures and supports Workday', 'mid', 'senior'),
    ('servicenow-developer', 'erp_crm', 'ServiceNow Developer', 'Builds ServiceNow workflows and integrations', 'mid', 'senior'),
    ('dynamics-365-developer', 'erp_crm', 'Dynamics 365 Developer', 'Builds Dynamics 365 customizations', 'mid', 'senior'),
    ('oracle-erp-consultant', 'erp_crm', 'Oracle ERP Consultant', 'Configures and supports Oracle ERP', 'mid', 'senior'),

    -- Technical Writing
    ('technical-writer', 'technical_writing', 'Technical Writer', 'Writes accurate technical documentation', 'junior', 'senior'),
    ('documentation-engineer', 'technical_writing', 'Documentation Engineer', 'Builds documentation systems and tooling', 'mid', 'senior')
ON CONFLICT (slug) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 2. IT-relevant competencies
-- ----------------------------------------------------------------------------

INSERT INTO competencies
    (id, name, category, primary_dimension, evidence_dimensions, default_min_evidence, description)
VALUES
    ('tech_core', 'Core Language Proficiency', 'technical', 'technical', ARRAY['technical','completeness'], 2, 'Depth in the primary language and its idioms'),
    ('tech_framework', 'Framework & Library Knowledge', 'technical', 'technical', ARRAY['technical','confidence'], 2, 'Practical use of the role framework and libraries'),
    ('tech_system_design', 'System Design & Architecture', 'technical', 'technical', ARRAY['technical','reasoning'], 3, 'Designs components, boundaries, and trade-offs'),
    ('tech_data', 'Data Structures & Algorithms', 'technical', 'technical', ARRAY['technical','reasoning'], 2, 'Chooses and applies data structures and algorithms'),
    ('tech_db', 'Database & Storage', 'technical', 'technical', ARRAY['technical','completeness'], 2, 'Models, queries, and operates data storage'),
    ('tech_devops', 'DevOps & Infrastructure', 'technical', 'technical', ARRAY['technical','confidence'], 1, 'Automates delivery and runs infrastructure'),
    ('tech_testing', 'Testing & Quality', 'technical', 'technical', ARRAY['technical','completeness'], 1, 'Prevents and detects defects with tests'),
    ('tech_security', 'Security Practices', 'technical', 'technical', ARRAY['technical','reasoning'], 1, 'Applies secure design and operational controls'),
    ('tech_event_driven', 'Event-Driven & Streaming Systems', 'technical', 'technical', ARRAY['technical','reasoning'], 2, 'Designs asynchronous and streaming systems'),
    ('tech_deployment', 'Deployment & Release Engineering', 'technical', 'technical', ARRAY['technical','completeness'], 1, 'Ships changes safely and repeatably'),
    ('tech_caching', 'Caching & Performance', 'technical', 'technical', ARRAY['technical','reasoning'], 1, 'Improves latency and throughput with caching'),
    ('tech_data_modeling', 'Data Modeling & Schema Design', 'technical', 'technical', ARRAY['technical','completeness'], 2, 'Designs normalized and fit-for-purpose schemas'),
    ('tech_networking', 'Networking & Protocols', 'technical', 'technical', ARRAY['technical','reasoning'], 1, 'Understands routing, switching, DNS, and protocols'),
    ('tech_cloud', 'Cloud Platforms & Services', 'technical', 'technical', ARRAY['technical','completeness'], 1, 'Uses cloud compute, storage, and managed services'),
    ('tech_automation', 'Automation & Scripting', 'technical', 'technical', ARRAY['technical','completeness'], 1, 'Automates manual and repetitive work'),
    ('tech_monitoring', 'Monitoring & Observability', 'technical', 'technical', ARRAY['technical','completeness'], 1, 'Measures health, logs, metrics, and traces'),
    ('tech_incident_response', 'Incident Response', 'technical', 'technical', ARRAY['technical','reasoning'], 1, 'Detects, contains, and recovers from incidents'),
    ('tech_virtualization', 'Virtualization & Containers', 'technical', 'technical', ARRAY['technical','completeness'], 1, 'Runs workloads on virtual and container platforms'),
    ('tech_embedded', 'Embedded & Firmware', 'technical', 'technical', ARRAY['technical','reasoning'], 2, 'Builds software close to hardware'),
    ('tech_game', 'Game Development', 'technical', 'technical', ARRAY['technical','reasoning'], 2, 'Builds gameplay, rendering, or game systems'),
    ('tech_mobile', 'Mobile Development', 'technical', 'technical', ARRAY['technical','completeness'], 2, 'Builds and ships mobile applications'),
    ('tech_accessibility', 'Accessibility & Inclusive Design', 'technical', 'technical', ARRAY['technical','communication'], 1, 'Meets accessibility standards and user needs'),
    ('tech_ui_implementation', 'UI Implementation', 'technical', 'technical', ARRAY['technical','completeness'], 1, 'Turns designs into working interfaces'),
    ('tech_data_pipelines', 'Data Pipelines & ETL', 'technical', 'technical', ARRAY['technical','completeness'], 2, 'Moves and transforms data reliably'),
    ('tech_ml', 'Machine Learning Engineering', 'technical', 'technical', ARRAY['technical','reasoning'], 2, 'Builds and evaluates machine-learning systems'),
    ('tech_llm', 'LLM & Prompt Engineering', 'technical', 'technical', ARRAY['technical','reasoning'], 2, 'Builds with large language models'),
    ('tech_iac', 'Infrastructure as Code', 'technical', 'technical', ARRAY['technical','completeness'], 1, 'Defines infrastructure in versioned code'),
    ('tech_ci_cd', 'CI/CD Pipeline Engineering', 'technical', 'technical', ARRAY['technical','completeness'], 1, 'Builds build-test-deploy pipelines'),
    ('tech_release', 'Release & Change Management', 'technical', 'technical', ARRAY['technical','communication'], 1, 'Plans, approves, and ships changes safely'),
    ('tech_service_mgmt', 'IT Service Management', 'technical', 'technical', ARRAY['technical','communication'], 1, 'Runs incidents, problems, changes, and SLAs'),
    ('tech_asset_mgmt', 'IT Asset Management', 'technical', 'technical', ARRAY['technical','completeness'], 1, 'Tracks hardware, software, and licenses'),
    ('tech_erp_crm', 'ERP/CRM Systems', 'technical', 'technical', ARRAY['technical','completeness'], 2, 'Configures and extends enterprise applications'),
    ('tech_technical_writing', 'Technical Writing', 'technical', 'communication', ARRAY['communication','completeness'], 1, 'Writes clear, accurate technical documentation'),

    ('behav_teamwork', 'Teamwork & Collaboration', 'behavioral', 'behavioral', ARRAY['behavioral','communication'], 2, 'Works effectively with others'),
    ('behav_leadership', 'Leadership & Ownership', 'behavioral', 'behavioral', ARRAY['behavioral','confidence'], 2, 'Takes ownership and leads others'),
    ('behav_conflict', 'Conflict Resolution', 'behavioral', 'behavioral', ARRAY['behavioral','reasoning'], 2, 'Handles disagreement constructively'),
    ('behav_communication', 'Communication Clarity', 'behavioral', 'communication', ARRAY['communication','completeness'], 1, 'Explains ideas clearly to the audience'),
    ('behav_adaptability', 'Adaptability & Learning', 'behavioral', 'behavioral', ARRAY['behavioral','confidence'], 1, 'Learns and adjusts to change'),

    ('cog_problem_solving', 'Problem Solving', 'cognitive', 'reasoning', ARRAY['reasoning','technical'], 2, 'Decomposes and solves unfamiliar problems'),
    ('cog_analytical', 'Analytical Thinking', 'cognitive', 'reasoning', ARRAY['reasoning','completeness'], 2, 'Reasons from evidence and data'),
    ('cog_creativity', 'Creativity & Innovation', 'cognitive', 'reasoning', ARRAY['reasoning','behavioral'], 1, 'Generates novel and useful options'),
    ('cog_decision_making', 'Decision Making', 'cognitive', 'reasoning', ARRAY['reasoning','confidence'], 2, 'Chooses among trade-offs with evidence'),

    ('exp_project_depth', 'Project Depth & Impact', 'experience', 'domain', ARRAY['domain','completeness'], 2, 'Has delivered meaningful work end to end'),
    ('exp_domain', 'Domain Knowledge', 'experience', 'domain', ARRAY['domain','completeness'], 2, 'Understands the business or technical domain'),
    ('exp_scaling', 'Scale & Complexity Experience', 'experience', 'domain', ARRAY['domain','reasoning'], 2, 'Has worked on large or complex systems'),
    ('exp_best_practices', 'Engineering Best Practices', 'experience', 'domain', ARRAY['domain','technical'], 1, 'Applies proven engineering practices'),

    ('des_ux_research', 'UX Research & User Insight', 'design', 'domain', ARRAY['domain','communication'], 2, 'Understands user needs through research'),
    ('des_visual_design', 'Visual & Interaction Design', 'design', 'domain', ARRAY['domain','communication'], 2, 'Creates clear and usable visual designs'),
    ('des_prototyping', 'Prototyping & Iteration', 'design', 'domain', ARRAY['domain','completeness'], 2, 'Builds and iterates prototypes'),
    ('des_design_systems', 'Design Systems & Consistency', 'design', 'domain', ARRAY['domain','completeness'], 2, 'Builds reusable and consistent design systems'),
    ('des_product_thinking', 'Product Thinking for Design', 'design', 'domain', ARRAY['domain','reasoning'], 2, 'Connects design to product outcomes'),

    ('prd_product_strategy', 'Product Strategy & Vision', 'product', 'domain', ARRAY['domain','reasoning'], 2, 'Defines product direction and value'),
    ('prd_user_stories', 'Requirements & User Stories', 'product', 'domain', ARRAY['domain','communication'], 2, 'Turns needs into clear requirements'),
    ('prd_roadmap_prioritization', 'Roadmapping & Prioritization', 'product', 'domain', ARRAY['domain','reasoning'], 2, 'Sequences work by value and risk'),
    ('prd_data_metrics', 'Product Metrics & Analysis', 'product', 'domain', ARRAY['domain','reasoning'], 2, 'Defines and uses product metrics'),
    ('prd_stakeholder_management', 'Stakeholder Management', 'product', 'communication', ARRAY['communication','behavioral'], 2, 'Aligns stakeholders on decisions'),

    ('ops_process_improvement', 'Process Improvement & Optimization', 'operations', 'domain', ARRAY['domain','completeness'], 2, 'Improves how work gets done'),
    ('ops_project_management', 'Project & Program Management', 'operations', 'domain', ARRAY['domain','communication'], 2, 'Delivers projects and programs'),
    ('ops_kpi_management', 'KPI & Operational Metrics', 'operations', 'domain', ARRAY['domain','reasoning'], 1, 'Defines and tracks operational indicators'),
    ('ops_vendor_management', 'Vendor & Partner Management', 'operations', 'domain', ARRAY['domain','communication'], 1, 'Manages suppliers and partners')
ON CONFLICT (id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 3. Family-level competency map (baseline for every role in the family)
-- ----------------------------------------------------------------------------

INSERT INTO role_competencies (role_id, competency_id, weight, required_level, is_core)
SELECT r.id, m.competency_id, m.weight, m.required_level, m.is_core
FROM it_roles r
JOIN (VALUES
    ('software_engineering', 'tech_core',              3.0, 'mid',    true),
    ('software_engineering', 'tech_system_design',     3.0, 'mid',    true),
    ('software_engineering', 'tech_data',              2.0, 'junior', true),
    ('software_engineering', 'tech_testing',           2.0, 'junior', true),
    ('software_engineering', 'cog_problem_solving',    2.0, 'mid',    true),
    ('software_engineering', 'behav_teamwork',         1.0, 'junior', false),

    ('frontend', 'tech_core',                3.0, 'mid',    true),
    ('frontend', 'tech_framework',           3.0, 'mid',    true),
    ('frontend', 'tech_ui_implementation',   2.0, 'mid',    true),
    ('frontend', 'tech_accessibility',       2.0, 'junior', true),
    ('frontend', 'tech_testing',             1.0, 'junior', false),
    ('frontend', 'behav_communication',      1.0, 'junior', false),

    ('backend', 'tech_core',             3.0, 'mid',    true),
    ('backend', 'tech_framework',        2.0, 'mid',    true),
    ('backend', 'tech_db',               3.0, 'mid',    true),
    ('backend', 'tech_system_design',    3.0, 'mid',    true),
    ('backend', 'tech_caching',          2.0, 'mid',    true),
    ('backend', 'tech_security',         2.0, 'junior', true),

    ('fullstack', 'tech_core',               3.0, 'mid',    true),
    ('fullstack', 'tech_framework',          2.0, 'mid',    true),
    ('fullstack', 'tech_db',                 2.0, 'mid',    true),
    ('fullstack', 'tech_ui_implementation',  2.0, 'mid',    true),
    ('fullstack', 'tech_system_design',      2.0, 'mid',    true),
    ('fullstack', 'tech_testing',            1.0, 'junior', false),

    ('mobile', 'tech_core',               3.0, 'mid',    true),
    ('mobile', 'tech_mobile',             3.0, 'mid',    true),
    ('mobile', 'tech_framework',          2.0, 'mid',    true),
    ('mobile', 'tech_ui_implementation',  2.0, 'mid',    true),
    ('mobile', 'tech_testing',            1.0, 'junior', false),
    ('mobile', 'tech_security',           1.0, 'junior', false),

    ('game', 'tech_core',        2.0, 'mid',    true),
    ('game', 'tech_game',        3.0, 'mid',    true),
    ('game', 'tech_data',        2.0, 'junior', true),
    ('game', 'tech_caching',     2.0, 'mid',    true),
    ('game', 'cog_creativity',   2.0, 'mid',    false),
    ('game', 'tech_testing',     1.0, 'junior', false),

    ('embedded', 'tech_core',       2.0, 'mid',    true),
    ('embedded', 'tech_embedded',   3.0, 'mid',    true),
    ('embedded', 'tech_data',       2.0, 'junior', true),
    ('embedded', 'tech_testing',    2.0, 'junior', true),
    ('embedded', 'tech_security',   1.0, 'junior', false),
    ('embedded', 'tech_monitoring', 1.0, 'junior', false),

    ('qa', 'tech_testing',        3.0, 'mid',    true),
    ('qa', 'tech_automation',     2.0, 'mid',    true),
    ('qa', 'tech_core',           2.0, 'junior', true),
    ('qa', 'cog_analytical',      2.0, 'mid',    true),
    ('qa', 'behav_communication', 1.0, 'junior', false),
    ('qa', 'tech_security',       1.0, 'junior', false),

    ('devops', 'tech_devops',        3.0, 'mid',    true),
    ('devops', 'tech_ci_cd',         3.0, 'mid',    true),
    ('devops', 'tech_iac',           2.0, 'mid',    true),
    ('devops', 'tech_monitoring',    2.0, 'mid',    true),
    ('devops', 'tech_security',      2.0, 'junior', true),
    ('devops', 'tech_release',       1.0, 'junior', false),

    ('cloud', 'tech_cloud',       3.0, 'mid',    true),
    ('cloud', 'tech_iac',         2.0, 'mid',    true),
    ('cloud', 'tech_networking',  2.0, 'mid',    true),
    ('cloud', 'tech_security',    2.0, 'mid',    true),
    ('cloud', 'tech_monitoring',  2.0, 'junior', true),
    ('cloud', 'tech_devops',      1.0, 'junior', false),

    ('infrastructure', 'tech_virtualization', 3.0, 'mid',    true),
    ('infrastructure', 'tech_networking',     2.0, 'mid',    true),
    ('infrastructure', 'tech_monitoring',     2.0, 'mid',    true),
    ('infrastructure', 'tech_security',       2.0, 'junior', true),
    ('infrastructure', 'tech_devops',         1.0, 'junior', false),
    ('infrastructure', 'tech_service_mgmt',   1.0, 'junior', false),

    ('network', 'tech_networking',        3.0, 'mid',    true),
    ('network', 'tech_security',          2.0, 'mid',    true),
    ('network', 'tech_monitoring',        2.0, 'mid',    true),
    ('network', 'tech_cloud',             1.0, 'junior', false),
    ('network', 'tech_incident_response', 1.0, 'junior', false),
    ('network', 'cog_analytical',         1.0, 'junior', false),

    ('security', 'tech_security',           3.0, 'mid',    true),
    ('security', 'tech_incident_response',  2.0, 'mid',    true),
    ('security', 'tech_monitoring',         2.0, 'mid',    true),
    ('security', 'tech_networking',         1.0, 'junior', false),
    ('security', 'tech_cloud',              1.0, 'junior', false),
    ('security', 'cog_analytical',          1.0, 'junior', false),

    ('data', 'tech_data_pipelines', 3.0, 'mid',    true),
    ('data', 'tech_db',             2.0, 'mid',    true),
    ('data', 'tech_data_modeling',  2.0, 'mid',    true),
    ('data', 'tech_ml',             1.0, 'junior', false),
    ('data', 'cog_analytical',      2.0, 'junior', true),
    ('data', 'tech_data',           1.0, 'junior', false),

    ('ai_ml', 'tech_ml',             3.0, 'mid',    true),
    ('ai_ml', 'tech_llm',            2.0, 'mid',    true),
    ('ai_ml', 'tech_data_pipelines', 2.0, 'mid',    true),
    ('ai_ml', 'tech_data',           1.0, 'junior', false),
    ('ai_ml', 'tech_cloud',          1.0, 'junior', false),
    ('ai_ml', 'cog_problem_solving', 1.0, 'junior', false),

    ('database', 'tech_db',              3.0, 'mid',    true),
    ('database', 'tech_data_modeling',   3.0, 'mid',    true),
    ('database', 'tech_caching',         2.0, 'mid',    true),
    ('database', 'tech_monitoring',      2.0, 'junior', true),
    ('database', 'tech_security',        1.0, 'junior', false),
    ('database', 'cog_analytical',       1.0, 'junior', false),

    ('it_support', 'tech_service_mgmt',     3.0, 'mid',    true),
    ('it_support', 'tech_asset_mgmt',       2.0, 'junior', true),
    ('it_support', 'tech_monitoring',       1.0, 'junior', false),
    ('it_support', 'behav_communication',   2.0, 'junior', true),
    ('it_support', 'cog_problem_solving',   1.0, 'junior', false),
    ('it_support', 'tech_security',         1.0, 'junior', false),

    ('architecture', 'tech_system_design',          3.0, 'senior', true),
    ('architecture', 'tech_cloud',                  2.0, 'senior', true),
    ('architecture', 'tech_security',               2.0, 'senior', true),
    ('architecture', 'tech_data_modeling',          1.0, 'mid',    false),
    ('architecture', 'exp_scaling',                 2.0, 'senior', true),
    ('architecture', 'prd_stakeholder_management',  1.0, 'mid',    false),

    ('it_management', 'ops_project_management',        3.0, 'mid',    true),
    ('it_management', 'ops_kpi_management',            2.0, 'mid',    true),
    ('it_management', 'ops_vendor_management',         2.0, 'mid',    true),
    ('it_management', 'behav_leadership',              3.0, 'mid',    true),
    ('it_management', 'prd_stakeholder_management',    2.0, 'mid',    true),
    ('it_management', 'tech_service_mgmt',             1.0, 'junior', false),

    ('business_analysis', 'prd_user_stories',             3.0, 'mid',    true),
    ('business_analysis', 'prd_stakeholder_management',   2.0, 'mid',    true),
    ('business_analysis', 'cog_analytical',               2.0, 'mid',    true),
    ('business_analysis', 'behav_communication',          2.0, 'junior', true),
    ('business_analysis', 'ops_process_improvement',      1.0, 'junior', false),
    ('business_analysis', 'prd_data_metrics',             1.0, 'junior', false),

    ('design', 'des_ux_research',        3.0, 'mid',    true),
    ('design', 'des_visual_design',      2.0, 'mid',    true),
    ('design', 'des_prototyping',        2.0, 'mid',    true),
    ('design', 'des_design_systems',     2.0, 'mid',    true),
    ('design', 'des_product_thinking',   1.0, 'junior', false),
    ('design', 'tech_accessibility',     1.0, 'junior', false),

    ('erp_crm', 'tech_erp_crm',             3.0, 'mid',    true),
    ('erp_crm', 'tech_db',                  2.0, 'mid',    true),
    ('erp_crm', 'ops_process_improvement',  2.0, 'mid',    true),
    ('erp_crm', 'behav_communication',      1.0, 'junior', false),
    ('erp_crm', 'tech_security',            1.0, 'junior', false),
    ('erp_crm', 'prd_user_stories',         1.0, 'junior', false),

    ('technical_writing', 'tech_technical_writing', 3.0, 'mid',    true),
    ('technical_writing', 'behav_communication',    2.0, 'mid',    true),
    ('technical_writing', 'cog_analytical',         2.0, 'junior', true),
    ('technical_writing', 'tech_security',          1.0, 'junior', false),
    ('technical_writing', 'prd_user_stories',       1.0, 'junior', false),
    ('technical_writing', 'des_design_systems',     1.0, 'junior', false)
) AS m(family, competency_id, weight, required_level, is_core)
ON r.family = m.family
ON CONFLICT (role_id, competency_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- End of seed
