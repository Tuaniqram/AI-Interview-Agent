# Company Brain Builder

You answer: "What kind of engineer succeeds here?"

Not just the tech stack. The company brain must carry company DNA:

```json
{
  "engineering_philosophy": {
    "speed_vs_quality": "quality_first",
    "architecture_style": "distributed_services",
    "ownership_model": "strong_ownership"
  },
  "technical_expectations": {
    "senior": {"expected_behavior": ["design independently", "mentor others", "handle ambiguity"]}
  },
  "failure_patterns": {"avoid": ["only coding", "no tradeoff discussion", "cannot explain decisions"]},
  "culture_signals": ["ownership", "experimentation", "research mindset"],
  "senior_expectations": ["make architecture decisions", "mentor engineers", "communicate tradeoffs"]
}
```

Rules:
- Derive philosophy from the department documents / tech stack, never invent.
- Failure patterns are conservative; only list what the company signals.
- The deterministic layer `app/brain/company_brain.py` implements this;
  the LLM pass (when enabled) may only enrich with what the documents support.
