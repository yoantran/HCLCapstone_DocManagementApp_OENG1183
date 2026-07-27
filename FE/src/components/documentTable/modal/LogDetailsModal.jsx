import {
    Modal,
    ModalHeader,
    ModalBody,
    Badge

} from "flowbite-react";

export const LogDetailsModal = ({ log, show, onClose, position = "center" }) => {
    if (!log) return null;

    const displayTimestamp = log.timestamp
        ? new Date(log.timestamp).toLocaleDateString('vi-VN') + ' at ' +
        new Date(log.timestamp).toLocaleTimeString('vi-VN', { hour12: false })
        : 'N/A';

    const displayIp = log.clientIp === "0:0:0:0:0:0:0:1" ? "127.0.0.1" : (log.clientIp ?? 'N/A');

    const displayAction = log.action ? log.action.split('.').pop() : 'N/A';

    const statusColor = log.status >= 500 ? 'failure'
        : log.status >= 400 ? 'warning'
            : log.status >= 200 ? 'success'
                : 'gray';

    const methodColor = {
        GET: 'blue', POST: 'green', PUT: 'yellow', PATCH: 'yellow', DELETE: 'red'
    }[log.method] ?? 'gray';

    return (
        <Modal dismissible show={show} onClose={onClose} position={position}>
            <ModalHeader className="bg-(--dark-blue-700) px-8">
                <div className="flex items-center gap-2 text-white">
                    <span>Log details</span>
                </div>
            </ModalHeader>

            <ModalBody className="bg-(--dark-blue-700) p-0 px-8">

                {/* action banner */}
                <div className="px-5 py-4 border-b border-(--cool-gray-500)/30 ">
                    <div className="flex justify-between gap-2 mb-1">
                        <span className="flex font-mono font-bold text-white">ACTION: {displayAction}</span>
                        <div className="flex gap-2 font-bold">
                            <Badge color={methodColor} className="flex">{log.method ?? 'N/A'}</Badge>
                            <Badge color={statusColor} className="flex">{log.status ?? 'N/A'}</Badge>
                        </div>

                    </div>
                    <div className="font-mono text-yellow-400">{log.path ?? 'N/A'}</div>
                </div>

                <div className="px-5 py-4 flex flex-col gap-5">

                    {/* user section */}
                    <div>
                        <p className="font-bold uppercase tracking-widest text-(--ch-cool-gray) pb-2">User</p>
                        <table className="w-full">
                            <tbody>
                                {[
                                    ['Name', log.name ?? 'N/A'],
                                    ['User ID', log.userId ?? 'N/A'],
                                    ['Email', log.email ?? 'N/A'],
                                    ['Role', log.role?.replace('ROLE_', '') ?? 'N/A'],
                                ].map(([label, val]) => (
                                    <tr key={label}>
                                        <td className="text-(--ch-cool-gray) py-1 w-24">{label}</td>
                                        <td className="text-white py-1">{val}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* request section */}
                    <div className="border-t border-(--cool-gray-500)/30 pt-4">
                        <p className="font-bold uppercase tracking-widest text-(--ch-cool-gray) pb-2">Request</p>
                        <table className="w-full">
                            <tbody>
                                {[
                                    ['Timestamp', displayTimestamp],
                                    ['Client IP', displayIp],
                                    ['Duration', log.durationMs != null ? `${log.durationMs} ms` : 'N/A'],
                                ].map(([label, val]) => (
                                    <tr key={label}>
                                        <td className="text-(--ch-cool-gray) py-1 w-24">{label}</td>
                                        <td className="text-white py-1">{val}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* error section */}
                    <div className="border-t border-(--cool-gray-500)/30 pt-4">
                        <p className="font-bold uppercase tracking-widest text-(--ch-cool-gray) mb-2">Error</p>
                        <div className="font-mono text-xs rounded bg-(--lighter-blue-800) border border-(--cool-gray-500)/30 px-3 py-2 my-4 text-(--ch-cool-gray)">
                            {log.error ?? 'null'}
                        </div>
                    </div>

                </div>
            </ModalBody>
        </Modal>
    );
};