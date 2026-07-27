import { useState, useRef } from 'react';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';
import { candidateService } from '../../services/candidateService';
import { Button } from '../../components/shared/Button';
import { PageHeader } from '../../components/shared/PageHeader';
import { ChipInput } from '../../components/shared/ChipInput';
import { useToast } from '../../components/shared/Toast';
import { Upload, FileText, X } from 'lucide-react';

export default function CandidateProfile() {
  const { candidate, updateProfile: updateContext } = useCandidateAuth();
  const [name, setName] = useState(candidate?.name || '');
  const [phone, setPhone] = useState(candidate?.phone || '');
  const [skills, setSkills] = useState(candidate?.skills || '');
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await candidateService.updateProfile({ name, phone: phone || undefined, skills: skills || undefined });
      updateContext(updated);
      toast.success('Profile saved');
    } catch (err) {
      toast.error('Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    try {
      const updated = await candidateService.uploadResume(selectedFile);
      updateContext(updated);
      setSelectedFile(null);
      setSkills(updated.skills || '');
      toast.success('Resume uploaded and parsed successfully');
    } catch (err) {
      toast.error('Failed to upload resume');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <PageHeader title="My Profile" description="Manage your candidate profile" />

      {/* Resume Upload */}
      <div className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)] space-y-4">
        <h3 className="text-base font-semibold text-[var(--text-primary)]">Resume</h3>
        {candidate?.resume_url ? (
          <div className="flex items-center gap-3 p-3 rounded-lg bg-[var(--bg-page)] border border-[var(--border-color)]">
            <FileText className="w-5 h-5 text-[var(--action-primary)]" />
            <span className="text-sm text-[var(--text-primary)] flex-1 truncate">Resume uploaded</span>
            <span className="text-xs text-[var(--text-muted)]">PDF</span>
          </div>
        ) : (
          <p className="text-sm text-[var(--text-muted)]">No resume uploaded yet. Upload a PDF to auto-extract your skills.</p>
        )}
        <div className="flex items-center gap-3">
          <input ref={fileRef} type="file" accept=".pdf" onChange={handleFileChange} className="hidden" />
          <Button type="button" variant="secondary" onClick={() => fileRef.current?.click()}>
            <Upload className="w-4 h-4 mr-1" />
            Choose File
          </Button>
          {selectedFile && (
            <div className="flex items-center gap-2 flex-1">
              <span className="text-sm text-[var(--text-primary)] truncate">{selectedFile.name}</span>
              <button onClick={() => setSelectedFile(null)} className="text-[var(--text-muted)] hover:text-[var(--text-primary)]">
                <X className="w-4 h-4" />
              </button>
              <Button type="button" size="sm" onClick={handleUpload} loading={uploading}>
                {uploading ? 'Parsing...' : 'Upload & Parse'}
              </Button>
            </div>
          )}
        </div>
      </div>

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
          <ChipInput value={skills} onChange={setSkills} placeholder="Type a skill and press Enter" />
          <p className="text-xs text-[var(--text-muted)] mt-1">Press Enter or comma to add a skill. Click &times; to remove.</p>
        </div>
        <Button type="submit" loading={saving}>
          Save Changes
        </Button>
      </form>
    </div>
  );
}
