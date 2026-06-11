import { TableHeader } from "./TableHeader"
import { CustomTableRow } from "./CustomTableRow"
import { Table, TableBody } from "flowbite-react";

export const DocumentTable = ({ columns, data, onRowClick, onDeleteSuccess }) => {
    // log data for debugging
    // console.log("Rendering DocumentTable with data:", data);

    return (
        <Table className="bg-(--code-bg) text-white">
            <TableHeader columns={columns} />

            <TableBody>
                {data.map((document) => (
                    <CustomTableRow
                        key={document.id}
                        document={document}
                        columns={columns}
                        onClick={() => onRowClick(document)}
                        onDeleteSuccess={onDeleteSuccess}
                    />
                ))}
            </TableBody>
        </Table>
    )
}