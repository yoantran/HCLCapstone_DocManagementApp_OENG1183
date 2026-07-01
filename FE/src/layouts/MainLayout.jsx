import { Link, Outlet } from 'react-router-dom';
import { useAuth } from "../context/AuthContext.jsx";
import dmsLogo from '../assets/DMSLogo.svg';
import avatar from '../assets/avatar.svg';
import {
    Navbar,
    NavbarBrand, NavbarCollapse,
    NavbarLink, NavbarToggle
} from "flowbite-react";
import { customNavbarTheme } from "../components/navbar/index.jsx";
import UserDropdown from "../components/userDropdown/index.jsx";
import { NotificationBell } from '../components/navbar/NotificationBell.jsx';

export default function MainLayout() {
    const { user, logout } = useAuth();
    if (!user) return null;

    const currentRole = user.role?.toUpperCase();
    const userId = user.id;

    const isStaffFeatureAllowed = ['STAFF', 'MANAGER', 'ADMIN'].includes(currentRole);

    const isManagerOnly = currentRole === 'MANAGER';
    const isAdminOnly = currentRole === 'ADMIN';


    return (
        <div
            className="border-r border-(--cool-gray-200)"
        >
            {/* Global Navbar*/}
            <Navbar
                fluid
                theme={customNavbarTheme}
            >
                <div className="flex items-center gap-10">
                    {/* Left Side: Brand Logo */}
                    <NavbarBrand as={Link} to={`/${userId}/submit-request`}>
                        <img
                            src={dmsLogo}
                            alt="DMS Icon"
                            className="h-11.25 w-11.25 object-contain"
                        />
                    </NavbarBrand>
                    {/* Middle Navigation */}
                    <NavbarCollapse>
                        {/*  Staff & Manager */}
                        {isStaffFeatureAllowed && (
                            <>
                                <NavbarLink
                                    as={Link}
                                    to={`/${userId}/submit-request`}
                                >
                                    Submit New Request
                                </NavbarLink>

                                <NavbarLink
                                    as={Link}
                                    to={`/${userId}/documents`}
                                >
                                    Documents
                                </NavbarLink>
                            </>
                        )}
                        {/* 2. Admin */}
                        {isAdminOnly && (
                            <NavbarLink
                                as={Link}
                                to={`/${userId}/admin/management`}
                            >
                                Users & Departments Management
                            </NavbarLink>
                        )}
                    </NavbarCollapse>
                </div>

                {/* Right Side Actions: Notification Bell + Dropdown Avatar Profile Wrapper */}
                <div className="flex items-center gap-4 md:order-2">

                    {/* notification */}
                    {isManagerOnly && (
                        <div>
                            <NotificationBell userId={userId} userEmail={user?.email} />
                        </div>
                    )}
                    <UserDropdown
                        user={user}
                        userId={userId}
                        currentRole={currentRole}
                        logout={logout}
                        avatarAsset={avatar}
                    />

                    {/* Core toggle trigger for small responsive screen handling collapse */}
                    <NavbarToggle className="text-slate-400 hover:bg-slate-800" />
                </div>

            </Navbar>

            {/* Page Content Panel */}
            <main className="flex-1 p-8">
                <Outlet />
            </main>
        </div>
    );
}