# Evidence Extractor

Map evaluation feedback to structured competency evidence.

## Input

- **Question**: {{question}}
- **Answer**: {{answer}}
- **Unified Evaluation**: {{evaluation_json}}

## Task

Extract structured evidence items from the evaluation. Each evidence item must map to a specific competency from the taxonomy.

For each dimension in the evaluation that has a non-null score:
1. Identify the relevant competency (match against the question objective or infer from the evidence text)
2. Extract the key observation as concise evidence text
3. Note any strengths and weaknesses

## Output Format

```json
{
    "evidence_items": [
        {
            "competency": "tech_core",
            "dimension": "technical",
            "score": 8.5,
            "evidence_text": "Demonstrated strong understanding of async/await with proper error handling",
            "confidence": 0.9,
            "strengths": ["Deep async understanding"],
            "weaknesses": []
        }
    ]
}
```
