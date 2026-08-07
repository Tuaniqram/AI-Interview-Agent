"""AURA V5 competency knowledge graph.

Competencies are not a flat list. This module holds a deterministic knowledge
graph: competency nodes (canonical taxonomy ids plus role/skill nodes that
appear in AI-profiled taxonomies) with ``specializes``/``requires`` edges to
the sub-capabilities a senior engineer is expected to command.

Runtime evidence connects an ``evidence`` node to one or more of these
competency nodes (see ``app.brain.evidence_reasoner``), which is what makes
evaluation explainable: an answer about Kafka lands on both ``tech_event_driven``
(backend) and its ``event_ordering`` child.
"""
from app.data.competency_taxonomy import COMPETENCY_TAXONOMY

DEFAULT_EDGE_RELATION = "specializes"


def _comp_node(comp: dict) -> dict:
    return {
        "id": comp["id"],
        "name": comp["name"],
        "category": comp.get("category", "general"),
        "type": "competency",
        "default_min_evidence": comp.get("default_min_evidence", 2),
    }


_NODE = {c["id"]: _comp_node(c) for c in COMPETENCY_TAXONOMY}

COMPETENCY_CHILDREN: dict[str, list[tuple[str, str]]] = {
    "tech_system_design": [
        ("scalability", "Scale handling & growth"),
        ("reliability", "Fault tolerance & SLAs"),
        ("tradeoffs", "Design tradeoff debate"),
        ("architecture_decision", "Clear architecture decision rationale"),
        ("capacity_planning", "Load estimation"),
        ("observability", "Monitoring & tracing"),
    ],
    "tech_core": [
        ("language_ecosystem", "Language runtime & ecosystem"),
        ("concurrency", "Concurrency & async model"),
        ("memory_management", "Memory/alloc behavior"),
    ],
    "tech_framework": [
        ("framework_patterns", "Framework idioms"),
        ("api_design", "API surface design"),
    ],
    "tech_db": [
        ("indexing", "Index design"),
        ("query_optimization", "Query & plan optimization"),
        ("sharding", "Sharding & partitioning"),
        ("data_modeling", "Schema design"),
        ("transactions", "Transactions & consistency"),
        ("replication", "Replication & durability"),
    ],
    "tech_event_driven": [
        ("kafka", "Kafka/streaming fundamentals"),
        ("event_ordering", "Event ordering guarantees"),
        ("failure_handling", "Failure & DLQ handling"),
        ("idempotency", "Idempotent consumers"),
        ("backpressure", "Backpressure"),
    ],
    "tech_deployment": [
        ("ci_cd", "CI/CD pipelines"),
        ("infra_as_code", "Infrastructure as code"),
        ("zero_downtime", "Zero-downtime release"),
        ("deploy_strategy", "Rollout & rollback strategy"),
    ],
    "tech_data_modeling": [
        ("normalization", "Normalization"),
        ("aggregation", "Analytical aggregation"),
        ("schema_evolution", "Schema evolution"),
    ],
    "tech_caching": [
        ("cache_invalidation", "Cache invalidation"),
        ("eviction_strategy", "Eviction strategies"),
        ("staleness_handling", "Staleness handling"),
    ],
    "tech_devops": [
        ("docker_containers", "Containerization"),
        ("observability", "Monitoring & alerting"),
        ("cost_management", "Infrastructure cost"),
    ],
    "tech_security": [
        ("authn_authz", "AuthN/AuthZ"),
        ("secrets_handling", "Secrets management"),
        ("threat_modeling", "Threat modeling"),
    ],
    "tech_testing": [
        ("unit_tests", "Unit testing"),
        ("integration_tests", "Integration testing"),
        ("flaky_test_handling", "Flaky test management"),
    ],
    "behav_leadership": [
        ("mentoring", "Mentoring engineers"),
        ("delegation", "Delegation"),
        ("stakeholder_communication", "Stakeholder communication"),
    ],
    "behav_communication": [
        ("documentation", "Written documentation"),
        ("tradeoff_debate", "Debating technical tradeoffs"),
    ],
    "cog_problem_solving": [
        ("root_cause_analysis", "Root-cause analysis"),
        ("first_principles", "First-principles reasoning"),
        ("debugging_skill", "Systematic debugging"),
    ],
    "cog_analytical": [
        ("metric_driven", "Metric-driven thinking"),
        ("system_synthesis", "Synthesizing across systems"),
    ],
    "exp_scaling": [
        ("performance_patterns", "Performance patterns"),
        ("load_characteristics", "Understanding load"),
        ("failure_modes", "Failure-mode reasoning"),
    ],
    "exp_project_depth": [
        ("impact_quantification", "Quantified impact"),
        ("trade_actuals", "Real-world tradeoffs"),
    ],
    "cog_creativity": [
        ("novel_solutions", "Novel solution generation"),
    ],
}

