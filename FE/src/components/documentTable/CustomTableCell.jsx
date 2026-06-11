import { TableCell } from "flowbite-react";


export const CustomTableCell = ({ column, document, onDeleteSuccess }) => {
    if (column.Cell) {
        const CustomCell = column.Cell;

        return (
            <TableCell
                className="text-center"
            >
                <CustomCell
                    document={document}
                    className={column.className || ''}
                    onDeleteSuccess={onDeleteSuccess}
                    value={document[column.accessor]}
                />
            </TableCell>
        );
    }

    return (
        <TableCell
            className={column.className}
        >
            {document[column.accessor]}
        </TableCell>
    );
}