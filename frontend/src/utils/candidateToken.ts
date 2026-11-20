export function getCandidateToken(): string | null {
  try {
    const stored = localStorage.getItem('candidate_tokens');
    if (stored) {
      const tokens = JSON.parse(stored);
      return tokens.access_token || null;
    }
  } catch {
    /* ignore */
  }
  return null;
}
