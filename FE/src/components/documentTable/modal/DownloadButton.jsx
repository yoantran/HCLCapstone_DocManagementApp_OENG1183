import { Button, Spinner } from "flowbite-react";
import { toast } from "react-toastify";
import { getRequest } from "../../../api/apiHelpers";

export const DownloadButton = ({
    file,
    className,
    isDownloadAllowed = true,
    redactedPreviewUrl,
    detailUrl,
    isLoadingPreview = false,
}) => {
    const handleDownload = async () => {
        try {
            let downloadFile = file;
            let redactedUrl = redactedPreviewUrl;

            // Modal case: fetch detail lazily only on Download click
            if (detailUrl) {
                downloadFile = await getRequest({ url: detailUrl });

                if (downloadFile.requesterIsOwner === false) {
                    try {
                        const preview = await getRequest({
                            url: `/documents/${downloadFile.id}/redacted-preview`
                        });
                        if (preview.status === "READY") {
                            redactedUrl = preview.previewUrl;
                        } else if (preview.status === "GENERATING") {
                            toast.info("Preview is still generating — try again in a moment.");
                            return;
                        } else if (preview.status === "FAILED") {
                            toast.error(`Preview failed: ${preview.failureReason || "unknown error"}`);
                            return;
                        }
                    } catch (err) {
                        const status = err.response?.status;
                        if (status === 501) {
                            toast.error("Redacted download is not available for this format.");
                        } else {
                            toast.error("Redacted download is not available.");
                        }
                        return;
                    }
                }
            }

            // Non-owner
            if (downloadFile?.requesterIsOwner === false) {
                if (!redactedUrl) {
                    toast.error("Redacted download is not available.");
                    return;
                }

                const link = window.document.createElement("a");
                link.href = redactedUrl;

                const baseName =
                    downloadFile.name?.replace(/\.[^/.]+$/, "") || "document";

                link.download = `${baseName}-redacted.png`;

                window.document.body.appendChild(link);
                link.click();
                link.remove();

                return;
            }

            // Owner
            if (!downloadFile?.signedUrl) {
                toast.error("No download link available — please refresh and try again.");
                return;
            }

            const response = await fetch(downloadFile.signedUrl);

            if (!response.ok) {
                throw new Error(`Download failed (${response.status})`);
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);

            const link = window.document.createElement("a");
            link.href = url;
            link.download = downloadFile.name;

            window.document.body.appendChild(link);
            link.click();
            link.remove();

            URL.revokeObjectURL(url);

        } catch (error) {
            console.error("Download failed:", error);
            toast.error("Download failed. Please try again.");
        }
    };

    return (
        <Button
            onClick={handleDownload}
            disabled={!isDownloadAllowed || isLoadingPreview}
            className={`cursor-pointer ${className}`}
        >
            {isLoadingPreview ? (
                <span className="flex items-center justify-center gap-3">
                    <Spinner size="sm" light={true} />
                    <span>Loading...</span>
                </span>
            ) : (
                "Download"
            )}
        </Button>
    );
};