import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import AdminManagement from '../pages/AdminManagement.jsx';

const { getRequestMock } = vi.hoisted(() => ({ getRequestMock: vi.fn() }));

vi.mock('../api/apiHelpers.js', () => ({
    getRequest: getRequestMock,
    patchRequest: vi.fn(),
    putRequest: vi.fn(),
}));

const users = [
    { id: 'u1', name: 'Alice', role: 'STAFF', departmentName: 'Eng', email: 'alice@hcl.com', phoneNumber: '111' },
];
const departments = [{ id: 'd1', name: 'Eng', managerName: null }];

describe('AdminManagement column identity stability', () => {
    beforeEach(() => {
        getRequestMock.mockReset();
        getRequestMock.mockImplementation(({ url }) => {
            if (url === '/admin/users') return Promise.resolve(users);
            if (url === '/admin/departments') return Promise.resolve(departments);
            return Promise.resolve([]);
        });
    });

    // Real, confirmed bug: adminManagementColumns() was called fresh every
    // render with a brand-new inline Cell component, so CustomTable's
    // <CustomCell/> got a different component type on every render (e.g.
    // every keystroke in the search box) and React fully unmounted/
    // remounted the row action cells -- silently closing any open
    // Manage/Delete popup out from under the user.
    it('keeps an open Manage modal open while typing in the search box', async () => {
        render(<AdminManagement />);

        const manageButton = await screen.findByRole('button', { name: 'Manage' });
        fireEvent.click(manageButton);

        await waitFor(() => expect(screen.getByRole('heading', { name: 'Alice' })).toBeInTheDocument());

        // 'a' still matches Alice's own name/email -- isolates the remount
        // concern from the (unrelated, correct) search-filtering behavior.
        fireEvent.change(screen.getByPlaceholderText('Search'), { target: { value: 'a' } });

        // If the row action cell got remounted, ManageAction's local
        // showModal state resets to false and this disappears.
        expect(screen.getByRole('heading', { name: 'Alice' })).toBeInTheDocument();
    });
});
