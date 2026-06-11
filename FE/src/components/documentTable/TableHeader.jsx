import { TableRow, TableHead, TableHeadCell } from "flowbite-react";

export const TableHeader = ({ columns }) => {
    return (
        <TableHead>
            <TableRow>
                {columns.map((column) => (
                    <TableHeadCell
                        key={column.key}
                        className="text-center text-white bg-(--dark-blue-300)"
                    >
                        {column.label}
                    </TableHeadCell>
                ))}
            </TableRow>
        </TableHead>
    )
};