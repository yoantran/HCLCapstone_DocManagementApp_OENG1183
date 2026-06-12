import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PublicViewer } from "../components/documentProcess/view"
import { DocInfo } from "../components/documentProcess/view/docInfo/DocInfo";
import { getRequest } from "../api/apiHelpers";
import { DeleteAction } from "../components/documentTable/cells/DeleteAction";
import { DownloadButton } from "../components/documentTable/modal/DownloadButton";

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
    }, []);

    if (!document) return null;

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

            <div className="flex justify-center bg-gray-100 p-6">
                <div className="w-full max-w-6xl rounded-lg bg-white shadow">
                    <PublicViewer
                        fileUrl={document.signedUrl || ''}
                        fileType={document.format?.toLowerCase() || ''}
                    />
                </div>
            </div>

        </>
    )
}