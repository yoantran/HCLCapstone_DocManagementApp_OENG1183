// src/components/navbar/UserDropdown.jsx
import { Link } from 'react-router-dom';
import { Dropdown, DropdownHeader, DropdownItem, DropdownDivider } from "flowbite-react";

export default function UserDropdown({ user, userId, currentRole, logout, avatarAsset }) {
    const customDropdownTheme = {
        arrow: {
            base: "hidden"
        },
        content: "py-0 bg-(--dark-blue-700) rounded-lg shadow-2xl border border-slate-800 focus:outline-none",
        floating: {
            animation: "transition-opacity",
            base: "z-50 w-56 rounded-lg shadow-2xl focus:outline-none bg-(--dark-blue-700)",
            placement: "mt-3",
            item: {
                base: "flex w-full cursor-pointer items-center justify-start px-4 py-3 text-left text-sm-custom text-(--ch-cool-gray) hover:bg-slate-700/30 hover:text-white focus:bg-slate-700/30 transition-colors duration-150 bg-transparent"
            }
        }
    }
    return (
        <Dropdown
            arrowIcon={false}
            inline
            label={
                <div className="w-8 h-8 rounded-full overflow-hidden cursor-pointer flex-shrink-0 transition-opacity duration-[160ms] ease-out hover:opacity-80">
                    <img src={avatarAsset} alt="User Menu" className="w-full h-full object-cover" />
                </div>
            }
            theme={customDropdownTheme}
        >
            <DropdownHeader className="bg-(--dark-blue-700) text-(--ch-light-canvas) border-b border-(--cool-gray-200)">
                <div className="flex flex-col items-center gap-0.5 py-1">
                    <span className="text-sm font-semibold">{user?.name || 'User'}</span>
                    <span className="text-xs text-(--cool-gray-500)">{user?.email}</span>
                    <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-xs font-medium text-(--lighter-blue-300)">{user?.role}</span>
                        {user?.departmentName && (
                            <>
                                <span className="text-(--dark-blue-300)">·</span>
                                <span className="text-xs text-(--cool-gray-500)">{user?.departmentName}</span>
                            </>
                        )}
                    </div>
                </div>
            </DropdownHeader>

            <DropdownItem as={Link} to={`/${userId}/profile`} >
                View My Profile
            </DropdownItem>

            <DropdownDivider className="border-(--cool-gray-200)" />

            <DropdownItem onClick={logout} className="text-red-400 hover:bg-red-500/10">
                Sign out
            </DropdownItem>
        </Dropdown>
    );
}