KNOWN_SKILL_NODES = {
    "system_design": "System Design",
    "distributed_systems": "Distributed Systems",
    "backend_execution": "Backend Execution",
    "frontend_execution": "Frontend Execution",
    "ui_architecture": "UI Architecture",
    "api_design": "API Design",
    "event_driven": "Event-Driven Systems",
    "fault_tolerance": "Fault Tolerance",
    "monitoring": "Monitoring",
    "failure_recovery": "Failure Recovery",
}


def _build_graph() -> dict:
    nodes = dict(_NODE)
    edges = []
    for parent, children in COMPETENCY_CHILDREN.items():
        for node_id, label in children:
            if node_id not in nodes:
                nodes[node_id] = {
                    "id": node_id,
                    "name": label,
                    "type": "skill",
                    "default_min_evidence": 0,
                }
            edges.append(
                {
                    "source": parent,
                    "target": node_id,
                    "relation": DEFAULT_EDGE_RELATION,
                    "weight": 1.0,
                }
            )
    for node_id, label in KNOWN_SKILL_NODES.items():
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "name": label,
                "type": "skill",
                "default_min_evidence": 0,
            }
    return {"nodes": nodes, "edges": edges}


COMPETENCY_GRAPH = _build_graph()
KNOWLEDGE_NODE_IDS = set(COMPETENCY_GRAPH["nodes"].keys())


def competency_children(competency_id: str) -> list[str]:
    return [
        e["target"]
        for e in COMPETENCY_GRAPH["edges"]
        if e["source"] == competency_id and e.get("relation") == DEFAULT_EDGE_RELATION
    ]


def competency_parents(node_id: str) -> list[str]:
    if node_id in _NODE:
        return [node_id]
    return [
        e["source"]
        for e in COMPETENCY_GRAPH["edges"]
        if e["target"] == node_id
    ]


def taxonomy_to_graph(
    taxonomy: list[dict],
    required_ids: list[str] | None = None,
) -> dict:
    """Project the global graph onto a session taxonomy.

    Only competency nodes present in the resolved taxonomy are kept as parents;
    their knowledge children are retained so evidence can attach to granular
    capabilities. Unknown taxonomy ids degrade to stub nodes so AI-profiled
    competencies never vanish.
    """
    required_ids = required_ids or []
    required_set = set(required_ids)
    session_ids = [c.get("id") for c in taxonomy if isinstance(c, dict) and c.get("id")]
    all_required = not required_set

    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    for comp_id in session_ids:
        node = dict(_NODE.get(comp_id) or COMPETENCY_GRAPH["nodes"].get(comp_id) or {})
        node.setdefault("id", comp_id)
        node.setdefault("name", comp_id)
        node.setdefault("type", "competency")
        node["category"] = next(
            (c.get("category") for c in taxonomy if c.get("id") == comp_id),
            node.get("category", "scope"),
        )
        node["scope"] = "required" if (comp_id in required_set or all_required) else "context"
        nodes[comp_id] = node
        for child in competency_children(comp_id):
            child_node = dict(COMPETENCY_GRAPH["nodes"].get(child) or {})
            child_node.setdefault("id", child)
            child_node.setdefault("name", child)
            child_node.setdefault("type", "skill")
            nodes[child] = child_node
            edges.append(
                {
                    "source": comp_id,
                    "target": child,
                    "relation": DEFAULT_EDGE_RELATION,
                    "weight": 1.0,
                }
            )

    for node_id in required_ids:
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "name": node_id,
                "type": "competency",
                "category": "scope",
                "scope": "required",
            }

    return {"nodes": nodes, "edges": edges}