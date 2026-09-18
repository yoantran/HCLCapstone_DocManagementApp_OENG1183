import { CustomTableCell } from "./CustomTableCell.jsx"
import { TableRow } from "flowbite-react";


export const CustomTableRow = ({ columns, row, onClick, onDeleteSuccess, isHighlighted }) => {
    return (
        <TableRow
            className={`cursor-pointer hover:bg-(--cool-gray-500) ${
                isHighlighted ? "bg-(--light-blue)/20 ring-2 ring-inset ring-(--light-blue)" : ""
            }`}
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