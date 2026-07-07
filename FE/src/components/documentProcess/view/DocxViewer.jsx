export const DocxViewer = ({ fileUrl }) => {
    const viewerUrl =
        `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(fileUrl)}`;

    return (
        <iframe
            src={viewerUrl}
            title="DOCX Viewer"
            className="w-full h-screen"
        />
    );
};