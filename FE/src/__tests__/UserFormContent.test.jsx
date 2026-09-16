import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { UserFormContent } from '../components/userFormContent/index.jsx';

const { pushErrorMock } = vi.hoisted(() => ({ pushErrorMock: vi.fn() }));

vi.mock('../components/toast/index.jsx', () => ({
    pushError: pushErrorMock,
}));

describe('UserFormContent', () => {
    beforeEach(() => {
        pushErrorMock.mockReset();
    });

    // Real, confirmed bug: clearing Name to empty enabled Apply (a real
    // diff was detected), but handleSubmit's `if (name.trim())` guard
    // silently dropped it from the submitted FormData -- the server never
    // received the change, yet onSave still fired as if it succeeded.
    // Reachable via Profile.jsx, where name is editable (not read-only).
    it('blocks submission and does not call onSave when Name is cleared', () => {
        const onSave = vi.fn();
        const initialData = { name: 'Jo Worker', phoneNumber: '0123456789' };

        render(<UserFormContent initialData={initialData} onSave={onSave} saving={false} />);

        fireEvent.change(screen.getByLabelText('Change Name'), { target: { value: '' } });

        const applyButton = screen.getByRole('button', { name: 'Apply' });
        expect(applyButton).not.toBeDisabled();

        fireEvent.click(applyButton);

        expect(onSave).not.toHaveBeenCalled();
        expect(pushErrorMock).toHaveBeenCalledWith('Name cannot be empty.');
    });

    it('submits normally when Name is a valid non-empty value', () => {
        const onSave = vi.fn();
        const initialData = { name: 'Jo Worker', phoneNumber: '0123456789' };

        render(<UserFormContent initialData={initialData} onSave={onSave} saving={false} />);

        fireEvent.change(screen.getByLabelText('Change Name'), { target: { value: 'Jo W. Worker' } });
        fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

        expect(onSave).toHaveBeenCalledTimes(1);
        const submittedFormData = onSave.mock.calls[0][0];
        expect(submittedFormData.get('name')).toBe('Jo W. Worker');
    });
});
