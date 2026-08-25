export const formatSize = (bytes) => {
    if (bytes == null) return 'Unknown';

    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;

    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

// BE sends zoneless LocalDateTime strings that actually represent UTC
// instants -- append Z so browsers outside UTC don't misparse them as local
// and shift every displayed/computed time by the browser's UTC offset.
export const parseServerDate = (date) => {
    if (!date) return null;

    const hasZone = /[Z+-]\d{2}:?\d{2}$|Z$/.test(date);
    return new Date(hasZone ? date : `${date}Z`);
};

export const formatDate = (date) => {
    const parsed = parseServerDate(date);
    if (!parsed) return 'Never';

    return parsed.toLocaleString();
};