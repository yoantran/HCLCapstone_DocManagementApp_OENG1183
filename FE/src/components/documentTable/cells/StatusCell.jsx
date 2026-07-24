import { Icon } from "../../icons";
import { Tooltip } from "flowbite-react";

export const StatusCell = ({ row, document }) => {
    const item = row || document;
    const status = item?.scanStatus;

    switch (status) {
        case null:
        case undefined:
        case "NOT_SCANNED":
            return (
                <Tooltip content="Document has not been scanned yet" style="light">
                    <Icon name="clock-arrow" size={20} className="text-blue-500" />
                </Tooltip>
            );

        case "PENDING":
            return (
                <Tooltip content="Malware scan is in progress" style="light">
                    <Icon name="hour-glass" size={20} className="animate-spin" />
                </Tooltip>
            );

        case "CLEAN":
            return (
                <Tooltip content="No malware detected" style="light">
                    <Icon name="shield-check" size={24} className="text-green-500" />
                </Tooltip>
            );

        case "INFECTED":
            return (
                <Tooltip content="Malware detected" style="light">
                    <Icon name="exit-sign" size={24} className="text-red-500" />
                </Tooltip>
            );

        case "ERROR":
            return (
                <Tooltip content="Malware scan failed" style="light">
                    <Icon name="warning-sign" size={22} className="text-yellow-500" />
                </Tooltip>
            );

        default:
            return <span>{status}</span>;
    }
};