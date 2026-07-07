import { useState } from "react";
import { CustomButton } from "../button/index.jsx";
import { deleteRequest } from "../../api/apiHelpers.js";
import { pushSuccess, pushError } from "../toast/index.jsx";
import { PopUpModal } from "../popUpModal/index.jsx";

export const DeleteAction = ({
                                 document,
                                 row, // Generic standard item reference
                                 idKey = "id",  // The key to find the item's unique identifier
                                 nameKey = "name",  // key to find the display name
                                 itemName: passedItemName,
                                 endpoint = "/documents", // API path prefix
                                 entityLabel = "Document", // Text used in confirmation messages and toasts
                                 className,
                                 onDeleteSuccess,
}) => {
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

    const targetItem = row || document;
    const itemId = targetItem?.[idKey];


    const itemName = passedItemName || targetItem?.[nameKey] || "<Unknown>";

    const handleDelete = async () => {
        if (!itemId) {
            pushError("Cannot delete")
        }

        try {
            await deleteRequest({
                url: `${endpoint}/${itemId}`,
            });

            onDeleteSuccess?.(itemId);
            pushSuccess(`${entityLabel} deleted successfully.`);

        } catch (err) {
            pushError(
                err?.response?.data?.message ||
                `Failed to delete ${entityLabel.toLowerCase()}.`
            );
        } finally {
            setShowDeleteConfirm(false);
        }
    };

    return (
        <>
            <CustomButton
                className={`hover:cursor-pointer ${className}`}
                onClick={(e) => {
                    e.stopPropagation();
                    setShowDeleteConfirm(true);
                }}
            >
                Delete
            </CustomButton>

            <PopUpModal
                isOpen={showDeleteConfirm}
                onClose={() => setShowDeleteConfirm(false)}
                onConfirm={(e) => {
                    e.stopPropagation();
                    handleDelete()
                }}
                title={`Delete ${entityLabel}?`}
                description={`Are you sure you want to delete ${entityLabel.toLowerCase()} "${itemName}"?`}
                confirmText="Delete"
                cancelText="Cancel"
            />
        </>
    );
}