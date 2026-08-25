import { useAuth } from '../context/AuthContext';
import {useCallback, useEffect, useRef, useState} from 'react';
import { useLocation } from 'react-router-dom';
import { columnsByRole } from '../components/customTable/columns.jsx';
import { CustomTable } from '../components/customTable/index.jsx';
import { DocumentModal } from '../components/documentTable/modal';
import { getRequest } from '../api/apiHelpers';
import FilteringPanel from '../components/filteringPanel/index.jsx';
import SortTable from '../components/filteringPanel/SortTable.jsx';
import ConfigTable from '../components/filteringPanel/ConfigTable.jsx';

export default function Documents() {
    const { user } = useAuth();
    const location = useLocation();

    // Set by NotificationBell's navigate(state: { highlightDocumentId }) --
    // read once on mount, not tracked against location changes, since we
    // only want the jump-and-highlight to happen for the navigation that
    // actually carried it (a later re-render/back-nav to this same route
    // shouldn't re-trigger it).
    const [highlightedId] = useState(location.state?.highlightDocumentId ?? null);
    const hasJumpedToHighlight = useRef(false);

    const [documents, setDocuments] = useState([]);
    const [openModal, setOpenModal] = useState(false);
    const [selectedDocument, setSelectedDocument] = useState(null);

    const isManager = user.role?.toUpperCase() === 'MANAGER';
    const [activeTab, setActiveTab] = useState(isManager ? 'department' : 'mine');
    const [showConfigMenu, setShowConfigMenu] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [showFilterMenu, setShowFilterMenu] = useState(false);
    const [currentSort, setCurrentSort] = useState('date-desc');

    const [isLoading, setIsLoading] = useState(true)

    const handleRowClick = (document) => {
        setSelectedDocument(document);
        setOpenModal(true)
    };

    const handleCloseModal = () => {
        setSelectedDocument(null)
        setOpenModal(false)
    }

    const handleDeleteSuccess = (deletedId) => {
        setDocuments((prev) =>
            prev.filter((doc) => doc.id !== deletedId)
        );

        setSelectedDocument(null);
        setOpenModal(false);
    };
    const fetchDocuments = useCallback(() => {
        setIsLoading(true);
        const url = isManager ? "/documents/department" : "/documents/mine";

        getRequest({ url })
            .then((response) => {
                const sorted = (response ?? []).sort((a, b) =>
                    new Date(b.uploadedDateTime) - new Date(a.uploadedDateTime)
                );
                setDocuments(sorted);
            })
            .catch((error) => console.error("Error fetching documents:", error))
            .finally(() => setIsLoading(false));
    }, [isManager]);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        fetchDocuments()
    }, [fetchDocuments]);

    // get column pattern based on role
    const columns = columnsByRole[user.role?.toUpperCase()] ?? [];

    const sortDocuments = (docs, sort) => {
        const sorted = [...docs];
        switch (sort) {
            case 'date-desc':
                return sorted.sort((a, b) => new Date(b.uploadedDateTime) - new Date(a.uploadedDateTime));
            case 'date-asc':
                return sorted.sort((a, b) => new Date(a.uploadedDateTime) - new Date(b.uploadedDateTime));
            case 'id-asc':
                return sorted.sort((a, b) => a.id.localeCompare(b.id));
            case 'id-desc':
                return sorted.sort((a, b) => b.id.localeCompare(a.id));
            case 'name-asc':
                return sorted.sort((a, b) => a.name.localeCompare(b.name));
            case 'name-desc':
                return sorted.sort((a, b) => b.name.localeCompare(a.name));
            default:
                return sorted;
        }
    };

    const tabFilteredDocuments = isManager && activeTab === 'mine'
        ? documents.filter((doc) => doc.uploaderId === user.id)
        : documents;

    const filteredDocuments = tabFilteredDocuments.filter((doc) =>
        doc.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        doc.type?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        doc.uploaderName?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const sortedDocuments = sortDocuments(filteredDocuments, currentSort); // ← add

    const pageSize = 7;
    const paginatedDocuments = sortedDocuments.slice( // ← use sortedDocuments
        (currentPage - 1) * pageSize,
        currentPage * pageSize
    );

    // Jump to whichever page the notification's target document actually
    // lands on, once (not on every sort/filter change afterward -- once the
    // user starts interacting with the table, their own navigation wins).
    useEffect(() => {
        if (!highlightedId || hasJumpedToHighlight.current || sortedDocuments.length === 0) {
            return;
        }
        const index = sortedDocuments.findIndex((doc) => doc.id === highlightedId);
        if (index !== -1) {
            setCurrentPage(Math.floor(index / pageSize) + 1);
        }
        hasJumpedToHighlight.current = true;
    }, [highlightedId, sortedDocuments, pageSize]);

    return (
        <>
            <FilteringPanel
                currentPage={currentPage}
                pageSize={pageSize}
                totalItems={filteredDocuments.length}
                onPageChange={(page) => setCurrentPage(page)}

                showSettings={isManager}
                onSettingsClick={() => setShowConfigMenu(!showConfigMenu)}
                showSearch={true}
                searchValue={searchTerm}
                onSearchChange={(value) => {
                    setSearchTerm(value);
                    setCurrentPage(1);
                }}

                showFilter={true}
                onFilterClick={() => setShowFilterMenu(!showFilterMenu)}

                showRefresh={true}
                onRefresh={fetchDocuments}
                isRefreshing={isLoading}

                activeTabLabel={activeTab === 'mine' ? 'My Documents' : 'Department Documents'}
                onClearFilters={() => {
                    setSearchTerm('');
                    setCurrentSort('date-desc');
                    setActiveTab(isManager ? 'department' : 'mine');
                    setCurrentPage(1);
                }}
            />

            <ConfigTable
                isOpen={showConfigMenu}
                activeTab={activeTab === 'mine' ? 'mine' : 'department'}
                onClose={() => setShowConfigMenu(false)}
                onApply={(selectedTab) => setActiveTab(selectedTab)}
                options={[
                    { value: 'mine', label: 'My Documents' },
                    { value: 'department', label: 'Department Documents' },
                ]}
            />

            <SortTable
                isOpen={showFilterMenu}
                currentSort={currentSort}
                onClose={() => setShowFilterMenu(false)}
                onApply={(selectedSort) => {
                    setCurrentSort(selectedSort);
                }}
            />

            <div className='m-2' />

            <CustomTable
                data={paginatedDocuments}
                columns={columns}
                onRowClick={handleRowClick}
                onDeleteSuccess={handleDeleteSuccess}
                isLoading={isLoading}
                highlightedId={highlightedId}
            />

            <DocumentModal
                document={selectedDocument}
                show={openModal}
                onClose={handleCloseModal}
                onDeleteSuccess={handleDeleteSuccess}
            />
        </>
    );
}