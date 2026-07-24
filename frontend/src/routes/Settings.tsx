import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOrg } from '../contexts/OrgContext';
import { PageHeader } from '../components/shared/PageHeader';
import { Card } from '../components/shared/Card';
import { Button } from '../components/shared/Button';
import { orgService } from '../services/orgService';
import { useToast } from '../components/shared/Toast';
import { Building2, Globe, FileText, Save, ArrowRight } from 'lucide-react';

export function Settings() {
  const { activeOrg } = useOrg();
  const navigate = useNavigate();

  const [orgName, setOrgName] = useState('');
  const [orgWebsite, setOrgWebsite] = useState('');
  const [orgDescription, setOrgDescription] = useState('');
  const [savingOrg, setSavingOrg] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (activeOrg) {
      setOrgName(activeOrg.name || '');
      setOrgWebsite((activeOrg as any).website || '');
      setOrgDescription((activeOrg as any).description || '');
    }
  }, [activeOrg]);

  const saveOrgProfile = async () => {
    if (!activeOrg?.id) return;
    setSavingOrg(true);
    try {
      const updated = await orgService.update(activeOrg.id, {
        name: orgName,
        website: orgWebsite || undefined,
        description: orgDescription || undefined,
      });
      if (updated?.name) setOrgName(updated.name);
      toast.success('Organization profile saved');
    } catch (err) {
      toast.error('Failed to save organization profile');
    } finally {
      setSavingOrg(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-6">
      <PageHeader title="Settings" description="Organization settings" />

      {/* Org Profile */}
      <Card padding="lg">
        <h3 className="text-sm font-semibold text-primary mb-1 flex items-center gap-2">
          <Building2 className="w-4 h-4 text-action-primary" /> Organization Profile
        </h3>
        <p className="text-xs text-muted mb-4">Update your organization's public information</p>
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-secondary mb-1.5">Organization Name</label>
            <input type="text" value={orgName} onChange={e => setOrgName(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-input text-primary rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)]" />
          </div>
          <div>
            <label className="block text-xs font-medium text-secondary mb-1.5 flex items-center gap-1.5">
              <Globe className="w-3 h-3" /> Website
            </label>
            <input type="url" value={orgWebsite} onChange={e => setOrgWebsite(e.target.value)}
              placeholder="https://example.com"
              className="w-full px-3 py-2 text-sm bg-input text-primary rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)]" />
          </div>
          <div>
            <label className="block text-xs font-medium text-secondary mb-1.5 flex items-center gap-1.5">
              <FileText className="w-3 h-3" /> Description
            </label>
            <textarea value={orgDescription} onChange={e => setOrgDescription(e.target.value)} rows={3}
              placeholder="Tell candidates about your organization..."
              className="w-full px-3 py-2 text-sm bg-input text-primary rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] resize-none" />
          </div>
          <div className="flex justify-end">
            <Button onClick={saveOrgProfile} loading={savingOrg}>
              <Save className="w-4 h-4 mr-1.5" /> Save Profile
            </Button>
          </div>
        </div>
      </Card>

      {/* Marketplace */}
      <Card padding="lg" hover onClick={() => navigate('/departments')}>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-primary mb-1">Marketplace</h3>
            <p className="text-xs text-muted mb-2">Manage your public interview listings</p>
            <p className="text-sm text-secondary">
              Create and manage interview listings from each department's{' '}
              <span className="font-medium text-primary">Interview Listings</span> tab.
            </p>
          </div>
          <ArrowRight className="w-5 h-5 text-muted shrink-0" />
        </div>
      </Card>

      {/* Org ID */}
      {activeOrg?.id && (
        <Card padding="sm">
          <p className="text-xs text-muted font-mono">Org ID: {activeOrg.id}</p>
        </Card>
      )}
    </div>
  );
}
