COMPETENCY_TAXONOMY = [
    # Technical Competencies
    {
        "id": "tech_core",
        "category": "technical",
        "name": "Core Language Proficiency",
        "evidence_dimensions": ["technical", "completeness"],
        "default_min_evidence": 2,
    },
    {
        "id": "tech_framework",
        "category": "technical",
        "name": "Framework & Library Knowledge",
        "evidence_dimensions": ["technical", "confidence"],
        "default_min_evidence": 2,
    },
    {
        "id": "tech_system_design",
        "category": "technical",
        "name": "System Design & Architecture",
        "evidence_dimensions": ["technical", "reasoning"],
        "default_min_evidence": 3,
    },
    {
        "id": "tech_data",
        "category": "technical",
        "name": "Data Structures & Algorithms",
        "evidence_dimensions": ["technical", "reasoning"],
        "default_min_evidence": 2,
    },
    {
        "id": "tech_db",
        "category": "technical",
        "name": "Database & Storage",
        "evidence_dimensions": ["technical", "completeness"],
        "default_min_evidence": 2,
    },
    {
        "id": "tech_devops",
        "category": "technical",
        "name": "DevOps & Infrastructure",
        "evidence_dimensions": ["technical", "confidence"],
        "default_min_evidence": 1,
    },
    {
        "id": "tech_testing",
        "category": "technical",
        "name": "Testing & Quality",
        "evidence_dimensions": ["technical", "completeness"],
        "default_min_evidence": 1,
    },
    {
        "id": "tech_security",
        "category": "technical",
        "name": "Security Practices",
        "evidence_dimensions": ["technical", "reasoning"],
        "default_min_evidence": 1,
    },
    # Behavioral Competencies
    {
        "id": "behav_teamwork",
        "category": "behavioral",
        "name": "Teamwork & Collaboration",
        "evidence_dimensions": ["behavioral", "communication"],
        "default_min_evidence": 2,
    },
    {
        "id": "behav_leadership",
        "category": "behavioral",
        "name": "Leadership & Ownership",
        "evidence_dimensions": ["behavioral", "confidence"],
        "default_min_evidence": 2,
    },
    {
        "id": "behav_conflict",
        "category": "behavioral",
        "name": "Conflict Resolution",
        "evidence_dimensions": ["behavioral", "reasoning"],
        "default_min_evidence": 2,
    },
    {
        "id": "behav_communication",
        "category": "behavioral",
        "name": "Communication Clarity",
        "evidence_dimensions": ["communication", "completeness"],
        "default_min_evidence": 1,
    },
    {
        "id": "behav_adaptability",
        "category": "behavioral",
        "name": "Adaptability & Learning",
        "evidence_dimensions": ["behavioral", "confidence"],
        "default_min_evidence": 1,
    },
    # Cognitive Competencies
    {
        "id": "cog_problem_solving",
        "category": "cognitive",
        "name": "Problem Solving",
        "evidence_dimensions": ["reasoning", "technical"],
        "default_min_evidence": 2,
    },
    {
        "id": "cog_analytical",
        "category": "cognitive",
        "name": "Analytical Thinking",
        "evidence_dimensions": ["reasoning", "completeness"],
        "default_min_evidence": 2,
    },
    {
        "id": "cog_creativity",
        "category": "cognitive",
        "name": "Creativity & Innovation",
        "evidence_dimensions": ["reasoning", "behavioral"],
        "default_min_evidence": 1,
    },
    {
        "id": "cog_decision_making",
        "category": "cognitive",
        "name": "Decision Making",
        "evidence_dimensions": ["reasoning", "confidence"],
        "default_min_evidence": 2,
    },
    # Experience Competencies
    {
        "id": "exp_project_depth",
        "category": "experience",
        "name": "Project Depth & Impact",
        "evidence_dimensions": ["technical", "completeness"],
        "default_min_evidence": 2,
    },
    {
        "id": "exp_domain",
        "category": "experience",
        "name": "Domain Knowledge",
        "evidence_dimensions": ["technical", "confidence"],
        "default_min_evidence": 2,
    },
    {
        "id": "exp_scaling",
        "category": "experience",
        "name": "Scale & Complexity Experience",
        "evidence_dimensions": ["technical", "reasoning"],
        "default_min_evidence": 2,
    },
    {
        "id": "exp_best_practices",
        "category": "experience",
        "name": "Engineering Best Practices",
        "evidence_dimensions": ["technical", "behavioral"],
        "default_min_evidence": 1,
    },
]

COMPETENCY_CATEGORIES = ["technical", "behavioral", "cognitive", "experience"]

COMPETENCY_IDS = [c["id"] for c in COMPETENCY_TAXONOMY]

SKILL_TO_COMPETENCY = {
    "python": "tech_core",
    "javascript": "tech_core",
    "typescript": "tech_core",
    "java": "tech_core",
    "golang": "tech_core",
    "rust": "tech_core",
    "c++": "tech_core",
    "c#": "tech_core",
    "react": "tech_framework",
    "vue": "tech_framework",
    "angular": "tech_framework",
    "django": "tech_framework",
    "flask": "tech_framework",
    "fastapi": "tech_framework",
    "spring": "tech_framework",
    "express": "tech_framework",
    "node": "tech_framework",
    "laravel": "tech_framework",
    "rails": "tech_framework",
    "system design": "tech_system_design",
    "architecture": "tech_system_design",
    "microservices": "tech_system_design",
    "algorithms": "tech_data",
    "data structures": "tech_data",
    "sql": "tech_db",
    "nosql": "tech_db",
    "mongodb": "tech_db",
    "postgresql": "tech_db",
    "redis": "tech_db",
    "docker": "tech_devops",
    "kubernetes": "tech_devops",
    "aws": "tech_devops",
    "gcp": "tech_devops",
    "azure": "tech_devops",
    "ci/cd": "tech_devops",
    "testing": "tech_testing",
    "unit testing": "tech_testing",
    "integration testing": "tech_testing",
    "security": "tech_security",
    "authentication": "tech_security",
    "authorization": "tech_security",
    "team collaboration": "behav_teamwork",
    "teamwork": "behav_teamwork",
    "leadership": "behav_leadership",
    "ownership": "behav_leadership",
    "mentoring": "behav_leadership",
    "conflict resolution": "behav_conflict",
    "negotiation": "behav_conflict",
    "communication": "behav_communication",
    "adaptability": "behav_adaptability",
    "learning": "behav_adaptability",
    "problem solving": "cog_problem_solving",
    "analytical": "cog_analytical",
    "creativity": "cog_creativity",
    "innovation": "cog_creativity",
    "decision making": "cog_decision_making",
    "project management": "exp_project_depth",
    "domain expertise": "exp_domain",
    "scaling": "exp_scaling",
    "performance": "exp_scaling",
    "code review": "exp_best_practices",
    "best practices": "exp_best_practices",
    "design patterns": "exp_best_practices",
}


def get_competency(competency_id: str) -> dict:
    for c in COMPETENCY_TAXONOMY:
        if c["id"] == competency_id:
            return c
    return {}


def map_skill_to_competency(skill: str) -> str:
    return SKILL_TO_COMPETENCY.get(skill.lower().strip(), "tech_core")


def get_competencies_by_category(category: str) -> list:
    return [c for c in COMPETENCY_TAXONOMY if c["category"] == category]
