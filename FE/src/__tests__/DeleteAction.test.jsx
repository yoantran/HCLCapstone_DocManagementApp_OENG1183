import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { DeleteAction } from '../components/action/DeleteAction.jsx';

const { deleteRequestMock, pushErrorMock } = vi.hoisted(() => ({
    deleteRequestMock: vi.fn(),
    pushErrorMock: vi.fn(),
}));

vi.mock('../api/apiHelpers.js', () => ({
    deleteRequest: deleteRequestMock,
}));

vi.mock('../components/toast/index.jsx', () => ({
    pushError: pushErrorMock,
    pushSuccess: vi.fn(),
}));

describe('DeleteAction', () => {
    beforeEach(() => {
        deleteRequestMock.mockReset();
        pushErrorMock.mockReset();
    });

    // Real, confirmed bug: the `!itemId` guard showed an error toast but had
    // no `return`, so handleDelete fell through and still issued the DELETE
    // request with a missing/undefined id (e.g. `/documents/undefined`).
    it('does not call deleteRequest when the row has no id', async () => {
        render(<DeleteAction row={{ name: 'Untitled' }} idKey="id" endpoint="/documents" />);

        fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
        const confirmButtons = await screen.findAllByRole('button', { name: 'Delete' });
        fireEvent.click(confirmButtons[confirmButtons.length - 1]);

        await waitFor(() => expect(pushErrorMock).toHaveBeenCalledWith('Cannot delete'));
        expect(deleteRequestMock).not.toHaveBeenCalled();
    });

    it('does call deleteRequest when the row has a valid id', async () => {
        deleteRequestMock.mockResolvedValue({});
        render(<DeleteAction row={{ id: 'abc-123', name: 'Real doc' }} idKey="id" endpoint="/documents" />);

        fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
        const confirmButtons = await screen.findAllByRole('button', { name: 'Delete' });
        fireEvent.click(confirmButtons[confirmButtons.length - 1]);

        await waitFor(() => expect(deleteRequestMock).toHaveBeenCalledWith({ url: '/documents/abc-123' }));
    });
});
