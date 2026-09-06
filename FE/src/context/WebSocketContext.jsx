import { createContext, useContext, useEffect, useRef, useState } from 'react';
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
            for (const destination of subscriptionsRef.current.keys()) {
                subscribeInternal(stompClient, destination);
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
        stompClient.subscribe(destination, (message) => {
            if (!message.body) return;
            let parsed;
            try {
                parsed = JSON.parse(message.body);
            } catch (err) {
                console.error('Error parsing socket body:', err);
                return;
            }
            const callbacks = subscriptionsRef.current.get(destination);
            if (callbacks) {
                callbacks.forEach((cb) => cb(parsed));
            }
        });
    }

    // Registers `callback` for `destination`, opening one real STOMP
    // subscription per destination string no matter how many callbacks are
    // registered against it (fan-out happens locally via the Set). Returns
    // an unsubscribe function.
    function subscribe(destination, callback) {
        let callbacks = subscriptionsRef.current.get(destination);
        if (!callbacks) {
            callbacks = new Set();
            subscriptionsRef.current.set(destination, callbacks);
            if (clientRef.current?.connected) {
                subscribeInternal(clientRef.current, destination);
            }
        }
        callbacks.add(callback);

        return () => {
            callbacks.delete(callback);
        };
    }

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
