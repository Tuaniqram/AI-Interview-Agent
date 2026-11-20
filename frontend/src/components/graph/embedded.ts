export interface EmbeddedBrain {
  sid: string; role: string; verdict: string; composite: number; confidence: number; coverage: number;
  difficulty_reached: number; evidence_total: number;
  hypothesis_outcomes?: Record<string, number>;
  sufficiency?: { severity?: string; is_sufficient?: boolean; remaining_gaps?: number; coverage?: number; details?: Record<string, any> };
  phases: Array<{ n: number; phase: string; difficulty: number; evidence_count: number }>;
  competencies: Array<{ id: string; avg: number; count: number; gap: number; scores: number[] }>;
  hypotheses: Array<Record<string, unknown>>;
  graph_edges: Array<{ from: string; to: string; w?: number; weight?: number; support?: boolean }>;
}

export const EMBEDDED: EmbeddedBrain = {
  "sid": "9f025266-26b8-4cbe-8b8c-b883c5436eea",
  "role": "Senior Backend Engineer",
  "verdict": "hire",
  "composite": 8.55,
  "confidence": 0.71,
  "coverage": 0.86,
  "difficulty_reached": 3,
  "evidence_total": 13,
  "hypothesis_outcomes": {
    "confirmed": 5,
    "testing": 3,
    "refuted": 0,
    "unanswered": 6
  },
  "sufficiency": {
    "severity": "sufficient",
    "is_sufficient": false,
    "remaining_gaps": 1,
    "coverage": 0.86,
    "details": {
      "tech_caching": {
        "gap": 0.0,
        "weight": 1.5,
        "covered": false,
        "average_score": 8.0,
        "evidence_count": 1
      },
      "tech_deployment": {
        "gap": 0.0,
        "weight": 2.5,
        "covered": true,
        "average_score": 6.67,
        "evidence_count": 3
      },
      "tech_event_driven": {
        "gap": 0.0,
        "weight": 2.0,
        "covered": true,
        "average_score": 8.17,
        "evidence_count": 3
      },
      "tech_data_modeling": {
        "gap": 0.0,
        "weight": 2.0,
        "covered": true,
        "average_score": 7.5,
        "evidence_count": 3
      },
      "tech_system_design": {
        "gap": 0.0,
        "weight": 3.0,
        "covered": true,
        "average_score": 8.0,
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
      "evidence_count": 4
    },
    {
      "n": 6,
      "phase": "technical",
      "difficulty": 3,
      "evidence_count": 5
    },
    {
      "n": 7,
      "phase": "technical",
      "difficulty": 4,
      "evidence_count": 6
    },
    {
      "n": 8,
      "phase": "technical",
      "difficulty": 5,
      "evidence_count": 7
    },
    {
      "n": 9,
      "phase": "behavioral",
      "difficulty": 5,
      "evidence_count": 8
    },
    {
      "n": 10,
      "phase": "behavioral",
      "difficulty": 5,
      "evidence_count": 9
    },
    {
      "n": 11,
      "phase": "behavioral",
      "difficulty": 4,
      "evidence_count": 10
    },
    {
      "n": 12,
      "phase": "behavioral",
      "difficulty": 3,
      "evidence_count": 11
    },
    {
      "n": 13,
      "phase": "behavioral",
      "difficulty": 3,
      "evidence_count": 12
    },
    {
      "n": 14,
      "phase": "conclusion",
      "difficulty": 3,
      "evidence_count": 13
    },
    {
      "n": 14,
      "phase": "conclusion",
      "difficulty": 3,
      "evidence_count": 13
    }
  ],
  "competencies": [
    {
      "id": "tech_caching",
      "avg": 8.0,
      "count": 1,
      "gap": 0.0,
      "scores": [
        8.0
      ]
    },
    {
      "id": "tech_deployment",
      "avg": 6.67,
      "count": 3,
      "gap": 0.0,
      "scores": [
        8.0,
        4.0,
        8.0
      ]
    },
    {
      "id": "tech_event_driven",
      "avg": 8.17,
      "count": 3,
      "gap": 0.0,
      "scores": [
        8.0,
        8.5,
        8.0
      ]
    },
    {
      "id": "tech_data_modeling",
      "avg": 7.5,
      "count": 3,
      "gap": 0.0,
      "scores": [
        9.0,
        8.5,
        5.0
      ]
    },
    {
      "id": "tech_system_design",
      "avg": 8.0,
      "count": 3,
      "gap": 0.0,
      "scores": [
        8.0,
        8.0,
        8.0
      ]
    }
  ],
  "hypotheses": [
    {
      "id": "0e6dbaee-5438-4f29-8037-89681a1edd3b",
      "status": "confirmed",
      "confidence": 0.93,
      "competency": "tech_core",
      "statement": "Candidate has strong strong technical depth in Python and FastAPI",
      "evidence": 3,
      "required": 3
    },
    {
      "id": "9cb04c09-733b-4acd-97ac-199b23bc9dc4",
      "status": "untested",
      "confidence": 0.5,
      "competency": "tech_core",
      "statement": "Candidate is weak in limited testing exposure and version control experience",
      "evidence": 0,
      "required": 3
    },
    {
      "id": "2dc8ab5a-9f57-42b4-832f-aabb2fefb2ac",
      "status": "untested",
      "confidence": 0.5,
      "competency": "tech_core",
      "statement": "Candidate has strong backend skills for this role",
      "evidence": 0,
      "required": 3
    },
    {
      "id": "bd02fc5e-6238-4194-9ebd-325bf2ceda43",
      "status": "untested",
      "confidence": 0.5,
      "competency": "tech_core",
      "statement": "Candidate demonstrates Core Language Proficiency",
      "evidence": 0,
      "required": 3
    },
    {
      "id": "bb56d771-fe8c-4d23-80fe-cad740f66c78",
      "status": "untested",
      "confidence": 0.5,
      "competency": "tech_framework",
      "statement": "Candidate demonstrates Framework & Library Knowledge",
      "evidence": 0,
      "required": 3
    },
    {
      "id": "5bb4c737-0cbf-42c5-a095-98295097e894",
      "status": "untested",
      "confidence": 0.5,
      "competency": "behav_communication",
      "statement": "Candidate communicates clearly and effectively",
      "evidence": 0,
      "required": 3
    },
    {
      "id": "cd95b26c-07b3-4944-9d81-285ed745c780",
      "status": "confirmed",
      "confidence": 0.96,
      "competency": "tech_system_design",
      "statement": "Candidate demonstrates System Design & Scalability",
      "evidence": 3,
      "required": 2
    },
    {
      "id": "f03d00f0-5268-4595-bbcc-31608bd99126",
      "status": "testing",
      "confidence": 0.74,
      "competency": "tech_system_design",
      "statement": "Candidate demonstrates System Design & Scalability",
      "evidence": 1,
      "required": 2
    },
    {
      "id": "6b5234ba-047f-4dd2-8eca-4e4e1836ea90",
      "status": "confirmed",
      "confidence": 0.85,
      "competency": "tech_deployment",
      "statement": "Candidate demonstrates Reliable Deployments & AWS",
      "evidence": 3,
      "required": 2
    },
    {
      "id": "155dd71e-86f0-4bf3-b08c-e69b7829e5be",
      "status": "confirmed",
      "confidence": 0.96,
      "competency": "tech_event_driven",
      "statement": "Candidate demonstrates Event-Driven Processing & Kafka",
      "evidence": 3,
      "required": 1
    },
    {
      "id": "7feeb809-088e-4743-992d-7c3d13cd864d",
      "status": "confirmed",
      "confidence": 0.94,
      "competency": "tech_data_modeling",
      "statement": "Candidate demonstrates PostgreSQL Data Modeling & SQLAlchemy",
      "evidence": 4,
      "required": 2
    },
    {
      "id": "29002272-394d-45bb-9497-7edd5edc99ee",
      "status": "testing",
      "confidence": 0.74,
      "competency": "tech_caching",
      "statement": "Candidate demonstrates Caching & Redis",
      "evidence": 1,
      "required": 1
    },
    {
      "id": "287cda39-66e1-41ed-b96e-9628e4a1802d",
      "status": "testing",
      "confidence": 0.74,
      "competency": "tech_event_driven",
      "statement": "Candidate demonstrates Event-Driven Processing & Kafka",
      "evidence": 1,
      "required": 1
    },
    {
      "id": "9cc3e4d6-95ae-479c-841f-342f5435ddf8",
      "status": "untested",
      "confidence": 0.5,
      "competency": "tech_data_modeling",
      "statement": "Candidate demonstrates PostgreSQL Data Modeling & SQLAlchemy",
      "evidence": 2,
      "required": 2
    }
  ],
  "graph_edges": [
    {
      "from": "19437a26-1a84-45ce-ac3c-214d3a752fb6",
      "to": "0e6dbaee-5438-4f29-8037-89681a1edd3b",
      "w": 0.7,
      "support": true
    },
    {
      "from": "19437a26-1a84-45ce-ac3c-214d3a752fb6",
      "to": "cd95b26c-07b3-4944-9d81-285ed745c780",
      "w": 0.85,
      "support": true
    },
    {
      "from": "19437a26-1a84-45ce-ac3c-214d3a752fb6",
      "to": "f03d00f0-5268-4595-bbcc-31608bd99126",
      "w": 0.85,
      "support": true
    },
    {
      "from": "21951193-4827-41ff-a9dc-38ad86eb9d7e",
      "to": "6b5234ba-047f-4dd2-8eca-4e4e1836ea90",
      "w": 0.85,
      "support": true
    },
    {
      "from": "49836ca7-42fa-4de5-adf3-6ca5f5cfc782",
      "to": "6b5234ba-047f-4dd2-8eca-4e4e1836ea90",
      "w": 0.85,
      "support": false
    },
    {
      "from": "4c748ca0-1505-4364-a698-b49d4b6e8e64",
      "to": "0e6dbaee-5438-4f29-8037-89681a1edd3b",
      "w": 0.7,
      "support": true
    },
    {
      "from": "4c748ca0-1505-4364-a698-b49d4b6e8e64",
      "to": "155dd71e-86f0-4bf3-b08c-e69b7829e5be",
      "w": 0.85,
      "support": true
    },
    {
      "from": "4c748ca0-1505-4364-a698-b49d4b6e8e64",
      "to": "287cda39-66e1-41ed-b96e-9628e4a1802d",
      "w": 0.85,
      "support": true
    },
    {
      "from": "84d21c51-6e49-475f-939d-3f8d931af491",
      "to": "7feeb809-088e-4743-992d-7c3d13cd864d",
      "w": 0.85,
      "support": true
    },
    {
      "from": "84d21c51-6e49-475f-939d-3f8d931af491",
      "to": "9cc3e4d6-95ae-479c-841f-342f5435ddf8",
      "w": 0.85,
      "support": true
    },
    {
      "from": "9bfbea61-7790-4872-97ee-11b9edabc836",
      "to": "7feeb809-088e-4743-992d-7c3d13cd864d",
      "w": 0.85,
      "support": true
    },
    {
      "from": "b7843cb0-c861-4e42-afe6-70ac9ade0771",
      "to": "155dd71e-86f0-4bf3-b08c-e69b7829e5be",
      "w": 0.85,
      "support": true
    },
    {
      "from": "ba08e580-7015-4401-8ea1-477b78edad58",
      "to": "0e6dbaee-5438-4f29-8037-89681a1edd3b",
      "w": 0.7,
      "support": true
    },
    {
      "from": "ba08e580-7015-4401-8ea1-477b78edad58",
      "to": "29002272-394d-45bb-9497-7edd5edc99ee",
      "w": 0.85,
      "support": true
    },
    {
      "from": "c80f10c4-a83e-44f5-9bea-cd9cbfd92636",
      "to": "cd95b26c-07b3-4944-9d81-285ed745c780",
      "w": 0.85,
      "support": true
    },
    {
      "from": "d3d1400a-6f85-4e9a-8bfa-bf7ac40be877",
      "to": "155dd71e-86f0-4bf3-b08c-e69b7829e5be",
      "w": 0.85,
      "support": true
    },
    {
      "from": "e83e285a-3b50-4d70-bd70-27c83c2bcf70",
      "to": "7feeb809-088e-4743-992d-7c3d13cd864d",
      "w": 0.85,
      "support": true
    },
    {
      "from": "e8f996cc-9133-4d0d-880b-8c724bc1860b",
      "to": "cd95b26c-07b3-4944-9d81-285ed745c780",
      "w": 0.85,
      "support": true
    },
    {
      "from": "fecfd1fa-7172-4ea6-a5d8-be6d8cac7f3d",
      "to": "6b5234ba-047f-4dd2-8eca-4e4e1836ea90",
      "w": 0.85,
      "support": true
    }
  ]
};
