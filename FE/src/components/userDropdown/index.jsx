// src/components/navbar/UserDropdown.jsx
import { Link } from 'react-router-dom';
import { Dropdown, DropdownHeader, DropdownItem, DropdownDivider, Avatar } from "flowbite-react";

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
                <Avatar
                    alt="User Menu Options"
                    img={avatarAsset}
                    rounded
                    className="w-8 h-8 object-contain cursor-pointer"
                />
            }
            theme={customDropdownTheme}
        >
            <DropdownHeader className="bg-(--dark-blue-700) text-(--ch-light-canvas) border-b border-(--cool-gray-200)">
                <span className="block text-sm font-semibold">{user?.name || 'User Name'}, {userId || 'ID'}</span>
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