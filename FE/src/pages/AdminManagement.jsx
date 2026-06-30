import {useState} from "react";
import {CustomButton} from "../components/button/index.jsx";

export default function AdminManagement() {
    const [activeTab, setActiveTab] = useState('users');

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
            </div>
        </>
    )
}