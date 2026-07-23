import { StatusCell } from '../documentTable/cells/StatusCell.jsx';
import { DeleteAction } from '../action/DeleteAction.jsx';
import { formatDate } from '../../utils/formatFields.js';
import { ManageAction } from "../action/ManageAction.jsx";
import { UserModal } from "../adminManagement/userModal/index.jsx";
import { DepartmentModal } from "../adminManagement/departmentModal/index.jsx";

const deleteButtonStyle = 'border-2 border-red-500 text-red-500 bg-(--code-bg) hover:bg-red-500 hover:text-white'

export const columnsByRole = {
    STAFF: [
        {
            key: 'secureStatus',
            label: '',
            Cell: StatusCell,
        },
        {
            key: 'name',
            label: 'Name',
            accessor: 'name',
        },
        {
            key: 'format',
            label: 'Format',
            accessor: 'format',
            className: 'text-center',
        },
        {
            key: 'date',
            label: 'Date',
            accessor: 'uploadedDateTime',
            Cell: ({ value }) => formatDate(value),
        },
        {
            key: 'action',
            label: 'Action',
            Cell: DeleteAction,
            className: deleteButtonStyle
        },
    ],

    MANAGER: [
        {
            key: 'secureStatus',
            label: '',
            Cell: StatusCell,
        },
        {
            key: 'name',
            label: 'Name',
            accessor: 'name',
            className: 'text-left min-w-44 sm:max-w-52 break-words',
        },
        {
            key: 'format',
            label: 'Format',
            accessor: 'format',
            className: 'text-center',
        },
        {
            key: 'type',
            label: 'Type',
            accessor: 'type',
            className: 'text-center',
        },
        {
            key: 'submitter',
            label: 'Uploaded By',
            accessor: 'uploaderName',
        },
        {
            key: 'date',
            label: 'Date',
            accessor: 'uploadedDateTime',
            Cell: ({ value }) => formatDate(value),
        },
        {
            key: 'action',
            label: 'Action',
            Cell: DeleteAction,
            className: deleteButtonStyle
        },
    ],

    ADMIN: [
        {
            key: 'secureStatus',
            label: '',
            Cell: StatusCell,
            className: '',
        },
        {
            key: 'name',
            label: 'Name',
            accessor: 'name',
            className: '',
        },
        {
            key: 'format',
            label: 'Format',
            accessor: 'format',
            className: 'text-center',
        },
        {
            key: 'type',
            label: 'Type',
            accessor: 'type',
            className: 'text-center',
        },
        {
            key: 'submitter',
            label: 'Uploaded By',
            accessor: 'uploaderName',
        },
        {
            key: 'date',
            label: 'Date',
            accessor: 'uploadedDateTime',
            Cell: ({ value }) => formatDate(value),
        },
        {
            key: 'department',
            label: 'Department',
            accessor: 'departmentName',
            className: 'text-center',
        },
        {
            key: 'action',
            label: 'Action',
            Cell: DeleteAction,
            className: deleteButtonStyle
        },
    ],
};

export const adminManagementColumns = (
    depsList, usersList, refreshUsers, refreshDeps
) => ({
    USERS: [
        // { key: 'id', label: 'ID', accessor: 'id' },
        { key: 'name', label: 'User', accessor: 'name' },
        { key: 'role', label: 'Role', accessor: 'role' },
        { key: 'departmentName', label: 'Department', accessor: 'departmentName' },
        { key: 'email', label: 'Email', accessor: 'email' },
        { key: 'phoneNumber', label: 'Phone Number', accessor: 'phoneNumber' },
        {
            key: 'action',
            label: 'Action',
            Cell: ({ row, onDeleteSuccess }) => {
                const item = row;
                return (
                    <div className="flex items-center justify-center gap-2">
                        <ManageAction
                            row={item}
                            ModalComponent={UserModal}
                            modalProps={{ departments: depsList }}
                            onSuccess={refreshUsers}
                        />
                        <DeleteAction
                            row={item}
                            itemName={item?.name}
                            endpoint="/admin/users"
                            entityLabel="User"
                            className={deleteButtonStyle}
                            onDeleteSuccess={onDeleteSuccess}
                        />
                    </div>
                )
            }
        }
    ],
    DEPARTMENTS: [
        // { key: 'id', label: 'ID', accessor: 'id' },
        { key: 'name', label: 'Department', accessor: 'name' },
        { key: 'managerName', label: 'Manager', accessor: 'managerName' },
        {
            key: 'action',
            label: 'Action',
            Cell: ({ row, document, onDeleteSuccess }) => {
                const item = row || document;
                return (
                    <div className="flex items-center justify-center gap-2">
                        <ManageAction
                            row={item}
                            ModalComponent={DepartmentModal}
                            modalProps={{ users: usersList }}
                            onSuccess={refreshDeps}
                        />
                        <DeleteAction
                            row={item}
                            itemName={item?.name}
                            endpoint="/admin/departments"
                            entityLabel="Department"
                            className={deleteButtonStyle}
                            onDeleteSuccess={onDeleteSuccess}
                        />
                    </div>
                )
            }
        }
    ]
});

export const auditLogColumns = () => [
    {
        key: "timestamp",
        label: "Timestamp",
        accessor: 'timestamp',
    },
    {key: "userId", label:"User",
        accessor: "userId",
    },
    {key: "email", label: "Email", accessor: 'email' },
    {key: "role", label: "Role", accessor: 'role' },
    {key: "action", label: "Action", accessor: 'action' },
    {
        key: "durationMs",
        label: "Execution (ms)",
        accessor: "durationMs",
    },
    {key: "clientIp", label: "Client Ip", accessor: 'clientIp' },
]