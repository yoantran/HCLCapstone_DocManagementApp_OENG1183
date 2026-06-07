import { createBrowserRouter } from 'react-router-dom';

import ProtectedRoute from './ProtectedRoute';
import MainLayout from '../layouts/MainLayout';
import AuthLayout from '../layouts/AuthLayout';

import Login from '../pages/auth/Login';
import Error from '../pages/Error';

// Lazy-load heavier pages once they exist
// import Dashboard from '../pages/Dashboard';

const router = createBrowserRouter([
  // Public routes
  {
    element: <AuthLayout />,
    children: [
      { path: '/login', element: <Login /> },
    ],
  },

  // Authenticated — staff + manager
  {
    element: <ProtectedRoute allowedRoles={['STAFF', 'manager']} />,
    children: [
      {
        element: <MainLayout />,
        children: [
          { path: '/', element: <div>Dashboard placeholder</div> },
          // { path: '/documents', element: <Documents /> },
        ],
      },
    ],
  },

  // Admin-only
  {
    element: <ProtectedRoute allowedRoles={['ADMIN']} />,
    children: [
      {
        element: <MainLayout />,
        children: [
          { path: '/admin', element: <div>Admin placeholder</div> },
        ],
      },
    ],
  },

  // Fallbacks
  { path: '/unauthorized', element: <div>403 — Access Denied</div> },
  { path: '*', element: <Error /> },
]);

export default router;