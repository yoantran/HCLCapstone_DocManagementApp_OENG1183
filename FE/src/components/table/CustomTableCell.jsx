import { TableCell } from "flowbite-react";


export const CustomTableCell = ({ column, row, onDeleteSuccess }) => {
    const cellValue = column.accessor ? row[column.accessor] : row[column.key];

    if (column.Cell) {
        const CustomCell = column.Cell;

        return (
            <TableCell
                className="text-center"
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
            className={column.className}
        >
            {cellValue}
        </TableCell>
    );
}