import { TableCell } from "flowbite-react";


export const CustomTableCell = ({ column, row, onDeleteSuccess }) => {
    const cellValue = column.accessor ? row[column.accessor] : row[column.key];

    if (column.Cell) {
        const CustomCell = column.Cell;

        return (
            <TableCell
                className="text-center align-middle py-1.5 px-3 text-sm"
            >
                <CustomCell
                    row={row}
                    className={column.className || ''}
                    onDeleteSuccess={onDeleteSuccess}
                    value={cellValue}
                />
            </TableCell>
        );
    }

    return (
        <TableCell
            className={`text-center align-middle md:w-44 h-5 text-sm ${column.className}`}
        >
            {cellValue}
        </TableCell>
    );
}