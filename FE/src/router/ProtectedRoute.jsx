import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {Spinner} from "flowbite-react";

/**
 * @param {string[]} allowedRoles - e.g. ['staff', 'manager'] or ['admin']
 *                                   omit/empty = any authenticated user
 */
export default function ProtectedRoute({ allowedRoles = [] }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
        <div className="flex h-screen w-screen items-center justify-center">
          <Spinner size="xl" color="info" aria-label="Loading" />
        </div>
        )
  }

  if (!user) return <Navigate to="/login" replace />;

  if (allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <Outlet />;
}