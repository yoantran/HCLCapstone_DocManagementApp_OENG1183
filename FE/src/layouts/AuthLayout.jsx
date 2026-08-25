// layouts/AuthLayout.jsx
import { Outlet } from 'react-router-dom';
import loginPhoto from '../assets/LogInPhoto.jpg';
export default function AuthLayout() {
    return (
        <div className="min-h-dvh w-full bg-(--dark-blue-700) flex items-center justify-center p-4 sm:p-6 md:p-10 rounded-[24px]">
            <div className="w-full max-w-[1200px] h-[85vh] max-h-[850px] bg-(--lighter-blue-800) border border-slate-800/60 shadow-2xl overflow-hidden grid grid-cols-1 md:grid-cols-2">

                {/* left side */}
                <div className="hidden md:block relative w-full h-full">
                    <div className="w-full h-full overflow-hidden relative">
                        <img
                            src={loginPhoto}
                            alt="Workspace Collaboration Process"
                            className="w-full h-full object-cover"
                        />
                        <div className="" />
                    </div>
                </div>

                {/* right side */}
                <div className="w-full flex flex-col justify-center items-center px-6 py-10 sm:px-12 lg:px-16 text-center">
                    <Outlet />
                </div>

            </div>
        </div>
    )}