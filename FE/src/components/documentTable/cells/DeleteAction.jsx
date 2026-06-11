import { useState } from "react";
import { CustomButton } from "../../button";
import { deleteRequest } from "../../../api/apiHelpers";
import { pushSuccess, pushError } from "../../toast";
import { PopUpModal } from "../../popUpModal";

export const DeleteAction = ({ document, className, onDeleteSuccess }) => {
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

    const handleDelete = async () => {
        try {
            await deleteRequest({
                url: `/documents/${document.id}`,
            });

            onDeleteSuccess?.(document.id);
            pushSuccess("Document deleted successfully.");

        } catch (err) {
            pushError(
                err?.response?.data?.message ||
                "Failed to delete document."
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
                title="Delete Document?"
                description={`Are you sure you want to delete "${document?.name}"?`}
                confirmText="Delete"
                cancelText="Cancel"
            />
        </>
    );
}