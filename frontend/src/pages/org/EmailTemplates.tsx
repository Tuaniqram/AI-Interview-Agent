import { useEffect, useState } from 'react';
import { useOrg } from '../../contexts/OrgContext';
import { apiClient } from '../../services/apiClient';
import { PageHeader } from '../../components/shared/PageHeader';
import { Card } from '../../components/shared/Card';
import { Button } from '../../components/shared/Button';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { EmptyState } from '../../components/shared/EmptyState';
import { useToast } from '../../components/shared/Toast';
import { FileText, Save } from 'lucide-react';

export default function EmailTemplates() {
  const { activeOrg } = useOrg();
  const toast = useToast();
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<any>(null);
  const [content, setContent] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!activeOrg?.id) return;
    setLoading(true);
    apiClient.get<any[]>(`/api/v1/orgs/${activeOrg.id}/email-templates`)
      .then(setTemplates)
      .catch(() => toast.error('Failed to load templates'))
      .finally(() => setLoading(false));
  }, [activeOrg?.id]);

  const openTemplate = async (t: any) => {
    try {
      const data = await apiClient.get<any>(`/api/v1/orgs/${activeOrg!.id}/email-templates/${t.name}`);
      setSelected(data);
      setContent(data.content || '');
    } catch {
      toast.error('Failed to load template content');
    }
  };

  const handleSave = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      await apiClient.put(`/api/v1/orgs/${activeOrg!.id}/email-templates/${selected.name}`, { content });
      toast.success('Template saved');
    } catch {
      toast.error('Failed to save template');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <PageHeader title="Email Templates" description="Edit email notification templates" />

      <div className="grid grid-cols-4 gap-4">
        <div className="col-span-1 space-y-1">
          {templates.length === 0 ? (
            <EmptyState title="No templates" description="" />
          ) : (
            templates.map(t => (
              <button key={t.name} onClick={() => openTemplate(t)}
                className={`w-full flex items-center gap-2 p-2 rounded-lg text-xs text-left transition-colors ${
                  selected?.name === t.name ? 'bg-action-primary/10 text-action-primary' : 'text-secondary hover:bg-hover'
                }`}>
                <FileText className="w-3.5 h-3.5" />
                <span className="truncate">{t.name}</span>
              </button>
            ))
          )}
        </div>
        <div className="col-span-3">
          {selected ? (
            <Card padding="lg" className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-primary">{selected.name}</h3>
                <Button size="sm" onClick={handleSave} loading={saving}>
                  <Save className="w-3.5 h-3.5 mr-1" /> Save
                </Button>
              </div>
              <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={25}
                className="w-full px-3 py-2 text-sm font-mono bg-page text-primary rounded-lg border border-border resize-y" />
            </Card>
          ) : (
            <EmptyState title="Select a template" description="Choose a template from the left to edit its HTML content" />
          )}
        </div>
      </div>
    </div>
  );
}
