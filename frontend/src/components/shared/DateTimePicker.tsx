import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import '../../styles/datepicker.css';
import { Calendar } from 'lucide-react';

interface DateTimePickerProps {
  value: string;
  onChange: (iso: string) => void;
  placeholder?: string;
}

export function DateTimePicker({ value, onChange, placeholder = 'Pick date & time' }: DateTimePickerProps) {
  const date = value ? new Date(value) : null;

  return (
    <div className="relative">
      <DatePicker
        selected={date}
        onChange={(d: Date | null) => onChange(d ? d.toISOString() : '')}
        showTimeSelect
        dateFormat="MMM d, yyyy h:mm aa"
        timeFormat="h:mm aa"
        timeIntervals={15}
        placeholderText={placeholder}
        isClearable
        className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)] text-sm cursor-pointer"
        wrapperClassName="w-full"
        popperClassName="!z-50"
      />
      <Calendar className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted pointer-events-none" />
    </div>
  );
}
