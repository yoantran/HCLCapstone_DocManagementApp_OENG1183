import {createBrowserRouter, Navigate} from "react-router-dom";
import {useAuth} from "../context/AuthContext.jsx";
import AuthLayout from "../layouts/AuthLayout.jsx";
import Login from "./auth/Login.jsx";
import ProtectedRoute from "../router/ProtectedRoute.jsx";
import MainLayout from "../layouts/MainLayout.jsx";
import Error from './Error';

/**
 * RootRedirect handles users typing the base URL exactly ("/") without a userId.
 * It waits for the Auth state to resolve, then sends them to their proper home.
 */
// eslint-disable-next-line react-refresh/only-export-components
function RootRedirect() {
    const { user, loading } = useAuth();

    if (loading) return null;
    if (!user) return <Navigate to="/login" replace />;

    return <Navigate to={`/${user.id}/dashboard`} replace />;
}

export const router = createBrowserRouter([
    // PUBLIC
    {
        element: <AuthLayout />,
        children: [
            { path: '/login', element: <Login /> },
        ],
    },

    // STAFF & BOSS
    {
        element: <ProtectedRoute allowedRoles={['STAFF', 'BOSS']} />,
        children: [
            {
                path: '/:userId',
                element: <MainLayout />,
                children: [
                    { path: 'dashboard'},
                    { path: 'submit-request'},
                    { path: 'documents'},
                    { path: 'profile'},
                ],
            },
        ],
    },

    // ADMIN-ONLY
    {
        element: <ProtectedRoute allowedRoles={['ADMIN']} />,
        children: [
            {
                path: '/:userId',
                element: <MainLayout />,
                children: [
                    { path: 'dashboard'},
                    { path: 'submit-request'},
                    { path: 'documents'},
                    { path: 'profile'},

                    // Admin-exclusive
                    {
                        path: 'admin',
                        children: [
                            { index: true, element: <Navigate to="departments" replace /> },
                            { path: 'departments'},
                            { path: 'users'},
                        ]
                    }
                ],
            },
        ],
    },

    // GLOBAL FALLBACK ROUTING
    { path: '/', element: <RootRedirect /> },
    { path: '/unauthorized', element: <div>403 — Access Denied</div> },
    { path: '*', element: <Error /> },
]);