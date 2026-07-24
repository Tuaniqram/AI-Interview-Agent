import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import type { Organization, OrgMember } from '../types/org';
import { orgService } from '../services/orgService';
import { useAuth } from './AuthContext';

interface OrgContextType {
  activeOrg: Organization | null;
  orgs: Organization[];
  members: OrgMember[];
  loading: boolean;
  switchOrg: (orgId: string) => Promise<void>;
  refreshMembers: () => Promise<void>;
  refreshOrgs: () => Promise<void>;
}

const OrgContext = createContext<OrgContextType | undefined>(undefined);

export function OrgProvider({ children }: { children: React.ReactNode }) {
  const { memberships } = useAuth();
  const [activeOrg, setActiveOrg] = useState<Organization | null>(null);
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [loading, setLoading] = useState(false);

  const switchOrg = useCallback(async (orgId: string) => {
    setLoading(true);
    try {
      localStorage.setItem('active_org_id', orgId);
      const org = await orgService.get(orgId);
      setActiveOrg(org);
      const memberList = await orgService.listMembers(orgId);
      setMembers(memberList);
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

  const refreshMembers = useCallback(async () => {
    if (!activeOrg) return;
    const memberList = await orgService.listMembers(activeOrg.id);
    setMembers(memberList);
  }, [activeOrg]);

  useEffect(() => {
    if (!memberships || memberships.length === 0) return;
    const initOrg = async () => {
      let orgId = localStorage.getItem('active_org_id');
      if (orgId) {
        try {
          await orgService.get(orgId);
        } catch {
          orgId = null;
        }
      }
      if (!orgId) {
        orgId = memberships[0].org_id;
      }
      switchOrg(orgId);
    };
    initOrg();
  }, [memberships, switchOrg]);

  useEffect(() => {
    refreshOrgs();
  }, [refreshOrgs]);

  return (
    <OrgContext.Provider
      value={{ activeOrg, orgs, members, loading, switchOrg, refreshMembers, refreshOrgs }}
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
