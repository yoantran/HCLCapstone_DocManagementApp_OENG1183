import { useEffect, useState } from 'react';

export const CsvViewer = ({ fileUrl }) => {
    const [content, setContent] = useState('');
    const [error, setError] = useState(false);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setError(false);
        if (!fileUrl) return;

        fetch(fileUrl)
            .then((response) => {
                if (!response.ok) throw new Error(`Failed to load CSV (${response.status})`);
                return response.text();
            })
            .then(setContent)
            .catch((err) => {
                console.error('Error reading CSV:', err);
                setError(true);
            });
    }, [fileUrl]);

    if (error) {
        return (
            <p className="p-4 text-sm text-red-500">
                Failed to load CSV content. The link may have expired -- try reopening the document.
            </p>
        );
    }

    return (
        <pre
            className="
                h-150
                w-full
                overflow-auto
                rounded-lg
                border
                border-gray-300
                bg-gray-100
                p-4
                text-left
                font-mono
                text-sm
                text-black
                whitespace-pre
            "
        >
            {content || 'Loading CSV content...'}
        </pre>
    );
};