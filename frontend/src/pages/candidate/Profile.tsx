import { useEffect, useState, useRef } from 'react';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';
import { candidateService } from '../../services/candidateService';
import { Button } from '../../components/shared/Button';
import { Card } from '../../components/shared/Card';
import { Input } from '../../components/shared/Input';
import { PageHeader } from '../../components/shared/PageHeader';
import { ChipInput } from '../../components/shared/ChipInput';
import { useToast } from '../../components/shared/Toast';
import { Upload, FileText, X } from 'lucide-react';

/** A settings section: what it is on the left, the fields on the right (stacked on phones). */
function Section({ title, text, children }: { title: string; text: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-4 md:grid-cols-[240px_minmax(0,1fr)] md:gap-8 py-8 first:pt-0 border-b border-border last:border-0">
      <div>
        <h2 className="text-sm font-semibold text-primary">{title}</h2>
        <p className="text-[13px] text-tertiary mt-1">{text}</p>
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  );
}

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

  // The candidate may load after this page mounts (a fresh page load): fill the fields once it arrives.
  useEffect(() => {
    if (!candidate) return;
    setName(candidate.name || '');
    setPhone(candidate.phone || '');
    setSkills(candidate.skills || '');
  }, [candidate?.id]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await candidateService.updateProfile({ name, phone: phone || undefined, skills: skills || undefined });
      updateContext(updated);
      toast.success('Profile saved');
    } catch {
      toast.error('Could not save your profile. Try again in a moment.');
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
      toast.success('CV uploaded. Your skills were read from it.');
    } catch {
      toast.error('Could not upload the CV. Check it is a PDF and try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-4xl">
      <PageHeader title="Profile" description="What interviewers know about you before the first question." />

      <Card padding="lg">
        <Section title="CV" text="Upload a PDF. Your skills are read from it, and interviews use it to ask about your own experience.">
          <div className="space-y-3">
            {candidate?.resume_url ? (
              <div className="flex items-center gap-3 rounded-lg border border-border bg-subtle px-3 h-11">
                <FileText className="w-4 h-4 text-action-primary shrink-0" />
                <span className="text-[13px] text-primary flex-1 truncate">CV on file</span>
                <span className="text-xs text-tertiary">PDF</span>
              </div>
            ) : (
              <p className="text-[13px] text-secondary">No CV uploaded yet.</p>
            )}
            <input ref={fileRef} type="file" accept=".pdf" onChange={handleFileChange} className="hidden" />
            {selectedFile ? (
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-2 h-8 pl-3 pr-1 rounded-md border border-border text-[13px] text-primary max-w-full">
                  <span className="truncate">{selectedFile.name}</span>
                  <button type="button" onClick={() => setSelectedFile(null)} aria-label="Remove file" className="p-1 rounded text-tertiary hover:text-primary hover:bg-hover">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </span>
                <Button type="button" onClick={handleUpload} loading={uploading}>
                  {uploading ? 'Reading your CV...' : 'Upload'}
                </Button>
              </div>
            ) : (
              <Button type="button" variant="secondary" icon={<Upload />} onClick={() => fileRef.current?.click()}>
                {candidate?.resume_url ? 'Replace CV' : 'Choose a PDF'}
              </Button>
            )}
          </div>
        </Section>

        <form onSubmit={handleSave}>
          <Section title="Details" text="Your name is how the interviewer addresses you.">
            <div className="space-y-4">
              <Input label="Email" type="email" value={candidate?.email || ''} disabled hint="Your sign-in address. It cannot be changed here." />
              <Input label="Name" value={name} onChange={e => setName(e.target.value)} autoComplete="name" />
              <Input label="Phone" type="tel" value={phone} onChange={e => setPhone(e.target.value)} autoComplete="tel" hint="Optional." />
            </div>
          </Section>

          <Section title="Skills" text="Filled in from your CV. Add or remove any of them.">
            <ChipInput value={skills} onChange={setSkills} placeholder="Type a skill and press Enter" />
            <p className="text-xs text-tertiary mt-1.5">Press Enter or a comma to add a skill.</p>
            <div className="mt-6 flex justify-end">
              <Button type="submit" loading={saving}>Save changes</Button>
            </div>
          </Section>
        </form>
      </Card>
    </div>
  );
}
