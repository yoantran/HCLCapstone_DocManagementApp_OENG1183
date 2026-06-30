import { StatusCell } from './cells/StatusCell';
import { DeleteAction } from './cells/DeleteAction';
import { formatDate } from '../../utils/formatFields';

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
        { key: 'action', label: 'Action', Cell: ManageActionCell }
    ],
    DEPARTMENTS: [
        { key: 'id', label: 'ID', accessor: 'id' },
        { key: 'department', label: 'Department', accessor: 'department' },
        { key: 'boss', label: 'Boss', accessor: 'boss' },
        { key: 'staffs', label: 'Staffs', accessor: 'staffs' },
        { key: 'action', label: 'Action', Cell: ManageActionCell }
    ]
};