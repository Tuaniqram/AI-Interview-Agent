import { useEffect, useState } from 'react';
import { schedulingService } from '../../services/schedulingService';
import { PageHeader } from '../../components/shared/PageHeader';
import { Button } from '../../components/shared/Button';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { EmptyState } from '../../components/shared/EmptyState';
import type { Slot } from '../../types/scheduling';

export default function Scheduling() {
  const [slots, setSlots] = useState<Slot[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    schedulingService.listSlots()
      .then(setSlots)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Interview Scheduling"
        description="Manage interview slots and availability"
        actions={<Button>Create Slot</Button>}
      />
      {slots.length === 0 ? (
        <EmptyState
          title="No interview slots"
          description="Create your first interview slot to start scheduling"
        />
      ) : (
        <div className="grid gap-4">
          {slots.map((slot) => (
            <div
              key={slot.id}
              className="p-4 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)]"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-[var(--text-primary)]">{slot.title || 'Untitled Slot'}</h3>
                  <p className="text-sm text-[var(--text-secondary)]">
                    {slot.duration_min} min + {slot.buffer_min} min buffer
                  </p>
                </div>
                <span
                  className={`text-xs px-2 py-1 rounded-full font-medium ${
                    slot.is_active
                      ? 'bg-green-100 dark:bg-green-900/20 text-green-600'
                      : 'bg-gray-100 dark:bg-gray-900/20 text-gray-600'
                  }`}
                >
                  {slot.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
