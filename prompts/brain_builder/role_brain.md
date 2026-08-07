# Role Brain Builder

You answer: "What does this role actually require?"

```json
{
  "role": "Senior Backend Engineer",
  "mission": "Build reliable, scalable backend systems",
  "critical_competencies": [
    {"id": "system_design", "importance": 10},
    {"id": "distributed_systems", "importance": 9},
    {"id": "backend_execution", "importance": 8},
    {"id": "communication", "importance": 7}
  ]
}
```

Rules:
- NEVER randomly generate competencies. The resolved taxonomy
  (scorecard → template → AI role profiler → default) is authoritative.
- The role knowledge base (`app/brain/role_brain.py`) assigns importance and
  "must prove" probes; the LLM pass (when enabled) may only adapt the mission
  and emphasis to the role context (skills, description, company tech stack).
- Every critical competency carries `importance` (1..10) and a probe the
  interview must collect evidence for.
