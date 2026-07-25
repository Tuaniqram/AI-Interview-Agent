import { Navigate, useLocation } from 'react-router-dom';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';

export function ProtectedCandidateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useCandidateAuth();
  const location = useLocation();

  if (isLoading) {
    return <>{children}</>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/candidate/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
