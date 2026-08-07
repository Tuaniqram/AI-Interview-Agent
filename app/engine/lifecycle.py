"""V5 session lifecycle — the start node chain.

Builds the intelligence bundle (company/candidate brain), seeds the interview
state through the init/planning/hypothesis agents, generates the opening
question and persists the first brain snapshot.
"""
import logging

from app.core.interview_state import brain_to_dict, dict_to_brain, sync_brain

logger = logging.getLogger(__name__)

INTELLIGENCE_KEYS = (
    "company_brain",
    "interview_blueprint",
    "candidate_brain",
    "initial_hypotheses",
    "evidence_requirements",
    "candidate_assessment",
    "aura_brain",
)


async def start_session(engine, state: dict, build_intelligence: bool = False, intelligence: dict | None = None) -> dict:
    """Run the start node chain over a seeded V4-style state dict.

    ``intelligence`` may carry ``company_brain``, ``interview_blueprint``,
    ``candidate_brain``, ``initial_hypotheses``, ``evidence_requirements``
    and ``candidate_assessment`` — all of which are merged into the brain
    and thus visible to every downstream agent.

    When ``build_intelligence`` is True and no intelligence kwargs are
    supplied, the V5 intelligence module produces the bundle from the
    session fields (job role, department, candidate profile/resume,
    scorecard competencies). Every stage is best-effort.

    Returns the ``{type: question}`` response dict.
    """
    store = engine._get_store()
    events = engine._get_events()
    session_id = state["session_id"]
    intelligence = dict(intelligence or {})

    from app.engine.builders import build_start_response

    existing = store.get(session_id)
    if existing is not None and existing.get("nodes_executed"):
        return build_start_response(session_id, existing)

    from app.agents.init.session_init import session_init_node
    from app.agents.init.company_context import department_context_node
    from app.agents.init.candidate_profile import candidate_profile_node
    from app.agents.planning.competency_planner import competency_planner_node
    from app.agents.planning.strategy_planner import strategy_brain_node
    from app.agents.reasoning.hypothesis_engine import hypothesis_node
    from app.agents.generation.question_generator import question_generator_node

    brain = dict_to_brain(state)

    provided = {
        key: intelligence.get(key)
        for key in INTELLIGENCE_KEYS
        if intelligence.get(key) is not None
    }
    if build_intelligence and len(provided) < len(INTELLIGENCE_KEYS):
        from app.intelligence import build_interview_intelligence

        try:
            bundle = await build_interview_intelligence(
                job_role=state.get("job_role", ""),
                department_id=state.get("department_id"),
                style=state.get("interview_style"),
                candidate_profile=state.get("candidate_profile"),
                candidate_id=state.get("candidate_id", ""),
                resume_text=state.get("resume_text"),
                required_competencies=state.get("required_competencies"),
                scorecard_competencies=state.get("scorecard_competencies"),
                competency_taxonomy=state.get("competency_taxonomy"),
                company_brain=provided.get("company_brain"),
            )
            intelligence = {**bundle, **provided}
        except Exception as exc:  # noqa: BLE001 - intelligence is best-effort
            logger.warning(f"Automatic V5 intelligence build failed (non-fatal): {exc}")
            intelligence = provided

    # Normalize competency IDs from provided intelligence so taxonomy ids align
    try:
        from app.agents.reasoning.evidence_engine import _normalize_competency_alias
    except Exception:
        # fallback normalizer (best-effort)
        _normalize_competency_alias = lambda x: (str(x).strip().lower().replace(" ", "_") if x else "")

    # Normalize blueprint priority_competencies ids to canonical taxonomy ids
    ibp = intelligence.get("interview_blueprint") or {}
    pc = ibp.get("priority_competencies", []) if isinstance(ibp, dict) else []
    normalized_pc = []
    for p in pc:
        if isinstance(p, dict):
            raw_id = str(p.get("id", "") or "")
            norm = _normalize_competency_alias(raw_id) or raw_id.replace(" ", "_").lower()
            normalized_pc.append({"id": norm, "name": p.get("name", ""), "weight": p.get("weight", 1.0)})
    if normalized_pc:
        intelligence.setdefault("interview_blueprint", {})["priority_competencies"] = normalized_pc

    # Normalize evidence_requirements competency ids
    ers = intelligence.get("evidence_requirements", [])
    normalized_ers = []
    for er in ers or []:
        if not isinstance(er, dict):
            continue
        raw_comp = str(er.get("competency", "") or "")
        norm = _normalize_competency_alias(raw_comp) or raw_comp.replace(" ", "_").lower()
        er["competency"] = norm
        normalized_ers.append(er)
    if normalized_ers:
        intelligence["evidence_requirements"] = normalized_ers

    # Normalize initial hypotheses competency fields (if present)
    ih = intelligence.get("initial_hypotheses", [])
    for h in ih or []:
        if isinstance(h, dict) and h.get("competency"):
            raw_comp = str(h.get("competency", "") or "")
            h["competency"] = _normalize_competency_alias(raw_comp) or raw_comp.replace(" ", "_").lower()

    for key in INTELLIGENCE_KEYS:
        if intelligence.get(key) is not None:
            setattr(brain, key, intelligence[key])

    # AURA V5: the question planner already ranked uncertainty — seed the
    # engine's planned competency from it unless a caller set one explicitly.
    aura_plan = (intelligence.get("aura_brain") or {}).get("question_strategy") or {}
    if not brain.planned_competency and aura_plan.get("planned_competency"):
        brain.planned_competency = aura_plan["planned_competency"]

    s = brain_to_dict(brain)
    s = session_init_node(s)
    s = await department_context_node(s)
    s = await candidate_profile_node(s)
    s = await competency_planner_node(s)
    s = await strategy_brain_node(s)
    s = await hypothesis_node(s)

    target = s.get("hypothesis_target") or {}
    await events.append(session_id, "question_selected", {
        "question_number": s.get("question_number", 0),
        "target_hypothesis_id": target.get("id", ""),
        "competency": target.get("competency", ""),
        "status": target.get("status", ""),
        "selection_reason": target.get("selection_reason", ""),
        "information_gain": target.get("information_gain", 0.0),
    })

    s = await question_generator_node(s)
    brain = sync_brain(brain, s)
    brain.bump_version()

    store.set(session_id, brain.to_dict())
    store.checkpoint(session_id, brain.to_dict())

    await events.append(session_id, "session_started", {
        "job_role": brain.job_role,
        "department_id": brain.department_id,
        "competency_count": len(brain.required_competencies),
        "domain_label": brain.domain_label,
        "has_company_brain": brain.company_brain is not None,
        "has_blueprint": brain.interview_blueprint is not None,
        "has_candidate_brain": brain.candidate_brain is not None,
        "initial_hypotheses": len(brain.initial_hypotheses),
    })

    if any(intelligence.get(key) is not None for key in INTELLIGENCE_KEYS):
        from app.intelligence.persist import persist_intelligence_bundle

        await persist_intelligence_bundle(
            session_id,
            state.get("department_id"),
            state.get("job_role", ""),
            intelligence,
        )

    from app.engine.persistence import persist_v5_snapshot

    await persist_v5_snapshot(session_id, brain, engine._v5_persister)
    return build_start_response(session_id, brain)
