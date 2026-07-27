import { useState, useRef } from 'react';
import { Upload, Loader2 } from 'lucide-react';
import { departmentService } from '../../services/departmentService';
import { useToast } from '../shared/Toast';

interface DocumentUploaderProps {
  departmentId: number;
  onUploaded: () => void;
}

export function DocumentUploader({ departmentId, onUploaded }: DocumentUploaderProps) {
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);

    try {
      await departmentService.uploadDocument(departmentId, file);
      toast.success('Document uploaded successfully');
      onUploaded();
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || 'Upload failed';
      toast.error(message);
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
    </div>
  );
}
