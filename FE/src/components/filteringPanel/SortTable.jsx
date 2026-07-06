import {useEffect, useState} from "react";
import {Button} from "flowbite-react";
import {CustomButton} from "../button/index.jsx";

export default function SortTable ({
                                       isOpen,
                                       onClose,
                                       currentSort,
                                       onApply
                                   }) {
    const [tempSort, setTempSort] = useState(currentSort);

    useEffect(() => {
        if (isOpen) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setTempSort(currentSort);
        }
    }, [isOpen, currentSort]);

    if (!isOpen) return null;

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 lg:absolute lg:inset-auto lg:top-13 lg:right-16 lg:left-auto lg:p-0 lg:bg-transparent"
            onClick={onClose}
        >
            <div
                className="w-full lg:mt-2 max-w-xs lg:w-64 bg-(--dark-blue-800) border border-(--cool-gray-500) rounded-lg shadow-2xl p-4 text-sm text-white animate-fadeIn"
                onClick={(e) => e.stopPropagation()}
            >
                <h4 className="font-semibold text-white pb-2 mb-3 border-b border-(--cool-gray-500)/50">
                    Filter by
                </h4>
                <div className="flex flex-col gap-3 p-3 mb-4 rounded bg-(--lighter-blue-800) border border-(--cool-gray-500)/40">

                    {/*ID ascend*/}
                    <label className="flex items-center gap-2.5 cursor-pointer select-none text-(--ch-cool-gray) hover:text-white transition-colors">
                        <input
                            type="radio"
                            name="table-sort"
                            checked={tempSort === 'id-asc'}
                            onChange={() => setTempSort('id-asc')}
                            className="rounded-full bg-(--lighter-blue-800) border-slate-600 text-(--color-primary-500) focus:ring-0 focus:ring-offset-0 w-4 h-4"
                        />
                        <span>ID (increase)</span>
                    </label>

                    {/*ID Descend*/}
                    <label className="flex items-center gap-2.5 cursor-pointer select-none text-(--ch-cool-gray) hover:text-white transition-colors">
                        <input
                            type="radio"
                            name="table-sort"
                            checked={tempSort === 'id-desc'}
                            onChange={() => setTempSort('id-desc')}
                            className="rounded-full bg-(--lighter-blue-800) border-slate-600 text-(--color-primary-500) focus:ring-0 focus:ring-offset-0 w-4 h-4"
                        />
                        <span>ID (decrease)</span>
                    </label>

                    {/* Name A-Z */}
                    <label className="flex items-center gap-2.5 cursor-pointer select-none text-(--ch-cool-gray) hover:text-white transition-colors">
                        <input
                            type="radio"
                            name="table-sort"
                            checked={tempSort === 'name-asc'}
                            onChange={() => setTempSort('name-asc')}
                            className="rounded-full bg-(--lighter-blue-800) border-slate-600 text-(--color-primary-500) focus:ring-0 focus:ring-offset-0 w-4 h-4"
                        />
                        <span>Name (A-Z)</span>
                    </label>

                    {/* Name Z-A*/}
                    <label className="flex items-center gap-2.5 cursor-pointer select-none text-(--ch-cool-gray) hover:text-white transition-colors">
                        <input
                            type="radio"
                            name="table-sort"
                            checked={tempSort === 'name-desc'}
                            onChange={() => setTempSort('name-desc')}
                            className="rounded-full bg-(--lighter-blue-800) border-slate-600 text-(--color-primary-500) focus:ring-0 focus:ring-offset-0 w-4 h-4"
                        />
                        <span>Name (Z-A)</span>
                    </label>
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-(--cool-gray-500)/50">
                    <Button color="alternative" onClick={onClose}>
                        Cancel
                    </Button>
                    <CustomButton
                        onClick={() => {
                            onApply(tempSort);
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