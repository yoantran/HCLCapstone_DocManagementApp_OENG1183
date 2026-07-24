import { formatDate } from "./formatFields";

export const getScanStatusInfo = (document) => {
    switch (document.scanStatus) {
        case "CLEAN":
            return {
                title: "0 MALWARE DETECTED",
                status: "Clean",
                description: document.scanMessage || "No malware detected.",
                date: document.scannedAt
                    ? formatDate(document.scannedAt)
                    : "-",
                color: "success",
            };

        case "INFECTED":
            return {
                title: "MALWARE DETECTED",
                status: "Infected",
                description: document.scanMessage || "Malware detected.",
                date: document.scannedAt
                    ? formatDate(document.scannedAt)
                    : "-",
                color: "failure",
            };

        case "PENDING":
            return {
                title: "SCAN PENDING",
                status: "Pending",
                description: "This document is waiting to be scanned.",
                date: "-",
                color: "warning",
            };

        case "ERROR":
            return {
                title: "SCAN FAILED",
                status: "Error",
                description:
                    document.scanMessage || "An error occurred during scanning.",
                date: "-",
                color: "failure",
            };

        default:
            return {
                title: "NOT SCANNED",
                status: "Not scanned",
                description: "Malware scanning has been skipped for this document.",
                date: "-",
                color: "gray",
            };
    }
};