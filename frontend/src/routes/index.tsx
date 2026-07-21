import React, { Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import { AppShell } from '../layout/AppShell';
import { InterviewShell } from '../layout/InterviewShell';

const Landing = React.lazy(() => import('../pages/Landing').then(m => ({ default: m.Landing })));
const Dashboard = React.lazy(() => import('./Dashboard').then(m => ({ default: m.Dashboard })));
const CompanyList = React.lazy(() => import('./CompanyList').then(m => ({ default: m.CompanyList })));
const CompanyDetail = React.lazy(() => import('./CompanyDetail').then(m => ({ default: m.CompanyDetail })));
const Sessions = React.lazy(() => import('./Sessions').then(m => ({ default: m.Sessions })));
const NewInterview = React.lazy(() => import('./NewInterview').then(m => ({ default: m.NewInterview })));
const InterviewRoom = React.lazy(() => import('./InterviewRoom').then(m => ({ default: m.InterviewRoom })));
const InterviewReportPage = React.lazy(() => import('./InterviewReport').then(m => ({ default: m.InterviewReportPage })));
const Analytics = React.lazy(() => import('./Analytics').then(m => ({ default: m.Analytics })));
const AvatarLab = React.lazy(() => import('./AvatarLab').then(m => ({ default: m.AvatarLab })));
const Settings = React.lazy(() => import('./Settings').then(m => ({ default: m.Settings })));

const LoadingFallback = () => (
  <div className="min-h-screen bg-app flex items-center justify-center">
    <div className="animate-spin w-8 h-8 -2 -action-primary -t-transparent rounded-full" />
  </div>
);

export function AppRoutes() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route element={<AppShell />}>
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="companies" element={<CompanyList />} />
          <Route path="companies/:id" element={<CompanyDetail />} />
          <Route path="sessions" element={<Sessions />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="interview/:id/report" element={<InterviewReportPage />} />
          <Route path="new-interview" element={<NewInterview />} />
          <Route path="avatar-lab" element={<AvatarLab />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        <Route element={<InterviewShell />}>
          <Route path="interview/:id" element={<InterviewRoom />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
