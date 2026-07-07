import { useEffect, useState } from 'react';

export const CsvViewer = ({ fileUrl }) => {
    const [content, setContent] = useState('');

    useEffect(() => {
        if (!fileUrl) return;

        fetch(fileUrl)
            .then((response) => response.text())
            .then(setContent)
            .catch((err) => console.error('Error reading CSV:', err));
    }, [fileUrl]);

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