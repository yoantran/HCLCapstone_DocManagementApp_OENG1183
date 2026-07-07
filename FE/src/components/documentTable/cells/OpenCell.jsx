
export const OpenCell = ({ document }) => {
    return (
        <a
            href={document.signedUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="underline"
            onClick={(e) => {
                e.stopPropagation();
            }}
        >
            View Document
        </a>
    );
}