import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { Client } from '@stomp/stompjs';
import { useAuth } from './AuthContext.jsx';

const WebSocketContext = createContext(null);

export function WebSocketProvider({ children }) {
    const { user } = useAuth();
    const clientRef = useRef(null);
    const subscriptionsRef = useRef(new Map()); // destination -> Set<callback>
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        if (!user?.email) return;

        const token = localStorage.getItem('token');
        const stompClient = new Client({
            brokerURL: `ws://localhost:8080/ws?token=${token}`,
            reconnectDelay: 5000,
            connectHeaders: {
                Authorization: token ? `Bearer ${token}` : '',
            },
            debug: (str) => console.log(' [STOMP Debug Input]:', str),
        });

        stompClient.onConnect = () => {
            setConnected(true);
            for (const [destination, entry] of subscriptionsRef.current.entries()) {
                entry.stompSub = subscribeInternal(stompClient, destination);
            }
        };

        clientRef.current = stompClient;
        stompClient.activate();

        return () => {
            stompClient.deactivate();
            clientRef.current = null;
            setConnected(false);
        };
    }, [user?.email]);

    function subscribeInternal(stompClient, destination) {
        return stompClient.subscribe(destination, (message) => {
            if (!message.body) return;
            let parsed;
            try {
                parsed = JSON.parse(message.body);
            } catch (err) {
                console.error('Error parsing socket body:', err);
                return;
            }
            const entry = subscriptionsRef.current.get(destination);
            if (entry) {
                entry.callbacks.forEach((cb) => cb(parsed));
            }
        });
    }

    // Registers `callback` for `destination`, opening one real STOMP
    // subscription per destination string no matter how many callbacks are
    // registered against it (fan-out happens locally via the Set). Returns
    // an unsubscribe function that, once the last callback for a
    // destination is removed, also tears down the underlying STOMP
    // subscription and drops the destination entry entirely -- otherwise
    // the broker keeps pushing messages for a destination nobody is
    // listening to for the lifetime of the connection.
    // Stable across renders (empty deps -- only touches refs) so consumers'
    // `useEffect(..., [subscribe])` don't unsubscribe/resubscribe on every
    // WebSocketProvider re-render (e.g. the setConnected(true) flip on
    // STOMP connect).
    const subscribe = useCallback((destination, callback) => {
        let entry = subscriptionsRef.current.get(destination);
        if (!entry) {
            entry = { callbacks: new Set(), stompSub: null };
            subscriptionsRef.current.set(destination, entry);
            if (clientRef.current?.connected) {
                entry.stompSub = subscribeInternal(clientRef.current, destination);
            }
        }
        entry.callbacks.add(callback);

        return () => {
            entry.callbacks.delete(callback);
            if (entry.callbacks.size === 0) {
                subscriptionsRef.current.delete(destination);
                entry.stompSub?.unsubscribe();
            }
        };
    }, []);

    return (
        <WebSocketContext.Provider value={{ subscribe, connected }}>
            {children}
        </WebSocketContext.Provider>
    );
}

export function useWebSocket() {
    const ctx = useContext(WebSocketContext);
    if (!ctx) {
        throw new Error('useWebSocket must be used within a WebSocketProvider');
    }
    return ctx;
}
