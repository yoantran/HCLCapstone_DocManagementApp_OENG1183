import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { getRequest, patchRequest } from '../../api/apiHelpers';
import { useWebSocket } from '../../context/WebSocketContext.jsx';
import bellOn from '../../assets/bell-on.svg';
import bellOff from '../../assets/bell-off.svg';
import { formatDate } from '../../utils/formatFields';
import { Dropdown, DropdownItem } from "flowbite-react";

// Flowbite's Dropdown only mounts `children` while open (see Dropdown.js --
// `open && <FloatingFocusManager>{children}</FloatingFocusManager>`), so a
// mount-only effect here fires exactly once per time the dropdown opens.
function MarkAllReadOnOpen({ markAllReadRef }) {
    useEffect(() => {
        markAllReadRef.current();
    }, [markAllReadRef]);
    return null;
}

export const NotificationBell = ({ userId, userEmail }) => {
    const [notifications, setNotifications] = useState([]);
    const navigate = useNavigate();

    const unreadCount = notifications.filter((n) => !n.hasRead).length;

    // fetch all notifications on mount
    useEffect(() => {
        const fetchNotifications = async () => {
            try {
                const data = await getRequest({ url: `/notifications` });
                setNotifications(Array.isArray(data) ? data : []);
            } catch (error) {
                console.error("Failed to load historical notifications:", error);
            }
        };

        if (userId) fetchNotifications();
    }, [userId]);

    // ws push via the shared connection
    const { subscribe } = useWebSocket();

    useEffect(() => {
        const unsubscribe = subscribe('/user/queue/notifications', (rawNoti) => {
            const normalizedNoti = {
                id: rawNoti.id,
                content: rawNoti.content,
                triggeredDocumentId: rawNoti.triggeredDocumentId || rawNoti.documentId,
                triggeredDocumentName: rawNoti.triggeredDocumentName || rawNoti.documentName,
                hasRead: rawNoti.hasRead !== undefined ? rawNoti.hasRead : false,
                createdAt: rawNoti.createdAt || new Date().toISOString()
            };
            setNotifications((prev) => [normalizedNoti, ...prev]);
        });
        return unsubscribe;
    }, [subscribe]);


    // route to `/documents` & push read noti request -- navigation must
    // always happen on click, even if MarkAllReadOnOpen already flipped
    // hasRead the instant the dropdown opened (before this specific item
    // was clicked); only the read-status PATCH is conditional on that.
    const handleNotificationClick = async (noti) => {
        if (!noti.hasRead) {
            setNotifications((prev) =>
                prev.map((n) => (n.id === noti.id ? { ...n, hasRead: true } : n))
            );

            try {
                await patchRequest({
                    url: `/notifications/${noti.id}/read`,
                    data: {}
                });
            } catch (error) {
                console.error(`Failed to update read status for notification ${noti.id}:`, error);
            }
        }

        navigate(`/${userId}/documents`, { state: { highlightDocumentId: noti.triggeredDocumentId } });
    };

    // Ref so the mount-effect below always calls the freshest closure without
    // needing to be in its dependency array -- the dropdown's content (and
    // this component with it) mounts/unmounts each time it opens/closes, so
    // firing once on mount == firing once per open.
    const markAllReadRef = useRef();
    markAllReadRef.current = () => {
        setNotifications((prev) => {
            prev.filter((n) => !n.hasRead).forEach((n) => {
                patchRequest({ url: `/notifications/${n.id}/read`, data: {} })
                    .catch((error) =>
                        console.error(`Failed to mark notification ${n.id} as read:`, error));
            });
            return prev.map((n) => (n.hasRead ? n : { ...n, hasRead: true }));
        });
    };

    return (
        <Dropdown
            label=""
            className=""
            dismissOnClick={true}
            renderTrigger={() => (
                <button className="relative p-1 rounded-lg transition-opacity hover:opacity-80 focus:outline-none">
                    <img
                        src={unreadCount > 0 ? bellOn : bellOff}
                        alt="Notification Bell"
                        className="h-8 w-8 hover:cursor-pointer"
                    />
                    {unreadCount > 0 && (
                        <span className="absolute top-1 right-1 flex h-3 w-3">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
                        </span>
                    )}
                </button>
            )}
        >

            <div className="w-80 rounded-lg bg-white dark:bg-slate-800">
                <MarkAllReadOnOpen markAllReadRef={markAllReadRef} />
                <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2.5 dark:border-slate-700">
                    <span className="font-semibold text-slate-700 dark:text-slate-200">
                        Notifications ({notifications.length})
                    </span>
                </div>

                <div className="max-h-64 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-700">
                    {notifications.length === 0 ? (
                        <div className="p-4 text-center text-sm text-slate-400">
                            No notifications found
                        </div>
                    ) : (
                        notifications.map((noti) => (
                            <DropdownItem
                                key={noti.id}
                                onClick={() => handleNotificationClick(noti)}
                                className={`flex flex-col p-3 transition-colors hover:bg-slate-50 dark:hover:bg-slate-700/50 ${!noti.hasRead ? 'bg-blue-100 dark:bg-blue-900/10 font-medium' : ''
                                    }`}
                            >
                                <p className="w-full text-left text-slate-600 dark:text-slate-300 whitespace-normal wrap-break-word">
                                    {noti.content}
                                </p>

                                <span className="w-full text-right text-xs text-slate-400 dark:text-slate-500 mt-1 block">
                                    {noti.createdAt ? formatDate(noti.createdAt) : 'Just now'}
                                </span>
                            </DropdownItem>
                        ))
                    )}
                </div>
            </div>
        </Dropdown>
    );
};
