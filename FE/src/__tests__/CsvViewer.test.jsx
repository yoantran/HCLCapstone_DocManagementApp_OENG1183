import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { CsvViewer } from '../components/documentProcess/view/CsvViewer.jsx';

// Real, confirmed bug: a failed fetch (e.g. an expired signed URL) was only
// ever console.error'd, leaving `content` empty forever -- the UI stayed
// stuck on "Loading CSV content..." with no user-facing indication anything
// failed.
describe('CsvViewer', () => {
    beforeEach(() => {
        globalThis.fetch = vi.fn();
    });

    it('shows an error message instead of an infinite loading state on fetch failure', async () => {
        globalThis.fetch.mockResolvedValue({ ok: false, status: 410 });

        render(<CsvViewer fileUrl="https://example.com/expired-signed-url" />);

        await waitFor(() =>
            expect(screen.getByText(/Failed to load CSV content/i)).toBeInTheDocument()
        );
        expect(screen.queryByText('Loading CSV content...')).not.toBeInTheDocument();
    });

    it('renders the CSV content on success', async () => {
        globalThis.fetch.mockResolvedValue({ ok: true, text: () => Promise.resolve('a,b,c') });

        render(<CsvViewer fileUrl="https://example.com/real.csv" />);

        await waitFor(() => expect(screen.getByText('a,b,c')).toBeInTheDocument());
    });
});
