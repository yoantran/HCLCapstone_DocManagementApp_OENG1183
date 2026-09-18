import {useCallback, useEffect, useMemo, useState} from "react";
import { getRequest } from "../api/apiHelpers.js";
import { CustomTable } from "../components/customTable/index.jsx";
import { adminManagementColumns } from "../components/customTable/columns.jsx";
import FilteringPanel from "../components/filteringPanel/index.jsx";
import { Button } from "flowbite-react";
import { HiPlus } from "react-icons/hi";
import ConfigTable from "../components/filteringPanel/ConfigTable.jsx";
import SortTable from "../components/filteringPanel/SortTable.jsx";


export default function AdminManagement() {
    const [activeTab, setActiveTab] = useState('users');
    const [usersData, setUsersData] = useState([]);
    const [departmentsData, setDepartmentsData] = useState([]);

    // filteringPanel
    const [searchTerm, setSearchTerm] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [showConfigMenu, setShowConfigMenu] = useState(false);

    const [showFilterMenu, setShowFilterMenu] = useState(false);
    const [currentSort, setCurrentSort] = useState('date-desc');

    const [isLoading, setIsLoading] = useState(true)

    const fetchAllData = useCallback(() => {
        setIsLoading(true);
        Promise.all([
            getRequest({ url: "/admin/users" }),
            getRequest({ url: "/admin/departments" })
        ])
            .then(([usersRes, deptsRes]) => {
                const cleanUsers = Array.isArray(usersRes)
                    ? usersRes
                    : (usersRes?.data || usersRes?.users || []);
                const cleanDepts = Array.isArray(deptsRes)
                    ? deptsRes
                    : (deptsRes?.data || deptsRes?.departments || []);

                setUsersData(cleanUsers);
                setDepartmentsData(cleanDepts);
            })
            .catch((error) => console.error("Error fetching management data:", error))
            .finally(() => setIsLoading(false));
    }, []);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        fetchAllData();
    }, [fetchAllData]);

    const handleUserUpdate = useCallback((updatedUser) => {
        if (!updatedUser || !updatedUser.id) {
            fetchAllData();
            return;
        }
        setUsersData((prev) =>
            prev.map((u) => (u?.id === updatedUser.id ? updatedUser : u))
        );
        getRequest({ url: "/admin/departments" })
            .then((res) => setDepartmentsData(Array.isArray(res) ? res : res?.departments || []))
            .catch(console.error);
    }, [fetchAllData]);

    const handleDeptUpdate = useCallback((updatedDept) => {
        if (!updatedDept || !updatedDept.id) {
            fetchAllData();
            return;
        }
        setDepartmentsData((prev) =>
            prev.map((d) => (d?.id === updatedDept.id ? updatedDept : d))
        );
        getRequest({ url: "/admin/users" })
            .then((res) => setUsersData(Array.isArray(res) ? res : res?.users || []))
            .catch(console.error);
    }, [fetchAllData]);

    const handleDeleteSuccess = useCallback((deletedId) => {
        if (activeTab === 'users') {
            setUsersData((prev) => prev.filter((user) => user.id !== deletedId));
        } else {
            setDepartmentsData((prev) => prev.filter((dept) => dept.id !== deletedId));
        }
    }, [activeTab]);

    // Real, confirmed bug: adminManagementColumns() was called fresh on every
    // render with a brand-new inline `Cell` component each time. CustomTable
    // renders that as <CustomCell/>, so React treated it as a different
    // component type on every render (e.g. every keystroke in the search
    // box) and fully unmounted/remounted the row action cells -- silently
    // closing any open Manage/Delete popup out from under the user.
    const allColumns = useMemo(
        () => adminManagementColumns(
            departmentsData,
            usersData,
            handleUserUpdate,
            handleDeptUpdate
        ),
        [departmentsData, usersData, handleUserUpdate, handleDeptUpdate]
    );

    const currentColumns = allColumns[activeTab.toUpperCase()] ?? [];
    const currentData = activeTab === 'users' ? usersData : departmentsData;

    const filteredData = (currentData || [])
        .filter(Boolean)
        .filter((item) => {
            if (!searchTerm) return true;
            return Object.values(item).some((val) =>
                String(val ?? '').toLowerCase().includes(searchTerm.toLowerCase())
            );
        });

    const sortedData = [...filteredData].sort((a, b) => {
        if (currentSort === 'id-asc') {
            return String(a.id ?? '').localeCompare(String(b.id ?? ''), undefined, { numeric: true });
        }
        if (currentSort === 'id-desc') {
            return String(b.id ?? '').localeCompare(String(a.id ?? ''), undefined, { numeric: true });
        }
        if (currentSort === 'name-asc') {
            const nameA = String(a.name || '');
            const nameB = String(b.name || '');
            return nameA.localeCompare(nameB);
        }
        if (currentSort === 'name-desc') {
            const nameA = String(a.name || '');
            const nameB = String(b.name || '');
            return nameB.localeCompare(nameA);
        }
        if (currentSort === 'date-asc') {
            const timeA = a.createdAtDateTime ? new Date(a.createdAtDateTime).getTime() : 0;
            const timeB = b.createdAtDateTime ? new Date(b.createdAtDateTime).getTime() : 0;
            return timeA - timeB;
        }
        if (currentSort === 'date-desc') {
            const timeA = a.createdAtDateTime ? new Date(a.createdAtDateTime).getTime() : 0;
            const timeB = b.createdAtDateTime ? new Date(b.createdAtDateTime).getTime() : 0;
            return timeB - timeA;
        }
        return 0;
    });

    const ITEMS_PER_PAGE = 7;
    const displayedData = sortedData.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

    return (
        <>
            <div className="relative w-full">
                <FilteringPanel
                    currentPage={currentPage}
                    pageSize={ITEMS_PER_PAGE}
                    totalItems={filteredData.length}
                    onPageChange={(page) => setCurrentPage(page)}

                    showSettings={true}
                    onSettingsClick={() => setShowConfigMenu(!showConfigMenu)}
                    showSearch={true}
                    searchValue={searchTerm}
                    onSearchChange={(value) => {
                        setSearchTerm(value);
                        setCurrentPage(1);
                    }}
                    showFilter={true}
                    onFilterClick={() => setShowFilterMenu(!showFilterMenu)}

                    showRefresh={true}
                    onRefresh={fetchAllData}
                    isRefreshing={isLoading}

                    activeTabLabel={activeTab === 'users' ? 'Users Management' : 'Departments Management'}
                    onClearFilters={() => {
                        setSearchTerm('');
                        setCurrentSort('date-desc');
                        setActiveTab('users');
                        setCurrentPage(1);
                    }}

                    customButton={
                        <div className="flex items-center gap-2">
                            <Button
                                disabled
                                className="md:hidden"
                                onClick={() => console.log("Create Action")}
                            >
                                <HiPlus className="text-base" />
                            </Button>
                            <Button disabled
                                    className="hidden md:flex "
                                onClick={() => console.log("Create User")}
                            >
                                < HiPlus className={"text-base mr-2"} />
                                    Create New User
                            </Button>
                            <Button disabled
                                className="hidden md:flex"
                                onClick={() => console.log("Create Department")}
                            >
                                < HiPlus className={"text-base  mr-2"} />
                                Create New Department
                            </Button>
                        </div>
                    }
                />

                <ConfigTable
                    isOpen={showConfigMenu}
                    activeTab={activeTab}
                    onClose={() => setShowConfigMenu(false)}
                    onApply={(selectedTab) => {
                        setActiveTab(selectedTab);
                        setCurrentPage(1);
                    }}
                />

                <SortTable
                    isOpen={showFilterMenu}
                    currentSort={currentSort}
                    onClose={() => setShowFilterMenu(false)}
                    onApply={(selectedSort) => {
                        setCurrentSort(selectedSort);
                    }}
                />

                <div className={"mt-2"}>
                    <CustomTable
                        data={displayedData}
                        columns={currentColumns}
                        onDeleteSuccess={handleDeleteSuccess}
                        isLoading={isLoading}
                    />
                </div>
            </div>
        </>
    )
}