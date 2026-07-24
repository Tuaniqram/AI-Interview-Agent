import { useState } from 'react';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';
import { candidateService } from '../../services/candidateService';
import { Button } from '../../components/shared/Button';
import { PageHeader } from '../../components/shared/PageHeader';

export default function CandidateProfile() {
  const { candidate, updateProfile: updateContext } = useCandidateAuth();
  const [name, setName] = useState(candidate?.name || '');
  const [phone, setPhone] = useState(candidate?.phone || '');
  const [skills, setSkills] = useState(candidate?.skills || '');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await candidateService.updateProfile({ name, phone: phone || undefined, skills: skills || undefined });
      updateContext(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <PageHeader title="My Profile" description="Manage your candidate profile" />

      <form onSubmit={handleSave} className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)] space-y-4">
        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Email</label>
          <input type="email" value={candidate?.email || ''} disabled className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-secondary)] cursor-not-allowed" />
        </div>
        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Name</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]" />
        </div>
        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Phone</label>
          <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]" />
        </div>
        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Skills</label>
          <textarea value={skills} onChange={(e) => setSkills(e.target.value)} rows={3} placeholder="e.g. Python, React, AWS, System Design" className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]" />
        </div>
        <Button type="submit" loading={saving}>
          {saved ? 'Saved!' : 'Save Changes'}
        </Button>
      </form>
    </div>
  );
}
