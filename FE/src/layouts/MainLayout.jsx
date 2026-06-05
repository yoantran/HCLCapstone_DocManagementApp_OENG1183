import {Link, Outlet, useNavigate} from 'react-router-dom';
import {useAuth} from "../context/AuthContext.jsx";
import dmsLogo from '../assets/DMSLogo.svg';
import avatar from '../assets/avatar.svg';
import bellOff from '../assets/bell-off.svg';
import {
    Avatar,
    Dropdown,
    DropdownDivider,
    DropdownHeader,
    DropdownItem,
    Navbar,
    NavbarBrand, NavbarCollapse,
    NavbarLink, NavbarToggle
} from "flowbite-react";
import {customNavbarTheme} from "../components/navbar/index.jsx";

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
        <div
            className="border-r border-(--cool-gray-200)"
            // className="flex flex-col min-h-screen bg-(--dark-blue-700) text-(--ch-cool-gray)"
        >
            {/* Global Navbar*/}
            <Navbar
                fluid
                theme={customNavbarTheme}
            >
                <div className="flex items-center gap-10">
                {/* Left Side: Brand Logo */}
                <NavbarBrand as={Link} to={`/${userId}/dashboard`}>
                    <img
                        src={dmsLogo}
                        alt="DMS Icon"
                        className="h-11.25 w-11.25 object-contain"
                    />
                </NavbarBrand>
                {/* Middle Navigation Link Grid Blocks */}
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
                        <>
                            <NavbarLink
                                as={Link}
                                to={`/${userId}/admin/departments`}
                            >
                                Departments
                            </NavbarLink>

                            <NavbarLink
                                as={Link}
                                to={`/${userId}/admin/users`}
                            >
                                Users
                            </NavbarLink>
                        </>
                    )}
                </NavbarCollapse>
                </div>

                {/* Right Side Actions: Notification Bell + Dropdown Avatar Profile Wrapper */}
                <div className="flex items-center gap-4 md:order-2">

                    {/* notification */}
                    {isManagerOnly && (
                        <div className="cursor-pointer transition-opacity hover:opacity-80">
                            <img
                                src={bellOff}
                                alt="bellOff"
                                className="h-8 w-8"
                            />
                        </div>
                    )}

                    {/* Profile */}
                    <Dropdown
                        arrowIcon={false}
                        inline
                        label={
                            <Avatar
                                alt="User Menu Options"
                                img={avatar}
                                rounded
                                className="w-8 h-8 object-contain cursor-pointer"
                            />
                        }
                    >
                        <DropdownHeader className="bg-(--dark-blue-700) text-white border-b border-slate-700">
                            <span className="block text-sm font-semibold">{user.name || 'User Profile'}</span>
                            <span className="block truncate text-xs text-slate-400 mt-0.5">Role: {currentRole}</span>

                        </DropdownHeader>

                        <DropdownItem as={Link} to={`/${userId}/profile`}>
                            View My Profile
                        </DropdownItem>

                        <DropdownDivider className="border-slate-700" />

                        <DropdownItem onClick={logout} className="text-red-400 hover:bg-red-500/10">
                            Sign out
                        </DropdownItem>
                    </Dropdown>

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