import { describe, it, expect } from 'vitest';
import { formatDate, parseServerDate } from '../utils/formatFields';

describe('parseServerDate', () => {
    // Real, confirmed bug: new Date('garbage') returns an Invalid Date
    // object, which is truthy -- parseServerDate must detect and normalize
    // that to null itself, since every caller's own truthiness check
    // (formatDate's `!parsed`, DocInfo's `uploadedAt ? ... : 0`) can never
    // catch it otherwise.
    it('returns null for a malformed date string instead of an Invalid Date', () => {
        expect(parseServerDate('not-a-real-date')).toBeNull();
    });

    it('still parses a valid zoneless server date', () => {
        const parsed = parseServerDate('2026-01-01T12:00:00');
        expect(parsed).not.toBeNull();
        expect(parsed.getUTCFullYear()).toBe(2026);
    });

    it('returns null for falsy input', () => {
        expect(parseServerDate(null)).toBeNull();
        expect(parseServerDate('')).toBeNull();
    });
});

describe('formatDate', () => {
    it('renders "Never" for a malformed date string, not "Invalid Date"', () => {
        expect(formatDate('not-a-real-date')).toBe('Never');
    });

    it('renders "Never" for null', () => {
        expect(formatDate(null)).toBe('Never');
    });
});
