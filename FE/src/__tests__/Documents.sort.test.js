import { describe, it, expect } from 'vitest';
import { sortDocuments } from '../utils/sortDocuments.js';

// Real, confirmed bug: name-asc/name-desc called a.name.localeCompare(b.name)
// with no null guard, while `document.name` is nullable elsewhere in this
// codebase (documentTable/modal/index.jsx has its own `document.name ||
// "<Unknown>"` fallback, proving the field can be missing).
describe('sortDocuments', () => {
    const docs = [
        { id: '1', name: 'Banana', uploadedDateTime: '2026-01-02T00:00:00' },
        { id: '2', name: null, uploadedDateTime: '2026-01-01T00:00:00' },
        { id: '3', name: 'Apple', uploadedDateTime: '2026-01-03T00:00:00' },
    ];

    it('does not throw when a document has no name (name-asc)', () => {
        expect(() => sortDocuments(docs, 'name-asc')).not.toThrow();
    });

    it('does not throw when a document has no name (name-desc)', () => {
        expect(() => sortDocuments(docs, 'name-desc')).not.toThrow();
    });

    it('sorts null names as empty string, ascending', () => {
        const sorted = sortDocuments(docs, 'name-asc');
        expect(sorted.map((d) => d.id)).toEqual(['2', '3', '1']); // '' < 'Apple' < 'Banana'
    });

    it('still sorts named documents correctly, descending', () => {
        const sorted = sortDocuments(docs, 'name-desc');
        expect(sorted.map((d) => d.id)).toEqual(['1', '3', '2']);
    });
});
