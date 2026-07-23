import FilteringPanel from "../components/filteringPanel/index.jsx";
import {CustomTable} from "../components/customTable/index.jsx";
import {useCallback, useEffect, useState} from "react";
import {getRequest} from "../api/apiHelpers.js";
import {auditLogColumns} from "../components/customTable/columns.jsx";

export default function AuditLog() {
    const [logs, setLogs] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);

    const PAGE_SIZE = 10;

    const fetchLogs = useCallback(async () => {
        setIsLoading(true);
        try {
            const response = await getRequest({
                url:  '/admin/audit-logs',
            });
            setLogs(response);
        } catch (error) {
            console.error("Error fetching audit logs:", error);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        fetchLogs();
    }, [fetchLogs]);

    const sortedLogs = [...logs].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    const paginatedLogs = sortedLogs.slice(
        (currentPage - 1) * PAGE_SIZE,
        currentPage * PAGE_SIZE
    )
    return (
        <>
            <div>
                <h1>System Audit Logs</h1>
                <button
                onClick= {fetchLogs}
                disabled={isLoading}
                >
                    <svg
                        className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    {isLoading ? 'Refreshing...' : 'Refresh Logs'}
                </button>
            </div>
            <FilteringPanel
                currentPage={currentPage}
                pageSize={PAGE_SIZE}
                totalItems={logs.length}
                onPageChange={(page) => setCurrentPage(page)}

                showSettings={false}
                showFilter={false}
                showSearch={true}
            />


            <div className='m-8' />

            <CustomTable
                data={paginatedLogs}
                columns={auditLogColumns()}
            />

        </>
    );
}