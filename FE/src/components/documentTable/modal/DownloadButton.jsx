import { Button } from "flowbite-react";
import { toast } from "react-toastify";

export const DownloadButton = ({ file, className, isDownloadAllowed }) => {
    const handleDownload = async () => {
        if (!file?.signedUrl) {
            toast.error("No download link available — please refresh and try again.");
            return;
        }
        try {
            const response = await fetch(file.signedUrl);
            if (!response.ok) {
                throw new Error(`Download failed (${response.status})`);
            }
            const blob = await response.blob();

            const url = window.URL.createObjectURL(blob);

            const link = window.document.createElement("a");
            link.href = url;
            link.download = file.name;

            window.document.body.appendChild(link);
            link.click();

            link.remove();
            window.URL.revokeObjectURL(url);
        } catch {
            toast.error("Download failed. The file link may have expired — please refresh and try again.");
        }
    };

    return (
        <Button
            onClick={handleDownload}
            disabled={!file.signedUrl}
            className={`cursor-pointer ${className}`}
        >
            Download
        </Button>
    );
};