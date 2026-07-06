import {useEffect, useState} from "react";
import {CustomButton} from "../components/button/index.jsx";
import {getRequest} from "../api/apiHelpers.js";
import {CustomTable} from "../components/customTable/index.jsx";
import {adminManagementColumns} from "../components/customTable/columns.jsx";
import {DepartmentModal} from "../components/adminManagement/departmentModal/index.jsx";
import {UserModal} from "../components/adminManagement/userModal/index.jsx";


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