import { apiClient } from './apiClient';
import type { Slot, Availability, AvailableSlot, Booking } from '../types/scheduling';

export const schedulingService = {
  async createSlot(data: { title?: string; duration_min?: number; buffer_min?: number }): Promise<Slot> {
    return apiClient.post<Slot>('/api/v1/scheduling/slots', data);
  },

  async listSlots(): Promise<Slot[]> {
    return apiClient.get<Slot[]>('/api/v1/scheduling/slots');
  },

  async setAvailability(data: { slot_id: string; date: string; start_time: string; end_time: string }): Promise<Availability> {
    return apiClient.post<Availability>('/api/v1/scheduling/availability', data);
  },

  async getAvailableSlots(): Promise<AvailableSlot[]> {
    return apiClient.get<AvailableSlot[]>('/api/v1/scheduling/available');
  },

  async bookSlot(data: { availability_id: string; candidate_email: string; candidate_name: string }): Promise<Booking> {
    return apiClient.post<Booking>('/api/v1/scheduling/book', data);
  },

  async cancelBooking(bookingId: string): Promise<void> {
    await apiClient.post<void>(`/api/v1/scheduling/bookings/${bookingId}/cancel`);
  },
};
