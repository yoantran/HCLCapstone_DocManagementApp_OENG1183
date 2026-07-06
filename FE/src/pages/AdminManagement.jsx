import {useEffect, useState} from "react";
import {getRequest} from "../api/apiHelpers.js";
import {CustomTable} from "../components/customTable/index.jsx";
import {adminManagementColumns} from "../components/customTable/columns.jsx";
import FilteringPanel from "../components/filteringPanel/index.jsx";
import {Button} from "flowbite-react";
import { HiPlus } from "react-icons/hi";
import ConfigTable from "../components/filteringPanel/ConfigTable.jsx";


export default function AdminManagement() {
    const [activeTab, setActiveTab] = useState('users');
    const [usersData, setUsersData] = useState([]);
    const [departmentsData, setDepartmentsData] = useState([]);

    // filteringPanel
    const [searchTerm, setSearchTerm] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [showConfigMenu, setShowConfigMenu] = useState(false);

    // Fetch data whenever the active tab switches
    useEffect(() => {
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

    const currentColumns = adminManagementColumns[activeTab.toUpperCase()] ?? [];
    const currentData = activeTab === 'users' ? usersData : departmentsData;

    const filteredData = currentData.filter((item) => {
        if (!searchTerm) return true;
        return Object.values(item).some((val) =>
            String(val).toLowerCase().includes(searchTerm.toLowerCase())
        );
    });

    const displayedData = filteredData.slice((currentPage - 1) * 10, currentPage * 10);

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
                    onFilterClick={() => console.log("Filter open")}

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

                <ConfigTable
                    isOpen={showConfigMenu}
                    activeTab={activeTab}
                    onClose={() => setShowConfigMenu(false)}
                    onApply={(selectedTab) => setActiveTab(selectedTab)}
                />
                <div className={"mt-5"}>
                    <CustomTable
                        data={displayedData}
                        columns={currentColumns}
                        onDeleteSuccess={handleDeleteSuccess}
                    />
                </div>
            </div>
        </>
    )
}