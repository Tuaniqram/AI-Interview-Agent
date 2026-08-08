export interface EmbeddedBrain {
  sid: string; role: string; verdict: string; composite: number; confidence: number; coverage: number;
  difficulty_reached: number; evidence_total: number;
  hypothesis_outcomes?: Record<string, number>;
  sufficiency?: { severity?: string; is_sufficient?: boolean; remaining_gaps?: number; coverage?: number };
  phases: Array<{ n: number; phase: string; difficulty: number; evidence_count: number }>;
  competencies: Array<{ id: string; avg: number; count: number; gap: number; scores: number[] }>;
  hypotheses: Array<Record<string, unknown>>;
  graph_edges: Array<{ from: string; to: string; w?: number; weight?: number; support?: boolean }>;
}

export const EMBEDDED = {
  "sid": "d0e0b2e7-3faf-46db-b6bb-a81b8415dba1",
  "role": "Senior Python Backend Engineer",
  "verdict": "borderline",
  "composite": 6.69,
  "confidence": 0.69,
  "coverage": 0.68,
  "difficulty_reached": 5,
  "evidence_total": 15,
  "hypothesis_outcomes": {
    "confirmed": 9,
    "refuted": 2,
    "unanswered": 1
  },
  "sufficiency": {
    "severity": "sufficient",
    "is_sufficient": true,
    "remaining_gaps": 2,
    "coverage": 0.68,
    "details": {
      "tech_caching": {
        "gap": 1.0,
        "weight": 1.5,
        "covered": false,
        "average_score": 0.0,
        "evidence_count": 0
      },
      "tech_deployment": {
        "gap": 0.0,
        "weight": 2.5,
        "covered": true,
        "average_score": 8.5,
        "evidence_count": 2
      },
      "tech_event_driven": {
        "gap": 0.0,
        "weight": 2.0,
        "covered": true,
        "average_score": 8.5,
        "evidence_count": 4
      },
      "tech_data_modeling": {
        "gap": 1.0,
        "weight": 2.0,
        "covered": false,
        "average_score": 0.0,
        "evidence_count": 0
      },
      "tech_system_design": {
        "gap": 0.0,
        "weight": 3.0,
        "covered": true,
        "average_score": 8.33,
        "evidence_count": 3
      }
    }
  },
  "phases": [
    {
      "n": 1,
      "phase": "intro",
      "difficulty": 3,
      "evidence_count": 0
    },
    {
      "n": 2,
      "phase": "intro",
      "difficulty": 3,
      "evidence_count": 1
    },
    {
      "n": 3,
      "phase": "technical",
      "difficulty": 3,
      "evidence_count": 2
    },
    {
      "n": 4,
      "phase": "technical",
      "difficulty": 3,
      "evidence_count": 3
    },
    {
      "n": 5,
      "phase": "technical",
      "difficulty": 3,
      "evidence_count": 5
    },
    {
      "n": 6,
      "phase": "technical",
      "difficulty": 3,
      "evidence_count": 6
    },
    {
      "n": 7,
      "phase": "technical",
      "difficulty": 4,
      "evidence_count": 7
    },
    {
      "n": 8,
      "phase": "technical",
      "difficulty": 4,
      "evidence_count": 8
    },
    {
      "n": 9,
      "phase": "behavioral",
      "difficulty": 5,
      "evidence_count": 10
    },
    {
      "n": 10,
      "phase": "behavioral",
      "difficulty": 5,
      "evidence_count": 11
    },
    {
      "n": 11,
      "phase": "behavioral",
      "difficulty": 5,
      "evidence_count": 12
    },
    {
      "n": 12,
      "phase": "behavioral",
      "difficulty": 5,
      "evidence_count": 13
    },
    {
      "n": 13,
      "phase": "behavioral",
      "difficulty": 5,
      "evidence_count": 14
    },
    {
      "n": 14,
      "phase": "conclusion",
      "difficulty": 5,
      "evidence_count": 15
    },
    {
      "n": 14,
      "phase": "conclusion",
      "difficulty": 5,
      "evidence_count": 15
    }
  ],
  "competencies": [
    {
      "id": "tech_core",
      "avg": 8.67,
      "count": 3,
      "gap": 1,
      "scores": [
        8.5,
        8.5,
        9
      ]
    },
    {
      "id": "tech_deployment",
      "avg": 8.5,
      "count": 2,
      "gap": 1,
      "scores": [
        8.5,
        8.5
      ]
    },
    {
      "id": "tech_event_driven",
      "avg": 8.5,
      "count": 4,
      "gap": 1,
      "scores": [
        8,
        8,
        9,
        9
      ]
    },
    {
      "id": "tech_system_design",
      "avg": 8.33,
      "count": 3,
      "gap": 1,
      "scores": [
        8,
        9,
        8
      ]
    },
    {
      "id": "behav_communication",
      "avg": 8.17,
      "count": 3,
      "gap": 1,
      "scores": [
        8,
        8,
        8.5
      ]
    }
  ],
  "hypotheses": [
    {
      "id": "d4ca2aff-93e3-4a0d-a4d5-d9c6b7147f50",
      "status": "confirmed",
      "confidence": 1,
      "competency": "tech_core",
      "statement": "Candidate has strong strong technical depth in Python and related technologies",
      "evidence": 9,
      "required": 3
    },
    {
      "id": "3eb0521f-372a-4fc6-987f-e543d37c0255",
      "status": "confirmed",
      "confidence": 1,
      "competency": "tech_core",
      "statement": "Candidate has strong experience with scalable system tools like Docker and Kubernetes",
      "evidence": 5,
      "required": 3
    },
    {
      "id": "d013bd61-cd67-4aa9-aa24-f924a77bc5b8",
      "status": "refuted",
      "confidence": 0.02,
      "competency": "tech_core",
      "statement": "Candidate is weak in limited testing exposure",
      "evidence": 3,
      "required": 3
    },
    {
      "id": "0ef5436c-19c6-4eeb-8ce2-7d26556d6e6d",
      "status": "refuted",
      "confidence": 0.02,
      "competency": "tech_core",
      "statement": "Candidate is weak in potentially limited experience with agile development or CI/CD due to lack of specific mentions",
      "evidence": 3,
      "required": 3
    },
    {
      "id": "2b3128d7-8bf2-433c-886c-b1823efd97c7",
      "status": "confirmed",
      "confidence": 0.98,
      "competency": "tech_core",
      "statement": "Candidate has strong python skills for this role",
      "evidence": 3,
      "required": 3
    },
    {
      "id": "dc368d9a-2417-4e68-946b-37088b8f3548",
      "status": "confirmed",
      "confidence": 0.99,
      "competency": "behav_communication",
      "statement": "Candidate communicates clearly and effectively",
      "evidence": 4,
      "required": 3
    },
    {
      "id": "0bc9a2b1-6721-422d-a0ff-13ad6687e7ad",
      "status": "confirmed",
      "confidence": 0.98,
      "competency": "tech_system_design",
      "statement": "Candidate demonstrates System Design & Scalability",
      "evidence": 4,
      "required": 2
    },
    {
      "id": "c79ec838-79af-4edd-a95a-02a2e3b05ab8",
      "status": "confirmed",
      "confidence": 0.82,
      "competency": "tech_system_design",
      "statement": "Candidate demonstrates System Design & Scalability",
      "evidence": 2,
      "required": 2
    },
    {
      "id": "d1920647-0a3c-49ca-943a-844768487d14",
      "status": "confirmed",
      "confidence": 0.93,
      "competency": "tech_deployment",
      "statement": "Candidate demonstrates Reliable Deployments & AWS",
      "evidence": 2,
      "required": 2
    },
    {
      "id": "595d37c4-3f09-4367-9ff4-d08b1ef97c2e",
      "status": "confirmed",
      "confidence": 0.99,
      "competency": "tech_event_driven",
      "statement": "Candidate demonstrates Event-Driven Processing & Kafka",
      "evidence": 4,
      "required": 1
    },
    {
      "id": "9b5cb423-2069-41b1-805b-d54267758fad",
      "status": "confirmed",
      "confidence": 0.96,
      "competency": "tech_event_driven",
      "statement": "Candidate demonstrates Event-Driven Processing & Kafka",
      "evidence": 2,
      "required": 1
    },
    {
      "id": "132ade6d-91a5-43a2-9304-6c106980fde9",
      "status": "untested",
      "confidence": 0.5,
      "competency": "tech_event_driven",
      "statement": "Candidate demonstrates Event-Driven Processing & Kafka",
      "evidence": 0,
      "required": 1
    }
  ],
  "graph_edges": [
    {
      "from": "04fbfc15-fa65-4c66-a516-60584f269b95",
      "to": "595d37c4-3f09-4367-9ff4-d08b1ef97c2e",
      "w": 0.85,
      "support": true
    },
    {
      "from": "18eb4495-8d3a-4259-be84-5085e0f50ca5",
      "to": "0bc9a2b1-6721-422d-a0ff-13ad6687e7ad",
      "w": 0.4,
      "support": true
    },
    {
      "from": "18eb4495-8d3a-4259-be84-5085e0f50ca5",
      "to": "3eb0521f-372a-4fc6-987f-e543d37c0255",
      "w": 0.4,
      "support": true
    },
    {
      "from": "18eb4495-8d3a-4259-be84-5085e0f50ca5",
      "to": "c79ec838-79af-4edd-a95a-02a2e3b05ab8",
      "w": 0.4,
      "support": true
    },
    {
      "from": "18eb4495-8d3a-4259-be84-5085e0f50ca5",
      "to": "d4ca2aff-93e3-4a0d-a4d5-d9c6b7147f50",
      "w": 0.7,
      "support": true
    },
    {
      "from": "18eb4495-8d3a-4259-be84-5085e0f50ca5",
      "to": "dc368d9a-2417-4e68-946b-37088b8f3548",
      "w": 0.85,
      "support": true
    },
    {
      "from": "26926639-bb99-4085-9bd7-df02270af36d",
      "to": "0bc9a2b1-6721-422d-a0ff-13ad6687e7ad",
      "w": 0.85,
      "support": true
    },
    {
      "from": "26926639-bb99-4085-9bd7-df02270af36d",
      "to": "c79ec838-79af-4edd-a95a-02a2e3b05ab8",
      "w": 0.85,
      "support": true
    },
    {
      "from": "32f84a5c-2f9c-456c-8a0e-62e48407c636",
      "to": "0ef5436c-19c6-4eeb-8ce2-7d26556d6e6d",
      "w": 0.85,
      "support": false
    },
    {
      "from": "32f84a5c-2f9c-456c-8a0e-62e48407c636",
      "to": "2b3128d7-8bf2-433c-886c-b1823efd97c7",
      "w": 0.85,
      "support": true
    },
    {
      "from": "32f84a5c-2f9c-456c-8a0e-62e48407c636",
      "to": "3eb0521f-372a-4fc6-987f-e543d37c0255",
      "w": 0.85,
      "support": true
    },
    {
      "from": "32f84a5c-2f9c-456c-8a0e-62e48407c636",
      "to": "d013bd61-cd67-4aa9-aa24-f924a77bc5b8",
      "w": 0.85,
      "support": false
    },
    {
      "from": "32f84a5c-2f9c-456c-8a0e-62e48407c636",
      "to": "d4ca2aff-93e3-4a0d-a4d5-d9c6b7147f50",
      "w": 0.85,
      "support": true
    },
    {
      "from": "64fd68a5-2dae-43f7-9ebb-6d33eb59c018",
      "to": "0bc9a2b1-6721-422d-a0ff-13ad6687e7ad",
      "w": 0.85,
      "support": true
    },
    {
      "from": "64fd68a5-2dae-43f7-9ebb-6d33eb59c018",
      "to": "d4ca2aff-93e3-4a0d-a4d5-d9c6b7147f50",
      "w": 0.7,
      "support": true
    },
    {
      "from": "693823f3-154c-4f7d-ae8a-fe58e5114b43",
      "to": "0ef5436c-19c6-4eeb-8ce2-7d26556d6e6d",
      "w": 0.85,
      "support": false
    },
    {
      "from": "693823f3-154c-4f7d-ae8a-fe58e5114b43",
      "to": "2b3128d7-8bf2-433c-886c-b1823efd97c7",
      "w": 0.85,
      "support": true
    },
    {
      "from": "693823f3-154c-4f7d-ae8a-fe58e5114b43",
      "to": "3eb0521f-372a-4fc6-987f-e543d37c0255",
      "w": 0.85,
      "support": true
    },
    {
      "from": "693823f3-154c-4f7d-ae8a-fe58e5114b43",
      "to": "d013bd61-cd67-4aa9-aa24-f924a77bc5b8",
      "w": 0.85,
      "support": false
    },
    {
      "from": "693823f3-154c-4f7d-ae8a-fe58e5114b43",
      "to": "d4ca2aff-93e3-4a0d-a4d5-d9c6b7147f50",
      "w": 0.85,
      "support": true
    },
    {
      "from": "6b8fea85-46a2-4c60-8601-6cfe4947dca2",
      "to": "d1920647-0a3c-49ca-943a-844768487d14",
      "w": 0.85,
      "support": true
    },
    {
      "from": "9657f4fd-43a1-42d8-a5e4-8ed20f2597c6",
      "to": "dc368d9a-2417-4e68-946b-37088b8f3548",
      "w": 0.85,
      "support": true
    },
    {
      "from": "a060e5a0-16ae-4b22-a968-a05b7fd29227",
      "to": "595d37c4-3f09-4367-9ff4-d08b1ef97c2e",
      "w": 0.85,
      "support": true
    },
    {
      "from": "a060e5a0-16ae-4b22-a968-a05b7fd29227",
      "to": "9b5cb423-2069-41b1-805b-d54267758fad",
      "w": 0.85,
      "support": true
    },
    {
      "from": "a060e5a0-16ae-4b22-a968-a05b7fd29227",
      "to": "d4ca2aff-93e3-4a0d-a4d5-d9c6b7147f50",
      "w": 0.7,
      "support": true
    },
    {
      "from": "c1c1fd41-b6f4-4ac4-adb9-bde00a53e5eb",
      "to": "0bc9a2b1-6721-422d-a0ff-13ad6687e7ad",
      "w": 0.85,
      "support": true
    },
    {
      "from": "c1c1fd41-b6f4-4ac4-adb9-bde00a53e5eb",
      "to": "3eb0521f-372a-4fc6-987f-e543d37c0255",
      "w": 0.45,
      "support": true
    },
    {
      "from": "c1c1fd41-b6f4-4ac4-adb9-bde00a53e5eb",
      "to": "d4ca2aff-93e3-4a0d-a4d5-d9c6b7147f50",
      "w": 0.7,
      "support": true
    },
    {
      "from": "da5bb392-1fcd-4490-a63f-38fae32f6ef5",
      "to": "0ef5436c-19c6-4eeb-8ce2-7d26556d6e6d",
      "w": 0.85,
      "support": false
    },
    {
      "from": "da5bb392-1fcd-4490-a63f-38fae32f6ef5",
      "to": "2b3128d7-8bf2-433c-886c-b1823efd97c7",
      "w": 0.85,
      "support": true
    },
    {
      "from": "da5bb392-1fcd-4490-a63f-38fae32f6ef5",
      "to": "3eb0521f-372a-4fc6-987f-e543d37c0255",
      "w": 0.85,
      "support": true
    },
    {
      "from": "da5bb392-1fcd-4490-a63f-38fae32f6ef5",
      "to": "d013bd61-cd67-4aa9-aa24-f924a77bc5b8",
      "w": 0.85,
      "support": false
    },
    {
      "from": "da5bb392-1fcd-4490-a63f-38fae32f6ef5",
      "to": "d4ca2aff-93e3-4a0d-a4d5-d9c6b7147f50",
      "w": 0.85,
      "support": true
    },
    {
      "from": "dad8d6d2-91c3-41cf-84d8-bc8414a61e83",
      "to": "d4ca2aff-93e3-4a0d-a4d5-d9c6b7147f50",
      "w": 0.7,
      "support": true
    },
    {
      "from": "dad8d6d2-91c3-41cf-84d8-bc8414a61e83",
      "to": "dc368d9a-2417-4e68-946b-37088b8f3548",
      "w": 0.85,
      "support": true
    },
    {
      "from": "e2a6b489-cd86-451e-8ac6-e267c929676b",
      "to": "595d37c4-3f09-4367-9ff4-d08b1ef97c2e",
      "w": 0.85,
      "support": true
    },
    {
      "from": "e54928df-5616-40c4-92bd-ef87cbad7a49",
      "to": "595d37c4-3f09-4367-9ff4-d08b1ef97c2e",
      "w": 0.85,
      "support": true
    },
    {
      "from": "e54928df-5616-40c4-92bd-ef87cbad7a49",
      "to": "9b5cb423-2069-41b1-805b-d54267758fad",
      "w": 0.85,
      "support": true
    },
    {
      "from": "e54928df-5616-40c4-92bd-ef87cbad7a49",
      "to": "d4ca2aff-93e3-4a0d-a4d5-d9c6b7147f50",
      "w": 0.7,
      "support": true
    },
    {
      "from": "ebfc4371-a2ee-4325-9e65-6b5a7a8776e8",
      "to": "d1920647-0a3c-49ca-943a-844768487d14",
      "w": 0.85,
      "support": true
    }
  ]
};
