export const formatSize = (bytes) => {
    if (bytes == null) return 'Unknown';

    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;

    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const formatDate = (date) => {
    if (!date) return 'Never';

    return new Date(date).toLocaleString();
};