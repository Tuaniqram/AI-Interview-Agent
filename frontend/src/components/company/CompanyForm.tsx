import { useState } from 'react';
import { X } from 'lucide-react';

interface CompanyFormProps {
  open: boolean;
  initial?: { name: string; website: string; description: string };
  onSave: (data: { name: string; website: string; description: string }) => void;
  onCancel: () => void;
}

export function CompanyForm({ open, initial, onSave, onCancel }: CompanyFormProps) {
  const [name, setName] = useState(initial?.name || '');
  const [website, setWebsite] = useState(initial?.website || '');
  const [description, setDescription] = useState(initial?.description || '');

  if (!open) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onSave({ name: name.trim(), website: website.trim(), description: description.trim() });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-overlay">
      <div className="bg-elevated rounded-xl shadow-lg max-w-lg w-full mx-4 p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="font-semibold text-primary">{initial ? 'Edit Company' : 'Add Company'}</h3>
          <button onClick={onCancel} className="text-muted hover:text-secondary"><X className="w-4 h-4" /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-secondary mb-1.5">Company Name *</label>
            <input type="text" value={name} onChange={e => setName(e.target.value)} required
              className="w-full px-3 py-2 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus"
              placeholder="e.g. Acme Corp" />
          </div>
          <div>
            <label className="block text-xs font-medium text-secondary mb-1.5">Website</label>
            <input type="url" value={website} onChange={e => setWebsite(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus"
              placeholder="https://acme.com" />
          </div>
          <div>
            <label className="block text-xs font-medium text-secondary mb-1.5">Description</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={3}
              className="w-full px-3 py-2 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus resize-none"
              placeholder="Brief description of the company" />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-action-ghost-text bg-action-ghost-hover rounded-lg hover:bg-action-secondary-hover transition-colors">
              Cancel
            </button>
            <button type="submit"
              className="px-4 py-2 text-sm font-medium text-inverse bg-action-primary rounded-lg hover:bg-action-primary-hover transition-colors">
              {initial ? 'Save Changes' : 'Add Company'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
