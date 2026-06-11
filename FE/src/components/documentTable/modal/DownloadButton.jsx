import { Button } from "flowbite-react";

export const DownloadButton = ({ file, className }) => {
    const handleDownload = async () => {
        const response = await fetch(file.signedUrl);
        const blob = await response.blob();

        const url = window.URL.createObjectURL(blob);

        const link = window.document.createElement("a");
        link.href = url;
        link.download = file.name;

        window.document.body.appendChild(link);
        link.click();

        link.remove();
        window.URL.revokeObjectURL(url);
    };

    return (
        <Button
            onClick={handleDownload}
            className={`cursor-pointer ${className}`}
        >
            Download
        </Button>
    );
};