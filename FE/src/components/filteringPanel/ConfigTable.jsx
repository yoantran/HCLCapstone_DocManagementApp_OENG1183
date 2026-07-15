import {useEffect, useState} from "react";
import {CustomButton} from "../button/index.jsx";
import {Button} from "flowbite-react";

export default function ConfigTable ({
    isOpen,
    onClose,
    activeTab,
    onApply
}) {
    const [tempSelectedTab, setTempSelectedTab] = useState(activeTab);
    useEffect(() => {
        if (isOpen) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setTempSelectedTab(activeTab);
        }
    }, [isOpen, activeTab]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-(--dark-blue-800) lg:absolute lg:inset-auto lg:top-13 lg:left-1 lg:p-0 lg:bg-transparent"
             onClick={onClose}
        >
            <div className="w-full lg:mt-2 max-w-xs lg:w-64 bg-(--dark-blue-800) border border-(--cool-gray-500) rounded-lg shadow-2xl p-4 text-sm text-white animate-fadeIn"
                 onClick={(e) => e.stopPropagation()}
            >

                <h4 className="font-semibold text-white pb-2 mb-3 border-b border-(--cool-gray-500)/50">Configure Table</h4>

                <div className="flex flex-col gap-3 p-3 mb-4 rounded bg-(--lighter-blue-800) border border-(--cool-gray-500)/40">
                    <label className="flex items-center gap-2.5 cursor-pointer select-none text-(--ch-cool-gray) hover:text-white transition-colors">
                        <input
                            type="checkbox"
                            checked={tempSelectedTab === 'users'}
                            onChange={() => setTempSelectedTab('users')}
                            className="rounded bg-(--lighter-blue-800) border-slate-600 text-(--color-primary-500) focus:ring-0 focus:ring-offset-0 w-4 h-4"
                        />
                        <span>Users</span>
                    </label>

                    <label className="flex items-center gap-2.5 cursor-pointer select-none text-(--ch-cool-gray) hover:text-white transition-colors">
                        <input
                            type="checkbox"
                            checked={tempSelectedTab === 'departments'}
                            onChange={() => setTempSelectedTab('departments')}
                            className="rounded bg-(--lighter-blue-800) border-slate-600 text-(--color-primary-500) focus:ring-0 focus:ring-offset-0 w-4 h-4"
                        />
                        <span>Departments</span>
                    </label>
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-(--cool-gray-500)/50">
                    <Button color="alternative"
                            onClick={onClose}
                    >
                        Cancel
                    </Button>
                    <CustomButton
                        onClick={() => {
                            onApply(tempSelectedTab);
                            onClose();
                        }}
                    >
                        Apply
                    </CustomButton>
                </div>
            </div>
        </div>
    );
}