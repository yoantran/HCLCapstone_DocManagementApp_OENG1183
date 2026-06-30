import {useEffect, useState} from "react";
import {CustomButton} from "../components/button/index.jsx";
import {getRequest} from "../api/apiHelpers.js";
import {DocumentModal} from "../components/documentTable/modal/index.jsx";
import {DocumentTable} from "../components/documentTable/index.jsx";
import {adminManagementColumns} from "../components/documentTable/columns.jsx";


// const userColumns = [
//     { label: "ID", key: "id" },
//     { label: "User", key: "user" },
//     { label: "Role", key: "role" },
//     { label: "Department", key: "department" },
//     { label: "Email", key: "email" },
//     { label: "Phone Number", key: "phoneNumber" },
//     { label: "Action", key: "action" }
// ];
//
// const departmentColumns = [
//     { label: "ID", key: "id" },
//     { label: "Department", key: "department" },
//     { label: "Boss", key: "boss" },
//     { label: "Staffs", key: "staffs" },
//     { label: "Action", key: "action" }
// ];

export default function AdminManagement() {
    const [activeTab, setActiveTab] = useState('users');

    const [usersData, setUsersData] = useState([]);
    const [departmentsData, setDepartmentsData] = useState([]);
    //
    // const [openModal, setOpenModal] = useState(false);
    // const [selectedItem, setSelectedItem] = useState(null);

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

    // const handleRowClick = (item) => {
    //     setSelectedItem(item);
    //     setOpenModal(true);
    // };
    //
    // const handleCloseModal = () => {
    //     setSelectedItem(null);
    //     setOpenModal(false);
    // };
    //
    // const handleDeleteSuccess = (deletedId) => {
    //     if (activeTab === 'users') {
    //         setUsersData((prev) => prev.filter((user) => user.id !== deletedId));
    //     } else {
    //         setDepartmentsData((prev) => prev.filter((dept) => dept.id !== deletedId));
    //     }
    //     setSelectedItem(null);
    //     setOpenModal(false);
    // };
    //
    // const currentColumns = activeTab === 'users' ? userColumns : departmentColumns;
    // const currentData = activeTab === 'users' ? usersData : departmentsData;

    // const columns = adminManagementColumns[user.role?.toUpperCase()] ?? [];

    return (
        <>
            <div>
                <h2>
                    {activeTab === 'users' ? 'User Management' : 'Department Management'}
                </h2>
                <div className={"inline-flex"}>
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
                {/*<div>*/}
                {/*    <DocumentTable*/}
                {/*        data={currentData}*/}
                {/*        columns={currentColumns}*/}
                {/*        onRowClick={handleRowClick}*/}
                {/*        onDeleteSuccess={handleDeleteSuccess}*/}
                {/*    />*/}
                {/*</div>*/}
                {/*<DocumentModal*/}
                {/*    document={selectedItem}*/}
                {/*    show={openModal}*/}
                {/*    onClose={handleCloseModal}*/}
                {/*    onDeleteSuccess={handleDeleteSuccess}*/}
                {/*/>*/}
            </div>
        </>
    )
}