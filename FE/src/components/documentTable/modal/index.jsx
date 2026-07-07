import { useNavigate } from 'react-router-dom';
import {
    Modal,
    ModalHeader,
    ModalBody,
    Button,
    Card,
} from "flowbite-react";
import { DownloadButton } from "./DownloadButton";
import { DeleteAction } from "../../action/DeleteAction.jsx";
import { formatDate, formatSize } from '../../../utils/formatFields';

export const DocumentModal = ({
    document,
    show,
    onClose,
    position = "center",
    onDeleteSuccess
}) => {
    const navigate = useNavigate();

    const handleViewDocument = () => {
        navigate(`../view-document/${document.id}`);
    }

    if (!document) return null;

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

            <ModalBody className="flex justify-center bg-(--dark-blue-700)">
                <Card className="w-4/5 bg-(--dark-blue-700) text-white">
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

                    <p>
                        <strong>0 MALWARE DETECTED:</strong>
                        <br />
                        Date of Scan: None
                        <br />
                        File Size: {formatSize(document.byteSize) || 0}
                        <br />
                        Status: Normal
                        <br />
                        Description: None
                    </p>

                    <hr />
                    <div
                        className="flex flex-row gap-4">

                        <div className="w-2/3">
                            <strong>Options:</strong>
                            <DownloadButton
                                file={document}
                                className={"w-full mt-4 cursor-pointer border border-(--lighter-blue-300) hover:bg-(--dark-blue-700) "}
                            />
                            <Button
                                onClick={handleViewDocument}
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
            <div className="flex justify-center gap-6 bg-(--dark-blue-700) px-10">
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