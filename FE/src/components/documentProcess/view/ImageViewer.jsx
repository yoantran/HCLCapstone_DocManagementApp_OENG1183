export const ImageViewer = ({ fileUrl }) => {
    return (
        <div className="flex justify-center">
            <img
                src={fileUrl}
                alt="Document Preview"
                className="max-w-full rounded-lg border border-gray-300"
            />
        </div>
    );
};