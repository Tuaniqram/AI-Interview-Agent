import React, { Suspense } from 'react';
import { Navigate, Routes, Route } from 'react-router-dom';
import { AppShell } from '../layout/AppShell';
import { InterviewShell } from '../layout/InterviewShell';
import { AdminShell } from '../layout/AdminShell';
import { CandidateShell } from '../layout/CandidateShell';
import { OpportunityHubLayout } from '../layout/OpportunityHubLayout';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { ProtectedCandidateRoute } from '../components/candidate/ProtectedCandidateRoute';
import { ContentSkeleton } from '../components/shared/ContentSkeleton';

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
const ForgotPassword = React.lazy(() => import('../pages/auth/ForgotPassword'));
const ResetPassword = React.lazy(() => import('../pages/auth/ResetPassword'));
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
const AcceptOrgInvite = React.lazy(() => import('../pages/invite/AcceptOrgInvite'));

const LoadingFallback = () => (
  <div className="min-h-screen bg-app flex items-center justify-center">
    <div className="animate-spin w-8 h-8 border-2 border-[var(--action-primary)] border-t-transparent rounded-full" />
  </div>
);

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Suspense fallback={<LoadingFallback />}><Landing /></Suspense>} />
      <Route path="/login" element={<Suspense fallback={<LoadingFallback />}><Login /></Suspense>} />
      <Route path="/register" element={<Suspense fallback={<LoadingFallback />}><Register /></Suspense>} />
      <Route path="/forgot-password" element={<Suspense fallback={<LoadingFallback />}><ForgotPassword /></Suspense>} />
      <Route path="/reset-password" element={<Suspense fallback={<LoadingFallback />}><ResetPassword /></Suspense>} />
      <Route path="/org-select" element={<Suspense fallback={<LoadingFallback />}><OrgSelect /></Suspense>} />
      <Route path="/public-interview/:token" element={<Suspense fallback={<LoadingFallback />}><PublicInterviewPage /></Suspense>} />
      <Route path="/invite/:token" element={<Suspense fallback={<LoadingFallback />}><AcceptInvitation /></Suspense>} />
      <Route path="/accept-org-invite/:token" element={<Suspense fallback={<LoadingFallback />}><AcceptOrgInvite /></Suspense>} />

      <Route element={<OpportunityHubLayout />}>
        <Route path="opportunity-hub" element={<Suspense fallback={<ContentSkeleton />}><OpportunityHubHome /></Suspense>} />
        <Route path="opportunity-hub/organizations/:slug" element={<Suspense fallback={<ContentSkeleton />}><OppHubOrgProfile /></Suspense>} />
        <Route path="opportunity-hub/interviews/:interviewId" element={<Suspense fallback={<ContentSkeleton />}><OppHubInterviewDetail /></Suspense>} />
      </Route>

      <Route path="/candidate/login" element={<Suspense fallback={<LoadingFallback />}><CandidateLogin /></Suspense>} />
      <Route path="/candidate/register" element={<Suspense fallback={<LoadingFallback />}><CandidateRegister /></Suspense>} />
      <Route element={<ProtectedCandidateRoute><CandidateShell /></ProtectedCandidateRoute>}>
        <Route path="/candidate/dashboard" element={<Suspense fallback={<ContentSkeleton />}><CandidateDashboard /></Suspense>} />
        <Route path="/candidate/interviews" element={<Suspense fallback={<ContentSkeleton />}><CandidateInterviews /></Suspense>} />
        <Route path="/candidate/interviews/:interviewId" element={<Suspense fallback={<ContentSkeleton />}><CandidateInterviewDetail /></Suspense>} />
        <Route path="/candidate/practice" element={<Suspense fallback={<ContentSkeleton />}><CandidatePractice /></Suspense>} />
        <Route path="/candidate/profile" element={<Suspense fallback={<ContentSkeleton />}><CandidateProfile /></Suspense>} />
      </Route>

      <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
        <Route path="dashboard" element={<Navigate to="/org" replace />} />
        <Route path="departments" element={<Suspense fallback={<ContentSkeleton />}><DepartmentList /></Suspense>} />
        <Route path="departments/:id" element={<Suspense fallback={<ContentSkeleton />}><DepartmentDetail /></Suspense>} />
        <Route path="sessions" element={<Suspense fallback={<ContentSkeleton />}><Sessions /></Suspense>} />
        <Route path="analytics" element={<Suspense fallback={<ContentSkeleton />}><Analytics /></Suspense>} />
        <Route path="interview/:id/report" element={<Suspense fallback={<ContentSkeleton />}><InterviewReportPage /></Suspense>} />
        <Route path="avatar-lab" element={<Suspense fallback={<ContentSkeleton />}><AvatarLab /></Suspense>} />
        <Route path="settings" element={<Suspense fallback={<ContentSkeleton />}><Settings /></Suspense>} />
        <Route path="org" element={<Suspense fallback={<ContentSkeleton />}><OrgDashboard /></Suspense>} />
        <Route path="org/members" element={<Suspense fallback={<ContentSkeleton />}><OrgMembers /></Suspense>} />
      </Route>

      <Route element={<ProtectedRoute><AdminShell /></ProtectedRoute>}>
        <Route path="admin" element={<Suspense fallback={<ContentSkeleton />}><AdminDashboard /></Suspense>} />
        <Route path="admin/organizations" element={<Suspense fallback={<ContentSkeleton />}><AdminOrgs /></Suspense>} />
        <Route path="admin/users" element={<Suspense fallback={<ContentSkeleton />}><AdminUsers /></Suspense>} />
      </Route>

      <Route element={<InterviewShell />}>
        <Route path="interview/:id" element={<Suspense fallback={<LoadingFallback />}><InterviewRoom /></Suspense>} />
      </Route>
    </Routes>
  );
}
