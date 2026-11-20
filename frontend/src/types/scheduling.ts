export interface Slot {
  id: string;
  org_id: string;
  title: string | null;
  duration_min: number;
  buffer_min: number;
  is_active: boolean;
}

export interface Availability {
  id: string;
  slot_id: string;
  date: string;
  start_time: string;
  end_time: string;
  is_booked: boolean;
}

export interface AvailableSlot {
  availability_id: string;
  slot_id: string;
  title: string | null;
  date: string;
  start_time: string;
  end_time: string;
  duration_min: number;
}

export interface Booking {
  id: string;
  slot_id: string;
  availability_id: string;
  candidate_email: string;
  candidate_name: string;
  status: string;
  booked_at: string | null;
}
