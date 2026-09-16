import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../context/AuthContext.jsx';

const { getRequestMock } = vi.hoisted(() => ({ getRequestMock: vi.fn() }));

vi.mock('../api/apiHelpers', () => ({
    getRequest: getRequestMock,
}));

function Probe() {
    const { token, loading } = useAuth();
    return (
        <div>
            <span data-testid="loading">{String(loading)}</span>
            <span data-testid="token">{token ?? 'null'}</span>
        </div>
    );
}

describe('AuthContext mount-time session rehydration', () => {
    beforeEach(() => {
        localStorage.clear();
        getRequestMock.mockReset();
    });

    // Real, confirmed bug: any /users/me failure (network blip, transient
    // 500) was treated the same as an invalid token and force-logged the
    // user out. Only a real 401 (the token itself being invalid/expired)
    // should clear the session -- axios's own interceptor already handles
    // the 401 case globally.
    it('keeps the token on a non-401 (transient) failure', async () => {
        localStorage.setItem('token', 'a-valid-token');
        getRequestMock.mockRejectedValue(new Error('Network Error'));

        render(
            <AuthProvider>
                <Probe />
            </AuthProvider>
        );

        await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'));

        expect(screen.getByTestId('token').textContent).toBe('a-valid-token');
        expect(localStorage.getItem('token')).toBe('a-valid-token');
    });

    it('clears the token on a real 401 (invalid/expired token)', async () => {
        localStorage.setItem('token', 'a-stale-token');
        const err = new Error('Unauthorized');
        err.response = { status: 401 };
        getRequestMock.mockRejectedValue(err);

        render(
            <AuthProvider>
                <Probe />
            </AuthProvider>
        );

        await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'));

        expect(screen.getByTestId('token').textContent).toBe('null');
        expect(localStorage.getItem('token')).toBeNull();
    });
});
