export interface Organization {
  id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  description: string | null;
  website: string | null;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export type OrgRole = 'owner';

export interface OrganizationCreate {
  name: string;
  slug: string;
  website?: string;
  description?: string;
}

export interface OrganizationUpdate {
  name?: string;
  website?: string;
  description?: string;
  settings?: string;
}
