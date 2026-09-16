// Real, confirmed bug: name-asc/name-desc used to call
// a.name.localeCompare(b.name) with no null guard, while `document.name` is
// nullable elsewhere in this codebase (documentTable/modal/index.jsx has its
// own `document.name || "<Unknown>"` fallback, proving the field can be
// missing). Extracted out of Documents.jsx (a pure function, no component
// state) so it can be unit tested directly and to avoid tripping
// react-refresh/only-export-components on that file's default export.
export const sortDocuments = (docs, sort) => {
    const sorted = [...docs];
    switch (sort) {
        case 'date-desc':
            return sorted.sort((a, b) => new Date(b.uploadedDateTime) - new Date(a.uploadedDateTime));
        case 'date-asc':
            return sorted.sort((a, b) => new Date(a.uploadedDateTime) - new Date(b.uploadedDateTime));
        case 'id-asc':
            return sorted.sort((a, b) => a.id.localeCompare(b.id));
        case 'id-desc':
            return sorted.sort((a, b) => b.id.localeCompare(a.id));
        case 'name-asc':
            return sorted.sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''));
        case 'name-desc':
            return sorted.sort((a, b) => (b.name ?? '').localeCompare(a.name ?? ''));
        default:
            return sorted;
    }
};
