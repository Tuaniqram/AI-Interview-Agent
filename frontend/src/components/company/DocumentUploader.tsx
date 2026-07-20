import { useState, useRef } from 'react';
import { Upload, Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import { apiClient } from '../../services/apiClient';

interface DocumentUploaderProps {
  companyId: number;
  onUploaded: () => void;
}

export function DocumentUploader({ companyId, onUploaded }: DocumentUploaderProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    setSuccess(false);

    try {
      const formData = new FormData();
      formData.append('file', file);
      const result = await apiClient.post<{
        message: string;
        warning?: string;
        chunks?: number;
      }>(`/companies/${companyId}/knowledge`, formData);

      if (result.warning) {
        setError(result.warning);
      } else {
        setSuccess(true);
        setTimeout(() => setSuccess(false), 3000);
      }

      onUploaded();
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || 'Upload failed. Please try again.';
      setError(message);
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-2">
      <input ref={inputRef} type="file" accept=".pdf,.doc,.docx,.txt,.md" onChange={handleFile} className="hidden" />
      <button
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
        className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-inverse bg-action-primary rounded-lg hover:bg-action-primary-hover active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed transition-all"
      >
        {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
        {uploading ? 'Uploading...' : 'Upload Document'}
      </button>
      {error && (
        <div className="flex items-center gap-1.5 text-xs text-warning-text bg-warning-bg px-3 py-2 rounded-lg">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="flex items-center gap-1.5 text-xs text-success-text bg-success-bg px-3 py-2 rounded-lg">
          <CheckCircle className="w-3.5 h-3.5 shrink-0" />
          <span>Document uploaded successfully</span>
        </div>
      )}
    </div>
  );
}
