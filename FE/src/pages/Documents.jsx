import { useAuth } from '../context/AuthContext';
import { useEffect, useState } from 'react';
import { columnsByRole } from '../components/customTable/columns.jsx';
import { CustomTable } from '../components/customTable/index.jsx';
import { DocumentModal } from '../components/documentTable/modal';
import { getRequest } from '../api/apiHelpers';

export default function Documents() {
    const { user } = useAuth();

    const [documents, setDocuments] = useState([]);
    const [openModal, setOpenModal] = useState(false);
    const [selectedDocument, setSelectedDocument] = useState(null);

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

    useEffect(() => {
        const isManager = user.role?.toUpperCase() === 'MANAGER';
        const url = isManager ? "/documents/department" : "/documents/mine";

        getRequest({ url })
            .then((response) => setDocuments(response ?? []))
            .catch((error) => console.error("Error fetching documents:", error));
    }, []);

    // get column pattern based on role
    const columns = columnsByRole[user.role?.toUpperCase()] ?? [];

    return (
        <>
            <CustomTable
                data={documents}
                columns={columns}
                onRowClick={handleRowClick}
                onDeleteSuccess={handleDeleteSuccess}
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