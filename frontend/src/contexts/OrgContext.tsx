import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import type { Organization } from '../types/org';
import { orgService } from '../services/orgService';
import { useAuth } from './AuthContext';

interface OrgContextType {
  activeOrg: Organization | null;
  orgs: Organization[];
  loading: boolean;
  switchOrg: (orgId: string) => Promise<void>;
  refreshOrgs: () => Promise<void>;
}

const OrgContext = createContext<OrgContextType | undefined>(undefined);

export function OrgProvider({ children }: { children: React.ReactNode }) {
  const { memberships } = useAuth();
  const [activeOrg, setActiveOrg] = useState<Organization | null>(null);
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(false);

  const switchOrg = useCallback(async (orgId: string) => {
    setLoading(true);
    try {
      localStorage.setItem('active_org_id', orgId);
      const org = await orgService.get(orgId);
      setActiveOrg(org);
    } catch (err) {
      console.error('Failed to switch org', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshOrgs = useCallback(async () => {
    if (!memberships || memberships.length === 0) return;
    const orgList: Organization[] = [];
    for (const m of memberships) {
      try {
        const org = await orgService.get(m.org_id);
        orgList.push(org);
      } catch { /* skip */ }
    }
    setOrgs(orgList);
  }, [memberships]);

  useEffect(() => {
    if (!memberships || memberships.length === 0) return;
    // Use the remembered org when the user still belongs to it, else the first membership.
    // (No validation request: switchOrg fetches the org anyway.)
    const stored = localStorage.getItem('active_org_id');
    const orgId = stored && memberships.some(m => m.org_id === stored) ? stored : memberships[0].org_id;
    switchOrg(orgId);
  }, [memberships, switchOrg]);

  useEffect(() => {
    refreshOrgs();
  }, [refreshOrgs]);

  return (
    <OrgContext.Provider
      value={{ activeOrg, orgs, loading, switchOrg, refreshOrgs }}
    >
      {children}
    </OrgContext.Provider>
  );
}

export function useOrg() {
  const ctx = useContext(OrgContext);
  if (!ctx) throw new Error('useOrg must be used within OrgProvider');
  return ctx;
}
