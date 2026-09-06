import { useNavigate } from 'react-router-dom';
import { useCallback, useEffect, useState } from "react";
import { useAuth } from '../../../context/AuthContext.jsx';
import {
    Modal,
    ModalHeader,
    ModalBody,
    Button,
    Card,
    Alert
} from "flowbite-react";
import { DownloadButton } from "./DownloadButton";
import { DeleteAction } from "../../action/DeleteAction.jsx";
import { formatDate, formatSize } from '../../../utils/formatFields';
import { getScanStatusInfo } from '../../../utils/scanHelper.js';
import { getRequest } from '../../../api/apiHelpers.js';
import { useWebSocket } from '../../../context/WebSocketContext.jsx';

export const DocumentModal = ({
    document,
    show,
    onClose,
    position = "center",
    onDeleteSuccess
}) => {
    const { user } = useAuth();
    const isManager = user.role?.toUpperCase() === "MANAGER";

    const [redactedPreview, setRedactedPreview] = useState({
        documentId: null,
        url: null,
    });

    const redactedPreviewUrl =
        redactedPreview.documentId === document?.id
            ? redactedPreview.url
            : null;

    const [previewStatus, setPreviewStatus] = useState(null); // NOT_STARTED|GENERATING|READY|FAILED
    const [previewFailureReason, setPreviewFailureReason] = useState(null);
    const [previewError, setPreviewError] = useState(null); // HTTP status for 501/422/etc, distinct from a GENERATING/FAILED status body

    const { subscribe } = useWebSocket();
    const navigate = useNavigate();

    const fetchPreviewStatus = useCallback((retry = false) => {
        if (!document?.id) return;
        getRequest({
            url: `/documents/${document.id}/redacted-preview`,
            params: retry ? { retry: true } : {},
        })
            .then((res) => {
                setPreviewStatus(res.status);
                setPreviewFailureReason(res.failureReason);
                if (res.status === 'READY') {
                    setRedactedPreview({ documentId: document.id, url: res.previewUrl });
                }
            })
            .catch((err) => {
                setPreviewError(err.response?.status ?? null);
            });
    }, [document?.id]);

    // kick off / check status when modal opens for a non-owner viewing an
    // AI-processed document
    useEffect(() => {
        if (!show || !document) return;
        if (!document.aiProcessed) return;
        if (document.requesterIsOwner !== false) return;
        fetchPreviewStatus();
    }, [show, document?.id, document?.requesterIsOwner, document?.aiProcessed, fetchPreviewStatus]);

    // primary path: live push when generation finishes
    useEffect(() => {
        if (!document?.id) return;
        return subscribe('/user/queue/redacted-preview-status', (payload) => {
            if (payload.documentId !== document.id) return;
            setPreviewStatus(payload.status);
            setPreviewFailureReason(payload.failureReason);
            if (payload.status === 'READY') {
                fetchPreviewStatus(); // one more GET to obtain the signed previewUrl
            }
        });
    }, [document?.id, subscribe, fetchPreviewStatus]);

    // fallback: poll while GENERATING in case the WS push is missed
    useEffect(() => {
        if (previewStatus !== 'GENERATING') return;
        const interval = setInterval(() => fetchPreviewStatus(), 10000);
        return () => clearInterval(interval);
    }, [previewStatus, fetchPreviewStatus]);

    const isLoadingPreview = document?.requesterIsOwner === false && previewStatus === 'GENERATING';

    const handleViewDocument = () => {
        navigate(`../view-document/${document.id}`);
    }

    if (!document) return null;
    const scanInfo = getScanStatusInfo(document);

    return (
        <Modal
            dismissible
            show={show}
            onClose={onClose}
            position={position}
        >
            <ModalHeader className="bg-(--dark-blue-700)">
                <div className="text-white">
                    View Loan Request
                </div>
            </ModalHeader>

            <ModalBody className="flex justify-center bg-(--dark-blue-700) wrap-break-word">
                <Card className="w-4/5 h-full bg-(--dark-blue-700) text-white">
                    <h5 className="text-2xl font-bold tracking-tight">
                        {document.name || "<Unknown>"}
                    </h5>

                    <p className="text-base text-gray-400">
                        ID: {document.id}
                    </p>

                    <p>
                        Document Type: {document.type?.replaceAll("_", " ")}
                        <br />
                        Format: {document.format || "<Unknown>"}
                        <br />
                        Uploaded by: {document.uploaderName}
                        {" - "}
                        Department: {document.departmentName || "<None>"}
                        <br />
                        Date: {formatDate(document.uploadedDateTime)}
                    </p>

                    <hr />

                    <div>
                        <strong>{scanInfo.title}</strong>
                        <br />
                        Date of Scan: {scanInfo.date}
                        <br />
                        File Size: {formatSize(document.byteSize) || 0}
                        <br />
                        Status: {scanInfo.status}
                        <br />
                        Description:
                        <Alert color={scanInfo.color} className="mt-2">
                            <span className="font-medium whitespace-pre-line">{scanInfo.description}</span>
                        </Alert>
                    </div>

                    <hr />
                    <div
                        className="flex flex-row gap-4">

                        <div className="w-2/3">
                            <strong>Options:</strong>

                            <DownloadButton
                                file={document}
                                isDownloadAllowed={
                                    document.requesterIsOwner
                                        ? document.scanStatus === "CLEAN" || document.scanStatus === "NOT_SCANNED"
                                        : Boolean(redactedPreviewUrl)
                                }
                                redactedPreviewUrl={
                                    document.requesterIsOwner === false ? redactedPreviewUrl : null
                                }
                                detailUrl={
                                    isManager
                                        ? `/documents/department/${document.id}`
                                        : `/documents/mine/${document.id}`
                                }
                                className="w-full mt-4 cursor-pointer border border-(--lighter-blue-300) hover:bg-(--dark-blue-700)"
                                isLoadingPreview={isLoadingPreview}
                            />

                            {document.requesterIsOwner === false && previewStatus === 'GENERATING' && (
                                <p className="text-sm text-gray-400 mt-2">Generating redacted preview…</p>
                            )}
                            {document.requesterIsOwner === false && previewStatus === 'FAILED' && (
                                <p className="text-sm text-red-400 mt-2">
                                    Preview failed: {previewFailureReason || 'unknown error'}.{' '}
                                    <button
                                        type="button"
                                        className="underline cursor-pointer"
                                        onClick={() => fetchPreviewStatus(true)}
                                    >
                                        Retry
                                    </button>
                                </p>
                            )}

                            <Button
                                onClick={handleViewDocument}
                                disabled={!document.accessible}
                                className="w-full mt-4 cursor-pointer border border-(--lighter-blue-300) hover:bg-(--dark-blue-700)"
                            >
                                View Document
                            </Button>
                        </div>

                        <div className="w-1/3 flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200">
                            <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                                File
                            </h3>
                            <p className="mb-4 text-sm text-center text-gray-500 dark:text-gray-400">
                                {document.format || "<Unknown>"} format
                                <br />
                                {formatSize(document.byteSize) || 0}
                            </p>
                        </div>
                    </div>
                </Card>

            </ModalBody>
            <div className="flex justify-center gap-6 bg-(--dark-blue-700) px-10 pb-5">
                <DeleteAction
                    document={document}
                    className="bg-red-700 border border-red-700 hover:bg-(--dark-blue-700) w-2/3"
                    onDeleteSuccess={onDeleteSuccess}
                />

                <Button
                    color="alternative"
                    onClick={onClose}
                    className="cursor-pointer text-white border-white bg-(--dark-blue-700) w-2/3"
                >
                    Close
                </Button>
            </div>
        </Modal>
    );
};