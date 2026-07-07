import { Icon } from "../../icons";
import { Tooltip } from "flowbite-react";

export const StatusCell = ({ row, document }) => {
    // const status = document.secureStatus ?? null;

    const item = row || document;
    const status = item?.secureStatus ?? null;

    if (status === null) {
        return <Tooltip content="Malware scan pending" style="light">
            <Icon name="hour-glass" size={24} className="" />
        </Tooltip>;
    }

    return <span>{status}</span>;
}