import { useState } from 'react';
import { Bookmark } from 'lucide-react';
import { candidateService } from '../../services/candidateService';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';
import { useToast } from '../shared/Toast';

interface BookmarkButtonProps {
  listingId: number;
  initiallySaved?: boolean;
  onToggle?: (saved: boolean) => void;
}

export function BookmarkButton({ listingId, initiallySaved = false, onToggle }: BookmarkButtonProps) {
  const { isAuthenticated } = useCandidateAuth();
  const toast = useToast();
  const [saved, setSaved] = useState(initiallySaved);
  const [loading, setLoading] = useState(false);

  if (!isAuthenticated) return null;

  const handleClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setLoading(true);
    try {
      if (saved) {
        await candidateService.unsaveListing(listingId);
        setSaved(false);
        onToggle?.(false);
      } else {
        await candidateService.saveListing(listingId);
        setSaved(true);
        onToggle?.(true);
      }
    } catch {
      toast.error('Failed to update bookmark');
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={loading}
      className={`p-1.5 rounded-lg transition-colors ${
        saved
          ? 'text-[#7C3AED] bg-[#7C3AED]/10'
          : 'text-muted hover:text-[#7C3AED] hover:bg-[#7C3AED]/5'
      }`}
      aria-label={saved ? 'Remove bookmark' : 'Bookmark this listing'}
    >
      <Bookmark className={`w-4 h-4 ${saved ? 'fill-current' : ''}`} />
    </button>
  );
}
