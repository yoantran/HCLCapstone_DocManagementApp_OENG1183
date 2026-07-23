import FilteringPanel from "../components/filteringPanel/index.jsx";
import {CustomTable} from "../components/customTable/index.jsx";
import {useCallback, useEffect, useMemo, useState} from "react";
import {getRequest} from "../api/apiHelpers.js";
import {auditLogColumns} from "../components/customTable/columns.jsx";
import SortTable from "../components/filteringPanel/SortTable.jsx";

export default function AuditLog() {
    const [logs, setLogs] = useState([]);
    const [isLoading, setIsLoading] = useState(false);

    const [searchTerm, setSearchTerm] = useState("")
    const [sortOrder, setSortOrder] = useState("date-desc")

    const [showFilterMenu, setShowFilterMenu] = useState(false);

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

    const handleClearFilters = () => {
        setSearchTerm("");
        setSortOrder("date-desc");
        setCurrentPage(1);
    };

    const filteredLogs = useMemo(() => {
        if (!searchTerm.trim()) return logs;

        const term = searchTerm.toLowerCase();
        return logs.filter((log) => {
            return (
                log.email?.toLowerCase().includes(term) ||
                log.action?.toLowerCase().includes(term) ||
                log.role?.toLowerCase().includes(term) ||
                log.path?.toLowerCase().includes(term) ||
                log.clientIp?.toLowerCase().includes(term) ||
                String(log.status).includes(term)
            );
        })
    }, [logs, searchTerm])

    const sortedLogs = [...filteredLogs].sort((a, b) => {
        if (sortOrder === 'id-asc') {
            return String(a.userId ?? '').localeCompare(String(b.userId ?? ''), undefined, { numeric: true });
        }
        if (sortOrder === 'id-desc') {
            return String(b.userId ?? '').localeCompare(String(a.userId ?? ''), undefined, { numeric: true });
        }
        if (sortOrder === 'name-asc') {
            const nameA = String(a.name || '');
            const nameB = String(b.name || '');
            return nameA.localeCompare(nameB);
        }
        if (sortOrder === 'name-desc') {
            const nameA = String(a.name || '');
            const nameB = String(b.name || '');
            return nameB.localeCompare(nameA);
        }
        if (sortOrder === 'date-asc') {
            const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
            const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
            return timeA - timeB;
        }
        if (sortOrder === 'date-desc') {
            const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
            const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
            return timeB - timeA;
        }
        return 0;
    });

    const paginatedLogs = useMemo(() => {
        const startIndex = (currentPage - 1) * PAGE_SIZE;
        return sortedLogs.slice(startIndex, startIndex + PAGE_SIZE);
    }, [sortedLogs, currentPage]);

    const handleSearchChange = (value) => {
        setSearchTerm(value);
        setCurrentPage(1);
    };

    const handleSortChange = (order) => {
        setSortOrder(order);
        setCurrentPage(1);
    };

    const formattedLogs = useMemo(() => {
        return paginatedLogs.map((log) => ({
            ...log,
            displayTimestamp: log.timestamp
                ? new Date(log.timestamp).toLocaleString('vi-VN', { hour12: false })
                : 'N/A',
            displayUserId: log.userId ? `${log.userId.slice(0, 3)}...` : 'N/A',
            displayRole: log.role ? log.role.replace('ROLE_', '') : 'N/A',
            displayAction: log.action ? log.action.split('.').pop() : 'N/A',
            displayIp: log.clientIp === "0:0:0:0:0:0:0:1" ? "127.0.0.1" : log.clientIp
        }));
    }, [paginatedLogs]);

    return (
        <>
            <div className="relative w-full">
                <FilteringPanel
                    currentPage={currentPage}
                    pageSize={PAGE_SIZE}
                    totalItems={sortedLogs.length}
                    onPageChange={(page) => setCurrentPage(page)}

                    showSearch={true}
                    searchValue={searchTerm}
                    onSearchChange={handleSearchChange}

                    sortOrder={sortOrder}
                    onSortChange={handleSortChange}

                    showFilter={true}
                    onFilterClick={() => setShowFilterMenu(true)}

                    onClearFilters={handleClearFilters}
                    onRefresh={fetchLogs}
                    isRefreshing={isLoading}

                    showSettings={false}
                />
            </div>
            <div className="">
                <SortTable
                    isOpen={showFilterMenu}
                    currentSort={sortOrder}
                    onClose={() => setShowFilterMenu(false)}
                    onApply={(selectedSort) => {
                        setSortOrder(selectedSort);
                        setCurrentPage(1);
                        setShowFilterMenu(false);
                    }}
                />
            </div>
            <div className="mt-5 w-full rounded-lg">
                <CustomTable
                    data={formattedLogs}
                    columns={auditLogColumns()}
                />
            </div>
        </>
    );
}