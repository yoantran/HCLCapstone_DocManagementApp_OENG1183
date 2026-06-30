import { StatusCell } from '../documentTable/cells/StatusCell.jsx';
import { DeleteAction } from '../action/DeleteAction.jsx';
import { formatDate } from '../../utils/formatFields.js';

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

export const adminManagementColumns = {
    USERS: [
        { key: 'id', label: 'ID', accessor: 'id' },
        { key: 'user', label: 'User', accessor: 'user' },
        { key: 'role', label: 'Role', accessor: 'role' },
        { key: 'department', label: 'Department', accessor: 'department' },
        { key: 'email', label: 'Email', accessor: 'email' },
        { key: 'phoneNumber', label: 'Phone Number', accessor: 'phoneNumber' },
        {
            key: 'action',
            label: 'Action',
            Cell: ({ row, onDeleteSuccess }) => (
                <DeleteAction
                    row={row}
                    nameKey="user"               // Points to row.user for the name
                    endpoint="/admin/users"       // Target deletion endpoint
                    entityLabel="User"           // Toast message modifier
                    className={deleteButtonStyle}
                    onDeleteSuccess={onDeleteSuccess}
                />
            )
        }
    ],
    DEPARTMENTS: [
        { key: 'id', label: 'ID', accessor: 'id' },
        { key: 'department', label: 'Department', accessor: 'department' },
        { key: 'boss', label: 'Boss', accessor: 'boss' },
        { key: 'staffs', label: 'Staffs', accessor: 'staffs' },
        {
            key: 'action',
            label: 'Action',
            Cell: ({ row, onDeleteSuccess }) => (
                <DeleteAction
                    row={row}
                    nameKey="department"         // Points to row.department for the name
                    endpoint="/admin/departments" // Target deletion endpoint
                    entityLabel="Department"     // Toast message modifier
                    className={deleteButtonStyle}
                    onDeleteSuccess={onDeleteSuccess}
                />
            )
        }
    ]
};