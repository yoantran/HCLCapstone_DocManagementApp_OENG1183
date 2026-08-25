import { useParams } from "react-router-dom";
import { useAuth } from '../context/AuthContext';
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PublicViewer } from "../components/documentProcess/view"
import { DocInfo } from "../components/documentProcess/view/docInfo/DocInfo";
import { getRequest, getBlobRequest } from "../api/apiHelpers";
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
    const { user } = useAuth();
    const isManager = user.role?.toUpperCase() === 'MANAGER';

    const { documentId } = useParams();
    const [document, setDocument] = useState(null);

    const [parsedAiResult, setParsedAiResult] = useState(null);
    const [redactedPreviewUrl, setRedactedPreviewUrl] = useState(null);
    const [previewError, setPreviewError] = useState(null);

    const navigate = useNavigate();

    const fetchDocument = useCallback(() => {
        const url = isManager
            ? `/documents/department/${documentId}`
            : `/documents/mine/${documentId}`;

        return getRequest({ url })
            .then((response) => {
                setDocument(response);

                // parse aiResult if available
                if (response.aiProcessed && response.aiResult) {
                    try {
                        const parsed = JSON.parse(response.aiResult);
                        setParsedAiResult(parsed);
                    } catch (e) {
                        console.error("Failed to parse aiResult:", e);
                    }
                }

                // fetch redacted preview for non-owners viewing documents
                if (response.aiProcessed && response.requesterIsOwner === false) {
                    getBlobRequest({ url: `/documents/${documentId}/redacted-preview` })
                        .then(setRedactedPreviewUrl)
                        .catch((err) => {
                            console.error("Failed to fetch redacted preview:", err);
                            setPreviewError(err.response?.status ?? null);    // only CSV unsupported
                        });
                }
            })
            .catch((error) =>
                console.error("Error fetching document:", error));
    }, [documentId, isManager]);

    useEffect(() => {
        fetchDocument();
    }, [fetchDocument]);

    // Poll while AI is still processing -- BE has no push mechanism into this
    // page (the WS notification only drives the bell), so this is the
    // simplest way to pick up aiResult/redacted-preview once it's ready
    // without a manual reload.
    useEffect(() => {
        if (!document || document.aiProcessed || document.aiProcessingFailed) {
            return;
        }
        const interval = setInterval(fetchDocument, 5000);
        return () => clearInterval(interval);
    }, [document, fetchDocument]);

    useEffect(() => {
        return () => {
            if (redactedPreviewUrl) {
                URL.revokeObjectURL(redactedPreviewUrl);
            }
        };
    }, [redactedPreviewUrl]);

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
                {
                    <DownloadButton
                        className="bg-(--bg) border"
                        file={document}
                        redactedPreviewUrl={
                            document.requesterIsOwner === false
                                ? redactedPreviewUrl
                                : null
                        }
                        isDownloadAllowed={
                            document.requesterIsOwner
                                ? Boolean(document.signedUrl)
                                : Boolean(redactedPreviewUrl)
                        }
                    />
                }
            </div>

            <DocInfo document={document} aiResult={parsedAiResult} />

            <div className="border-gray-700 border-b px-6 py-5 my-3">
                <h3 className="text-lg font-bold">
                    Document Preview
                </h3>
                <p className="mt-1 text-sm text-gray-500">
                    {document.requesterIsOwner
                        ? "Preview of the uploaded document"
                        : "Redacted preview with sensitive information protected"}
                </p>
            </div>

            {canView ? (
                <div className="flex justify-center bg-gray-100 p-6">
                    <div className="w-full max-w-6xl rounded-lg bg-white shadow italic">
                        {document.requesterIsOwner === false ? (
                            // non-owner: show redacted preview
                            previewError === 501 ? (
                                <p className="p-6 text-gray-500 text-sm">Preview not available for this format.</p>
                            ) : previewError === 422 ? (
                                <p className="p-6 text-gray-500 text-sm">AI processing not complete yet. Check back shortly.</p>
                            ) : redactedPreviewUrl ? (
                                <img src={redactedPreviewUrl} alt="Redacted preview" className="w-full rounded-lg" />
                            ) : (
                                <p className="p-6 text-gray-500 text-sm">Preview is not available</p>
                            )
                        ) : (
                            // owner: show original via signedUrl as before
                            <PublicViewer
                                fileUrl={document.signedUrl}
                                fileType={document.format?.toLowerCase()}
                            />
                        )}
                    </div>
                </div>
            ) : (
                <DocumentBlocked document={document} />
            )}
        </>
    )
}