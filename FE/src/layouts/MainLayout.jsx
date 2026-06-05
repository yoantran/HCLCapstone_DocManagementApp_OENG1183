import {Link, Outlet, useNavigate} from 'react-router-dom';
import {useAuth} from "../context/AuthContext.jsx";
import dmsLogo from '../assets/DMSLogo.svg';
import avatar from '../assets/avatar.svg';
import bellOff from '../assets/bell-off.svg';

export default function MainLayout() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    if (!user) return null;

    const currentRole = user.role?.toUpperCase();
    const userId = user.id;

    const isStaffFeatureAllowed = ['STAFF', 'BOSS', 'ADMIN'].includes(currentRole);

    const isManagerOnly = currentRole === 'BOSS';
    const isAdminOnly = currentRole === 'ADMIN';

    // TODO: WIP NavBar
    return (
        <div className="flex flex-col min-h-screen bg-(--dark-blue-700) text-(--ch-cool-gray)">
            {/* Global Navbar */}
            <nav className={"flex justify-between items-center h-16.25 bg-[#0b151e] border-b-2 border-(--cool-gray-200)"}>
                <div className="flex items-center gap-10">
                    <div className="flex items-center">
                        <Link to="/">
                            <img
                                src={dmsLogo}
                                alt="DMS Icon"
                                className="h-8"
                            />
                        </Link>
                    </div>
                </div>

                <div className="flex items-center gap-6">
                    {/* All Can see */}
                    {isStaffFeatureAllowed && (
                        <>
                            <Link to={`/${userId}/submit-request`}>Submit New Request</Link>
                            <Link to={`/${userId}/documents`}>Documents</Link>
                        </>
                    )}

                    {/* Only Admin */}
                    {isAdminOnly && (
                        <>
                            <Link to={`/${userId}/admin/departments`}>Departments</Link>
                            <Link to={`/${userId}/admin/users`}>Users</Link>
                        </>
                    )}
                </div>

                <div className="flex items-center gap-5">
                    {/* ONLY the Manager */}
                    {isManagerOnly && (
                        <div className="cursor-pointer text-[#8a99a8] text-eed flex items-center hover:text-white transition-colors">
                            <img
                                src={bellOff}
                                alt="bellOff"
                                className="h-8 w-8"
                            />
                        </div>
                    )}
                    <Link to={`/${userId}/profile`} className="flex items-center no-underline">
                        <img
                            src={avatar}
                            alt="Avatar"
                            className="h-8 w-8"
                        />
                    </Link>
                </div>
            </nav>

            {/* Page Content Panel */}
            <main className="content-container" style={{ flex: 1, padding: '2rem' }}>
                <Outlet />
            </main>
        </div>
    );
}