import { TableHeader } from "./TableHeader.jsx"
import { CustomTableRow } from "./CustomTableRow.jsx"
import { Table, TableBody } from "flowbite-react";

export const CustomTable = ({ columns, data, onRowClick, onDeleteSuccess }) => {
    // log data for debugging
    // console.log("Rendering DocumentTable with data:", data);

    return (
        <Table className="bg-(--code-bg) text-white w-fit mx-auto">
            <TableHeader columns={columns} />

            <TableBody>
                {(data ?? []).map((row) => (
                    <CustomTableRow
                        key={row.id}
                        row={row}
                        columns={columns}
                        onClick={() => onRowClick(row)}
                        onDeleteSuccess={onDeleteSuccess}
                    />
                ))}
            </TableBody>
        </Table>
    )
}