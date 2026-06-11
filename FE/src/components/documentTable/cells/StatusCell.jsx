import { Icon } from "../../icons";
import { Tooltip } from "flowbite-react";

export const StatusCell = ({ document }) => {
    const status = document.secureStatus ?? null;

    if (status === null) {
        return <Tooltip content="Malware scan pending" style="light">
            <Icon name="hour-glass" size={24} className="" />
        </Tooltip>;
    }

    return <span>{status}</span>;
}