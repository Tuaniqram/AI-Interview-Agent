import { Routes, Route } from 'react-router-dom';
import { AppShell } from '../layout/AppShell';
import { InterviewShell } from '../layout/InterviewShell';
import { Dashboard } from './Dashboard';
import { CompanyList } from './CompanyList';
import { CompanyDetail } from './CompanyDetail';
import { Sessions } from './Sessions';
import { NewInterview } from './NewInterview';
import { InterviewRoom } from './InterviewRoom';
import { AvatarLab } from './AvatarLab';
import { Settings } from './Settings';

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Dashboard />} />
        <Route path="companies" element={<CompanyList />} />
        <Route path="companies/:id" element={<CompanyDetail />} />
        <Route path="sessions" element={<Sessions />} />
        <Route path="new-interview" element={<NewInterview />} />
        <Route path="avatar-lab" element={<AvatarLab />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route element={<InterviewShell />}>
        <Route path="interview/:id" element={<InterviewRoom />} />
      </Route>
    </Routes>
  );
}
