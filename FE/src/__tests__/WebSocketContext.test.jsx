import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { WebSocketProvider, useWebSocket } from '../context/WebSocketContext.jsx';

const { subscribeMock, activateMock, clientInstances } = vi.hoisted(() => ({
    subscribeMock: vi.fn(),
    activateMock: vi.fn(),
    clientInstances: [],
}));

vi.mock('@stomp/stompjs', () => ({
    Client: class {
        constructor(config) {
            this.connected = false;
            this._config = config;
            clientInstances.push(this);
        }
        activate() {
            activateMock();
            this.connected = true;
            this.onConnect?.();
        }
        deactivate() {
            this.connected = false;
        }
        subscribe(destination, cb) {
            return subscribeMock(destination, cb);
        }
    },
}));

vi.mock('../context/AuthContext.jsx', () => ({
    useAuth: () => ({ user: { email: 'staff1@hcl.com' } }),
}));

let capturedSubscribe;

function Probe() {
    const { subscribe } = useWebSocket();
    capturedSubscribe = subscribe;
    return null;
}

describe('WebSocketContext subscribe/unsubscribe', () => {
    beforeEach(() => {
        subscribeMock.mockReset();
        activateMock.mockReset();
        clientInstances.length = 0;
        localStorage.setItem('token', 'a-token');
    });

    // Real, confirmed bug: the unsubscribe function returned by subscribe()
    // only removed the local callback from the Set -- it never called the
    // underlying STOMP subscription's own unsubscribe(), and never removed
    // the destination from the map. The broker kept pushing messages for a
    // destination nobody was listening to for the lifetime of the connection.
    it('tears down the real STOMP subscription once the last callback unsubscribes', async () => {
        const stompUnsubscribe = vi.fn();
        subscribeMock.mockReturnValue({ id: 'sub-0', unsubscribe: stompUnsubscribe });

        render(
            <WebSocketProvider>
                <Probe />
            </WebSocketProvider>
        );

        await waitFor(() => expect(activateMock).toHaveBeenCalled());

        const unsubscribe = capturedSubscribe('/user/queue/notifications', () => {});
        expect(subscribeMock).toHaveBeenCalledTimes(1);

        unsubscribe();

        expect(stompUnsubscribe).toHaveBeenCalledTimes(1);
    });

    it('keeps the real subscription alive while at least one callback remains', async () => {
        const stompUnsubscribe = vi.fn();
        subscribeMock.mockReturnValue({ id: 'sub-0', unsubscribe: stompUnsubscribe });

        render(
            <WebSocketProvider>
                <Probe />
            </WebSocketProvider>
        );

        await waitFor(() => expect(activateMock).toHaveBeenCalled());

        const unsubscribeA = capturedSubscribe('/user/queue/notifications', () => {});
        const unsubscribeB = capturedSubscribe('/user/queue/notifications', () => {});
        // Only one real STOMP subscription for both callbacks on the same destination
        expect(subscribeMock).toHaveBeenCalledTimes(1);

        unsubscribeA();
        expect(stompUnsubscribe).not.toHaveBeenCalled();

        unsubscribeB();
        expect(stompUnsubscribe).toHaveBeenCalledTimes(1);
    });

    // Real, confirmed bug: `subscribe` was a plain function recreated on
    // every WebSocketProvider render (e.g. the setConnected(true) flip on
    // STOMP connect), so every consumer's `useEffect(..., [subscribe])`
    // unsubscribed and resubscribed on that render even though nothing
    // about the callback or destination changed.
    it('keeps a stable subscribe reference across the onConnect re-render', async () => {
        subscribeMock.mockReturnValue({ id: 'sub-0', unsubscribe: vi.fn() });
        const captured = [];

        function Probe() {
            const { subscribe } = useWebSocket();
            captured.push(subscribe);
            return null;
        }

        render(
            <WebSocketProvider>
                <Probe />
            </WebSocketProvider>
        );

        await waitFor(() => expect(captured.length).toBeGreaterThan(1));

        expect(new Set(captured).size).toBe(1);
    });
});
