import React, { Suspense } from 'react';
import { Navigate, Routes, Route } from 'react-router-dom';
import { AppShell } from '../layout/AppShell';
import { InterviewShell } from '../layout/InterviewShell';
import { AdminShell } from '../layout/AdminShell';
import { CandidateShell } from '../layout/CandidateShell';
import { OpportunityHubLayout } from '../layout/OpportunityHubLayout';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { ProtectedCandidateRoute } from '../components/candidate/ProtectedCandidateRoute';

const Landing = React.lazy(() => import('../pages/Landing').then(m => ({ default: m.Landing })));
const DepartmentList = React.lazy(() => import('./DepartmentList').then(m => ({ default: m.DepartmentList })));
const DepartmentDetail = React.lazy(() => import('./DepartmentDetail').then(m => ({ default: m.DepartmentDetail })));
const Sessions = React.lazy(() => import('./Sessions').then(m => ({ default: m.Sessions })));
const InterviewRoom = React.lazy(() => import('./InterviewRoom').then(m => ({ default: m.InterviewRoom })));
const InterviewReportPage = React.lazy(() => import('./InterviewReport').then(m => ({ default: m.InterviewReportPage })));
const Analytics = React.lazy(() => import('./Analytics').then(m => ({ default: m.Analytics })));
const AvatarLab = React.lazy(() => import('./AvatarLab').then(m => ({ default: m.AvatarLab })));
const Settings = React.lazy(() => import('./Settings').then(m => ({ default: m.Settings })));

const Login = React.lazy(() => import('../pages/auth/Login'));
const Register = React.lazy(() => import('../pages/auth/Register'));
const OrgSelect = React.lazy(() => import('../pages/auth/OrgSelect'));
const OpportunityHubHome = React.lazy(() => import('../pages/opportunity-hub/OpportunityHubHome'));
const OppHubOrgProfile = React.lazy(() => import('../pages/opportunity-hub/OrgProfile'));
const OppHubInterviewDetail = React.lazy(() => import('../pages/opportunity-hub/InterviewDetail'));
const PublicInterviewPage = React.lazy(() => import('../pages/public-interview/PublicInterview'));
const OrgDashboard = React.lazy(() => import('../pages/org/OrgDashboard'));
const OrgMembers = React.lazy(() => import('../pages/org/Members'));
const AdminDashboard = React.lazy(() => import('../pages/admin/AdminDashboard'));
const AdminOrgs = React.lazy(() => import('../pages/admin/OrgManagement'));
const AdminUsers = React.lazy(() => import('../pages/admin/UserManagement'));

const CandidateLogin = React.lazy(() => import('../pages/candidate/Login'));
const CandidateRegister = React.lazy(() => import('../pages/candidate/Register'));
const CandidateDashboard = React.lazy(() => import('../pages/candidate/Dashboard'));
const CandidateInterviews = React.lazy(() => import('../pages/candidate/Interviews'));
const CandidateInterviewDetail = React.lazy(() => import('../pages/candidate/InterviewDetail'));
const CandidatePractice = React.lazy(() => import('../pages/candidate/Practice'));
const CandidateProfile = React.lazy(() => import('../pages/candidate/Profile'));
const AcceptInvitation = React.lazy(() => import('../pages/invite/AcceptInvitation'));

const LoadingFallback = () => (
  <div className="min-h-screen bg-app flex items-center justify-center">
    <div className="animate-spin w-8 h-8 border-2 border-[var(--action-primary)] border-t-transparent rounded-full" />
  </div>
);

export function AppRoutes() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/org-select" element={<OrgSelect />} />
        <Route path="/public-interview/:token" element={<PublicInterviewPage />} />
        <Route path="/invite/:token" element={<AcceptInvitation />} />

        <Route element={<OpportunityHubLayout />}>
          <Route path="opportunity-hub" element={<OpportunityHubHome />} />
          <Route path="opportunity-hub/organizations/:slug" element={<OppHubOrgProfile />} />
          <Route path="opportunity-hub/interviews/:interviewId" element={<OppHubInterviewDetail />} />
        </Route>

        {/* Candidate routes */}
        <Route path="/candidate/login" element={<CandidateLogin />} />
        <Route path="/candidate/register" element={<CandidateRegister />} />
        <Route element={<ProtectedCandidateRoute><CandidateShell /></ProtectedCandidateRoute>}>
          <Route path="/candidate/dashboard" element={<CandidateDashboard />} />
          <Route path="/candidate/interviews" element={<CandidateInterviews />} />
          <Route path="/candidate/interviews/:interviewId" element={<CandidateInterviewDetail />} />
          <Route path="/candidate/practice" element={<CandidatePractice />} />
          <Route path="/candidate/profile" element={<CandidateProfile />} />
        </Route>

        {/* Org user routes */}
        <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
          <Route path="dashboard" element={<Navigate to="/org" replace />} />
          <Route path="departments" element={<DepartmentList />} />
          <Route path="departments/:id" element={<DepartmentDetail />} />
          <Route path="sessions" element={<Sessions />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="interview/:id/report" element={<InterviewReportPage />} />
          <Route path="avatar-lab" element={<AvatarLab />} />
          <Route path="settings" element={<Settings />} />
          <Route path="org" element={<OrgDashboard />} />
          <Route path="org/members" element={<OrgMembers />} />
        </Route>

        {/* Admin routes */}
        <Route element={<ProtectedRoute><AdminShell /></ProtectedRoute>}>
          <Route path="admin" element={<AdminDashboard />} />
          <Route path="admin/organizations" element={<AdminOrgs />} />
          <Route path="admin/users" element={<AdminUsers />} />
        </Route>

        {/* Interview room (shared across all user types) */}
        <Route element={<InterviewShell />}>
          <Route path="interview/:id" element={<InterviewRoom />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
