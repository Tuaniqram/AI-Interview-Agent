import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useOrg } from '../contexts/OrgContext';
import { PageHeader } from '../components/shared/PageHeader';
import { Card } from '../components/shared/Card';
import { Button } from '../components/shared/Button';
import { Input } from '../components/shared/Input';
import { orgService } from '../services/orgService';
import { useToast } from '../components/shared/Toast';
import { Check, Copy } from 'lucide-react';

/** A settings section: what it is on the left, the fields on the right (stacked on narrow screens). */
function Section({ title, text, children }: { title: string; text: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-4 md:grid-cols-[240px_minmax(0,1fr)] md:gap-8 py-8 first:pt-0 last:pb-0 border-b border-border last:border-0">
      <div>
        <h2 className="text-sm font-semibold text-primary">{title}</h2>
        <p className="text-[13px] text-tertiary mt-1">{text}</p>
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  );
}

export function Settings() {
  const { activeOrg } = useOrg();

  const [orgName, setOrgName] = useState('');
  const [orgWebsite, setOrgWebsite] = useState('');
  const [orgDescription, setOrgDescription] = useState('');
  const [savingOrg, setSavingOrg] = useState(false);
  const [copied, setCopied] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (activeOrg) {
      setOrgName(activeOrg.name || '');
      setOrgWebsite((activeOrg as any).website || '');
      setOrgDescription((activeOrg as any).description || '');
    }
  }, [activeOrg]);

  const saveOrgProfile = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!activeOrg?.id) return;
    setSavingOrg(true);
    try {
      const updated = await orgService.update(activeOrg.id, {
        name: orgName,
        website: orgWebsite || undefined,
        description: orgDescription || undefined,
      });
      setOrgName(updated.name || orgName);
      setOrgWebsite((updated as any).website || '');
      setOrgDescription((updated as any).description || '');
      toast.success('Organization profile saved');
    } catch {
      toast.error('Could not save the profile. Try again in a moment.');
    } finally {
      setSavingOrg(false);
    }
  };

  const copyId = async () => {
    if (!activeOrg?.id) return;
    try {
      await navigator.clipboard.writeText(activeOrg.id);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable: the id is still selectable
    }
  };

  return (
    <div className="max-w-4xl">
      <PageHeader title="Settings" description="How your organization appears to candidates." />

      <Card padding="lg">
        <form onSubmit={saveOrgProfile} className="pb-8 border-b border-border">
          <Section title="Organization profile" text="Shown on your Opportunity Hub page and in interview invitations.">
            <div className="space-y-4">
              <Input label="Name" value={orgName} onChange={e => setOrgName(e.target.value)} required />
              <Input label="Website" type="url" value={orgWebsite} onChange={e => setOrgWebsite(e.target.value)} placeholder="https://example.com" />
              <div className="space-y-1.5">
                <label htmlFor="org-description" className="block text-[13px] font-medium text-primary">Description</label>
                <textarea
                  id="org-description"
                  value={orgDescription}
                  onChange={e => setOrgDescription(e.target.value)}
                  rows={4}
                  placeholder="What your organization does, in a sentence or two."
                  className="w-full px-3 py-2 text-[13px] bg-input text-primary rounded-md border border-[var(--border-strong)] shadow-sm hover:border-[var(--text-tertiary)] focus:border-[var(--action-primary)] focus:outline-none focus:ring-[3px] focus:ring-[var(--focus-ring)] placeholder:text-tertiary resize-y"
                />
              </div>
              <div className="flex justify-end pt-1">
                <Button type="submit" loading={savingOrg}>Save profile</Button>
              </div>
            </div>
          </Section>
        </form>

        <Section title="Public listings" text="The interviews candidates can find and apply to.">
          <p className="text-[13px] text-secondary">
            Listings are created and edited on the company page, under Interview listings.
          </p>
          <Link to="/org/company" className="inline-block mt-2 text-[13px] font-medium text-action-primary hover:underline">Open the company page</Link>
        </Section>

        {activeOrg?.id && (
          <Section title="Organization ID" text="The internal identifier for this organization.">
            <div className="flex items-center gap-2">
              <code className="flex-1 min-w-0 truncate h-8 px-3 flex items-center rounded-md bg-subtle border border-border text-[13px] text-secondary tabular">{activeOrg.id}</code>
              <Button type="button" variant="secondary" icon={copied ? <Check /> : <Copy />} onClick={copyId}>{copied ? 'Copied' : 'Copy'}</Button>
            </div>
          </Section>
        )}
      </Card>
    </div>
  );
}
