"""AURA V5 generation capabilities — question generation (LLM + deterministic).

Stateless over ``InterviewBrain`` fragments (plus the LLM service it may call);
never reads the database and never mutates shared state.
"""
