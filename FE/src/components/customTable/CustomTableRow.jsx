import { CustomTableCell } from "./CustomTableCell.jsx"
import { TableRow } from "flowbite-react";


export const CustomTableRow = ({ columns, row, onClick, onDeleteSuccess }) => {
    return (
        <TableRow
            className="cursor-pointer hover:bg-(--cool-gray-500)"
            onClick={onClick}
        >
            {columns.map((column) => (
                <CustomTableCell
                    key={column.key}
                    column={column}
                    row={row}
                    onDeleteSuccess={onDeleteSuccess}
                />
            ))}
        </TableRow>
    )
}