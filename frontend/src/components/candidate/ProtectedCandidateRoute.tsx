import { Navigate, useLocation } from 'react-router-dom';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';
import { LoadingSpinner } from '../shared/LoadingSpinner';

export function ProtectedCandidateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useCandidateAuth();
  const location = useLocation();

  if (isLoading) {
    return <LoadingSpinner message="Loading..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/candidate/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
