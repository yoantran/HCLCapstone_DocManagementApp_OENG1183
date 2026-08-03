import { TableHeader } from "./TableHeader.jsx"
import { CustomTableRow } from "./CustomTableRow.jsx"
import {Spinner, Table, TableBody, TableCell, TableRow} from "flowbite-react";

export const CustomTable = ({ columns, data, onRowClick, onDeleteSuccess, isLoading }) => {
    // log data for debugging
    // console.log("Rendering DocumentTable with data:", data);

    const safeData = data ?? []

    return (
        <Table className="bg-(--code-bg) text-white w-fit mx-auto">
            <TableHeader columns={columns} />

            <TableBody>
                {isLoading ? (
                    <TableRow>
                        <TableCell colSpan={columns.length} className="text-center py-8 text-slate-400">
                            <div className="flex flex-col items-center justify-center gap-3">
                                <Spinner size="lg" color="info" aria-label="Loading data..." />
                                <span>
                                    Loading data...
                                </span>
                            </div>
                        </TableCell>
                    </TableRow>
                ) : safeData.length === 0 ? (
                    <TableRow>
                        <TableCell colSpan={columns.length} className="text-center py-8 text-slate-400">
                            No data found.
                        </TableCell>
                    </TableRow>
                ) : (
                    safeData.map((row) => (
                    <CustomTableRow
                        key={row.id}
                        row={row}
                        columns={columns}
                        onClick={() => onRowClick?.(row)}
                        onDeleteSuccess={onDeleteSuccess}
                    />
                ))
                )}
            </TableBody>
        </Table>
    )
}