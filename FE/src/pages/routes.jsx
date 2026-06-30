import { createBrowserRouter, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import AuthLayout from "../layouts/AuthLayout.jsx";
import Login from "./auth/Login.jsx";
import ProtectedRoute from "../router/ProtectedRoute.jsx";
import MainLayout from "../layouts/MainLayout.jsx";
import Error from './Error';
import RequestSubmission from "./RequestSubmission.jsx";
import Documents from "./Documents.jsx";
import ViewDocument from "./ViewDocument.jsx";
import AdminManagement from "./AdminManagement.jsx";

/**
 * RootRedirect handles users typing the base URL exactly ("/") without a userId.
 * It waits for the Auth state to resolve, then sends them to their proper home.
 */
// eslint-disable-next-line react-refresh/only-export-components
function RootRedirect() {
    const { user, loading } = useAuth();

    if (loading) return null;
    if (!user) return <Navigate to="/login" replace />;

    return <Navigate to={`/${user.id}/submit-request`} replace />;
}

export const router = createBrowserRouter([
    // PUBLIC
    {
        element: <AuthLayout />,
        children: [
            { path: '/login', element: <Login /> },
        ],
    },

    {
        element: <ProtectedRoute allowedRoles={['STAFF', 'MANAGER', 'ADMIN']} />,
        children: [
            {
                path: '/:userId',
                element: <MainLayout />,
                children: [
                    // Default redirect when visiting /:userId base route directly
                    { index: true, element: <Navigate to="submit-request" replace /> },

                    { path: 'submit-request', element: <RequestSubmission /> },
                    { path: 'documents', element: <Documents /> },
                    { path: 'profile' },
                    { path: 'view-document/:documentId', element: <ViewDocument /> },


                    {
                        path: 'admin',
                        element: <ProtectedRoute allowedRoles={['ADMIN']} />,
                        children: [
                            { path: 'management', element: <AdminManagement /> },
                        ]
                    }
                ],
            },
        ],
    },

    // GLOBAL FALLBACK ROUTING
    { path: '/', element: <RootRedirect /> },
    { path: '/unauthorized', element: <div>403 - Access Denied</div> },
    { path: '*', element: <Error /> },
]);