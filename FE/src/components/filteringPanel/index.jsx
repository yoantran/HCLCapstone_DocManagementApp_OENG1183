import { TextInput } from "flowbite-react";
import { CustomSearchIcon } from "./icon/CustomSearchIcon.jsx";
import { CustomSettingIcon } from "./icon/CustomSettingIcon.jsx";
import { LeftArrowIcon } from "./icon/LeftArrowIcon.jsx";
import { RightArrowIcon } from "./icon/RightArrowIcon.jsx";
import { CustomFilterIcon } from "./icon/CustomFilterIcon.jsx";
import { useEffect } from "react";

const searchInputTheme = {
    field: {
        input: {
            base: "w-full text-sm font-normal focus:ring-1 focus:outline-none ",
            colors: {
                gray: "bg-(--dark-blue-800) text-(--cool-gray-500) border-(--ch-cool-gray) focus:border-(--ch-lighter-blue) focus:ring-(--ch-lighter-blue)"
            }
        }
    }
}
const FilteringPanel = ({
    // Global
    currentPage = 1,
    pageSize = 10,
    totalItems = 0,
    onPageChange = number => { },
    customButton = null,

    // Manager
    showSearch = false,
    searchValue = '',
    onSearchChange = () => { },
    searchPlaceholder = 'Search',
    showFilter = false,
    onFilterClick = () => { },

    // Admin
    showSettings = false,
    onSettingsClick = () => { },
    activeTabLabel = null,
    onClearFilters = null,
}) => {
    const totalPages = Math.ceil(totalItems / pageSize) || 1;

    useEffect(() => {
        if (currentPage > totalPages) {
            onPageChange(totalPages);
        } else if (currentPage < 1) {
            onPageChange(1);
        }
    }, [totalPages, currentPage, onPageChange]);


    const startItem = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1;
    const endItem = Math.min(currentPage * pageSize, totalItems);

    const handlePrevPage = () => {
        if (currentPage > 1) onPageChange(currentPage - 1);
    };

    const handleNextPage = () => {
        if (currentPage < totalPages) onPageChange(currentPage + 1);
    };

    return (
        <>
            <div
                className="flex w-[95%] max-w-365 h-17.25 items-center justify-between bg-(--dark-blue-800) px-4 py-3 text-(--cool-gray-500) shadow-md border-b border--(--ch-cool-gray) rounded-t-md">

                {/*Settings Icon & Search Bar */}
                <div className={"flex items-center gap-3 flex-1 max-w-xl shrink-0"}>
                    {showSettings && (
                        <button
                            onClick={onSettingsClick}
                            className="flex items-center justify-center w-8 h-8 text-(--cool-gray-200) hover:text-white transition-colors p-1"
                            type="button"
                        >
                            <CustomSettingIcon />
                        </button>
                    )}
                    {showSettings && showSearch && (
                        <div className="h-6 w-px bg-(--ch-cool-gray)" />
                    )}
                    {showSearch && (
                        <div className="w-full max-w-md">
                            <TextInput
                                id="toolbar-search"
                                type="text"
                                icon={CustomSearchIcon}
                                placeholder={searchPlaceholder}
                                value={searchValue}
                                onChange={(e) => onSearchChange(e.target.value)}
                                theme={searchInputTheme}
                            />
                        </div>
                    )}
                </div>

                {/*Action, Pagination, Navigation, Filter*/}
                <div className="flex items-center gap-1">
                    <div className="flex items-center gap-1 shrink-0">
                        {customButton}
                    </div>
                    <div className="flex items-center gap-1 text-sm select-none text-white">
                        <span className={"w-28 text-center tabular-nums"}>
                            {startItem} - {endItem} of {totalItems}
                        </span>
                        <div className="flex items-center">
                            <button
                                onClick={handlePrevPage}
                                disabled={currentPage <= 1}
                                className="p-1 text-(--cool-gray-200) hover:text-white disabled:opacity-30 disabled:hover:text-(--cool-gray-500) transition-colors"
                                type="button"
                            >
                                <LeftArrowIcon />
                            </button>
                            <button
                                onClick={handleNextPage}
                                disabled={currentPage >= totalPages}
                                className="p-1 text-(--cool-gray-200) hover:text-white disabled:opacity-30 disabled:hover:text-(--cool-gray-500) transition-colors"
                                type="button"
                            >
                                <RightArrowIcon />
                            </button>
                        </div>
                    </div>

                    {showFilter && (
                        <>
                            <div className="h-6 w-px bg-(--ch-cool-gray)" />
                            <button
                                onClick={onFilterClick}
                                className="text-(--cool-gray-500) hover:text-white transition-colors p-1"
                                type="button"
                            >
                                <CustomFilterIcon />
                            </button>
                        </>
                    )}
                </div>

            </div>
            {(activeTabLabel || onClearFilters) && (
                <div className="flex w-[95%] max-w-365 h-12 items-center bg-(--dark-blue-800) px-4 text-xs border-b border-r border-l border-(--ch-cool-gray) select-none justify-between">
                    {activeTabLabel && (
                        <div className="flex items-center gap-2 bg-(--lighter-blue-700) px-2.5 py-1 rounded border border-(--cool-gray-500)/30">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]" />
                            <span className="text-(--ch-cool-gray)">Current Table:</span>
                            <span className="font-semibold capitalize text-white">{activeTabLabel}</span>
                        </div>
                    )}
                    {onClearFilters && (
                        <div className="flex gap-2 bg-(--lighter-blue-700) px-2.5 py-1 rounded border border-(--cool-gray-500)/30 hover:bg-(--lighter-blue-600) transition-colors">
                            <button className='hover:cursor-pointer' onClick={onClearFilters}>
                                Clear All Filters
                            </button>
                        </div>
                    )}
                </div>
            )}
        </>
    );
};

export default FilteringPanel;