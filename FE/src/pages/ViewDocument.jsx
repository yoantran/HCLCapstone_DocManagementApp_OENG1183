import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PublicViewer } from "../components/documentProcess/view"
import { DocInfo } from "../components/documentProcess/view/docInfo/DocInfo";
import { getRequest } from "../api/apiHelpers";
import { DeleteAction } from "../components/action/DeleteAction.jsx";
import { DownloadButton } from "../components/documentTable/modal/DownloadButton";
import { Alert } from "flowbite-react";
import { getScanStatusInfo } from "../utils/scanHelper.js";

function DocumentBlocked({ document }) {
    const scanInfo = getScanStatusInfo(document);

    return (
        <Alert color={scanInfo.color} className="mt-6 items-center py-10">
            <h3 className="font-bold mb-2">
                This document cannot be viewed.
            </h3>

            <p>{scanInfo.description}</p>
        </Alert>
    );
}

export default function ViewDocument() {
    const { documentId } = useParams();
    const [document, setDocument] = useState(null);
    const navigate = useNavigate();

    useEffect(() => {
        getRequest({ url: `/documents/mine/${documentId}` })
            .then((response) => {
                // console.log("Fetched document:", response);
                setDocument(response);
            })
            .catch((error) => {
                console.error("Error fetching document:", error);
            });
    }, [documentId]);

    if (!document) return null;
    const canView = document.accessible;

    return (
        <>
            <div className="flex flex-row gap-5 justify-end">
                <DeleteAction
                    document={document}
                    className="bg-(--bg) border border-red-500 text-red-500"
                    onDeleteSuccess={() => {
                        navigate("../documents");
                    }}
                />
                <DownloadButton
                    className="bg-(--bg) border"
                    file={document}
                />
            </div>

            <DocInfo document={document} />

            {canView ? (
                <div className="flex justify-center bg-gray-100 p-6">
                    <div className="w-full max-w-6xl rounded-lg bg-white shadow">
                        <PublicViewer
                            fileUrl={document.signedUrl}
                            fileType={document.format?.toLowerCase()}
                        />
                    </div>
                </div>
            ) : (
                <DocumentBlocked document={document} />
            )}

        </>
    )
}