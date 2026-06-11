import { CustomTableCell } from "./CustomTableCell"
import { TableRow } from "flowbite-react";


export const CustomTableRow = ({ columns, document, onClick, onDeleteSuccess }) => {
    return (
        <TableRow
            className="cursor-pointer hover:bg-(--cool-gray-500)"
            onClick={onClick}
        >
            {columns.map((column) => (
                <CustomTableCell
                    key={column.key}
                    column={column}
                    document={document}
                    onDeleteSuccess={onDeleteSuccess}
                />
            ))}
        </TableRow>
    )
}