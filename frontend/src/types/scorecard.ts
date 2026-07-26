export interface CompetencyDef {
  id: string;
  name: string;
  category: string;
  weight: number;
  max_score: number;
}

export interface ScorecardTemplate {
  id: string;
  org_id: string;
  name: string;
  competencies: CompetencyDef[];
  created_at: string | null;
  updated_at: string | null;
}

export interface ScorecardResult {
  id: string;
  session_id: string;
  template_id: string | null;
  scores: Record<string, {
    raw_avg: number;
    normalized: number;
    weight: number;
    weighted: number;
    evidence_count: number;
  }>;
  weighted_score: number | null;
  created_at: string | null;
}
