import {useEffect, useState} from "react";
import {getRequest} from "../api/apiHelpers.js";
import {CustomTable} from "../components/customTable/index.jsx";
import {adminManagementColumns} from "../components/customTable/columns.jsx";
import {DepartmentModal} from "../components/adminManagement/departmentModal/index.jsx";
import {UserModal} from "../components/adminManagement/userModal/index.jsx";
import FilteringPanel from "../components/filteringPanel/index.jsx";
import {Button} from "flowbite-react";
import { HiPlus } from "react-icons/hi";
import ConfigTable from "../components/filteringPanel/ConfigTable.jsx";
import SortTable from "../components/filteringPanel/SortTable.jsx";


export default function AdminManagement() {
    const [activeTab, setActiveTab] = useState('users');
    const [usersData, setUsersData] = useState([]);
    const [departmentsData, setDepartmentsData] = useState([]);

    const [editingUser, setEditingUser] = useState(null);
    const [editingDept, setEditingDept] = useState(null);

    const handleUserUpdate = (updatedUser) => {
        setUsersData(prev => prev.map(u => u.id === updatedUser.id ? updatedUser : u));
    };

    const handleDeptUpdate = (updatedDept) => {
        setDepartmentsData(prev => prev.map(d => d.id === updatedDept.id ? updatedDept : d));
    };


    // filteringPanel
    const [searchTerm, setSearchTerm] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [showConfigMenu, setShowConfigMenu] = useState(false);

    const [showFilterMenu, setShowFilterMenu] = useState(false);
    const [currentSort, setCurrentSort] = useState('date-desc');

    // Fetch data whenever the active tab switches
    useEffect(() => {
        // Fetch Users
        getRequest({ url: "/admin/users" })
            .then((response) => {
                const cleanUsers = Array.isArray(response)
                    ? response
                    : (response?.data || response?.users || []);
                setUsersData(cleanUsers);
            })
            .catch((error) => console.error("Error fetching users:", error));

        // Fetch Departments
        getRequest({ url: "/admin/departments" })
            .then((response) => {
                const cleanDepts = Array.isArray(response)
                    ? response
                    : (response?.data || response?.departments || []);
                setDepartmentsData(cleanDepts);
            })
            .catch((error) => console.error("Error fetching departments:", error));
    }, []);
        if (activeTab === 'users') {
            getRequest({ url: "/admin/users" })
                .then((response) => {
                    setUsersData(response ?? []);
                })
                .catch((error) => console.error("Error fetching users:", error));
        } else {
            getRequest({ url: "/admin/departments" })
                .then((response) => {
                    setDepartmentsData(response ?? []);
                })
                .catch((error) => console.error("Error fetching departments:", error));
        }

        // eslint-disable-next-line react-hooks/set-state-in-effect
        setCurrentPage(1);
    }, [activeTab]);

    const handleDeleteSuccess = (deletedId) => {
        if (activeTab === 'users') {
            setUsersData((prev) => prev.filter((user) => user.id !== deletedId));
        } else {
            setDepartmentsData((prev) => prev.filter((dept) => dept.id !== deletedId));
        }
    };

    const allColumns = adminManagementColumns(
        departmentsData,
        usersData,
        handleUserUpdate,
        handleDeptUpdate,
        setEditingUser,
        setEditingDept
    );

    const currentColumns = allColumns[activeTab.toUpperCase()] ?? [];
    const currentData = activeTab === 'users' ? usersData : departmentsData;

    const filteredData = currentData.filter((item) => {
        if (!searchTerm) return true;
        return Object.values(item).some((val) =>
            String(val).toLowerCase().includes(searchTerm.toLowerCase())
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
            const nameA = String( a.name || '');
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

    const displayedData = sortedData.slice((currentPage - 1) * 10, currentPage * 10);

    return (
        <>
            <div className="relative w-full">
                <FilteringPanel
                    currentPage={currentPage}
                    pageSize={10}
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

                    customButton={
                        <div className="flex items-center gap-2">
                            <Button disabled
                                onClick={() => console.log("Create User")}
                            >
                                < HiPlus className={"mr-2"} />
                                Create New User
                            </Button>
                            <Button disabled
                                onClick={() => console.log("Create Department")}
                            >
                                < HiPlus className={"mr-2"} />
                                Create New Department
                            </Button>
                        </div>
                    }
                />

                <div className="flex w-[95%] max-w-365 h-12 items-center bg-(--dark-blue-800) px-4 text-xs border-b border-r border-l border-(--ch-cool-gray) select-none">
                    <div className="flex items-center gap-2 bg-(--lighter-blue-700) px-2.5 py-1 rounded border border-(--cool-gray-500)/30">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]" />
                        <span className="text-(--ch-cool-gray)">Current Table:</span>
                        <span className="font-semibold capitalize text-white">
                        {activeTab === 'users' ? 'Users Management' : 'Departments Management'}
                        </span>
                    </div>
                </div>

                <ConfigTable
                    isOpen={showConfigMenu}
                    activeTab={activeTab}
                    onClose={() => setShowConfigMenu(false)}
                    onApply={(selectedTab) => setActiveTab(selectedTab)}
                />

                <SortTable
                    isOpen={showFilterMenu}
                    currentSort={currentSort}
                    onClose={() => setShowFilterMenu(false)}
                    onApply={(selectedSort) => {
                        setCurrentSort(selectedSort);
                    }}
                />

                <div className={"mt-5"}>
                    <CustomTable
                        data={displayedData}
                        columns={currentColumns}
                        onDeleteSuccess={handleDeleteSuccess}
                    />
                </div>

                <UserModal
                    show={!!editingUser}
                    user={editingUser}
                    // departments={departmentsData}
                    departments={Array.isArray(departmentsData) ? departmentsData : []}
                    onClose={() => setEditingUser(null)}
                    onUpdateSuccess={handleUserUpdate}
                    onDeleteSuccess={handleDeleteSuccess}
                />
                <DepartmentModal
                    show={!!editingDept}
                    department={editingDept}
                    // users={usersData}
                    users={Array.isArray(usersData) ? usersData : []}
                    onClose={() => setEditingDept(null)}
                    onUpdateSuccess={handleDeptUpdate}
                />
            </div>
        </>
    )
}