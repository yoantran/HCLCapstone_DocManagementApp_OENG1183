import {useEffect, useState} from "react";
import {CustomButton} from "../components/button/index.jsx";
import {getRequest} from "../api/apiHelpers.js";
import {CustomTable} from "../components/customTable/index.jsx";
import {adminManagementColumns} from "../components/customTable/columns.jsx";


export default function AdminManagement() {
    const [activeTab, setActiveTab] = useState('users');
    const [usersData, setUsersData] = useState([]);
    const [departmentsData, setDepartmentsData] = useState([]);

    // Fetch data whenever the active tab switches
    useEffect(() => {
        if (activeTab === 'users') {
            // Adjust endpoint URL to match your real user/document backend route
            getRequest({ url: "/admin/users" })
                .then((response) => {
                    setUsersData(response ?? []);
                })
                .catch((error) => console.error("Error fetching users:", error));
        } else {
            // Adjust endpoint URL to match your real department backend route
            getRequest({ url: "/admin/departments" })
                .then((response) => {
                    setDepartmentsData(response ?? []);
                })
                .catch((error) => console.error("Error fetching departments:", error));
        }
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

    return (
        <>
            <div>
                <h2>
                    {activeTab === 'users' ? 'User Management' : 'Department Management'}
                </h2>
                <div className={"inline-flex py-4 gap-2"}>
                    <CustomButton
                        onClick={() => setActiveTab('users')}
                        pill
                        color={activeTab === 'users' ? 'primary' : 'alternative'}
                        className={"transition-colors"}
                    >
                        User Management
                    </CustomButton>
                    <CustomButton
                        onClick={() => setActiveTab('departments')}
                        pill
                        color={activeTab === 'departments' ? 'primary' : 'alternative'}
                        className={"transition-colors"}
                    >
                        Department Management
                    </CustomButton>
                </div>
                <div>
                    <CustomTable
                        data={currentData}
                        columns={currentColumns}
                        onDeleteSuccess={handleDeleteSuccess}
                    />
                </div>
            </div>
        </>
    )
}