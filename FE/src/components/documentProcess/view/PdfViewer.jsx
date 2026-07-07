
export const PdfViewer = ({ fileUrl }) => {
    return (
        <embed
            src={fileUrl}
            type="application/pdf"
            className="h-150 w-full rounded-lg"
        />
    );
};