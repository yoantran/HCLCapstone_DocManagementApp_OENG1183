import {useState} from "react";
import {patchRequest} from "../../../api/apiHelpers.js";
import {pushError, pushSuccess} from "../../toast/index.jsx";
import {Button, Card, Modal, ModalBody, ModalHeader} from "flowbite-react";
import {UserFormContent} from "../../userFormContent/index.jsx";
import {DeleteAction} from "../../action/DeleteAction.jsx";

export const UserModal = (
    {
        user,
        departments = [],
        show,
        onClose,
        position = 'center',
        onUpdateSuccess,
        onDeleteSuccess,
    }
) => {
    const [saving, setSaving] = useState(false)

    if (!user) return null;

    const handleAdminSave = async (formData) => {
        setSaving(true);
        try {
            const submittedDeptValue = formData.get("departmentId") || formData.get("department");

            const matchedDept = departments.find(dept => {
                const nameToCompare = typeof dept === "string" ? dept : dept.name;
                const idToCompare = typeof dept === "string" ? dept : dept.id;

                return nameToCompare === submittedDeptValue || String(idToCompare) === String(submittedDeptValue);
            })

            const finalDeptId = matchedDept?.id || submittedDeptValue;

            const cleanPayload = {
                departmentId: finalDeptId,
                staffId: user.id
            };

            const updated = await patchRequest({
                url: `/admin/users/${user.id}`,
                data: cleanPayload
            });

            pushSuccess("User's records updated successfully.");
            onUpdateSuccess?.(updated);
            onClose();
        } catch (error) {
            pushError(error.message || "Something went wrong.");
        } finally {
            setSaving(false);
        }
    }

    const isStaff = user.role?.toLowerCase() === "staff";

    return (
        <>
            <Modal dismissible show={show} onClose={onClose} position={position}>
                <ModalHeader className="bg-(--dark-blue-700)">
                    <div className="text-white">Manage User Account</div>
                </ModalHeader>

                <ModalBody className="flex justify-center bg-(--dark-blue-700)">
                    <Card className="w-full max-w-2xl bg-(--dark-blue-700) text-white border-none shadow-none">
                        <div className="mb-2">
                            <h5 className="text-2xl font-bold tracking-tight">{user.name || "Unknown"}</h5>
                            <p className="text-sm text-gray-400">ID: {user.id} · Role: <span
                                className="text-cyan-400 font-semibold uppercase text-xs">{user.role}</span></p>
                        </div>
                        <hr className="border-(--dark-blue-300) mb-4"/>

                        {/*TODO: Can Admin edit User info?*/}
                        <UserFormContent
                            initialData={user}
                            onSave={handleAdminSave}
                            saving={saving}
                            showDepartment={isStaff}
                            departments={departments}
                            layout="split"
                            readOnlyFields={true}
                        />
                    </Card>
                </ModalBody>

                <div className="flex justify-center gap-6 bg-(--dark-blue-700) px-10 pb-6">
                    <DeleteAction
                        row={user}
                        idKey="id"
                        nameKey="user"
                        itemName={user.name}
                        endpoint="/admin/users"
                        entityLabel="User Account"
                        className="bg-red-700 border border-red-700 hover:bg-(--dark-blue-700) w-1/2"
                        onDeleteSuccess={() => {
                            onDeleteSuccess?.(user.id);
                            onClose();
                        }}
                    />
                    <Button color="alternative" onClick={onClose}
                            className="text-white border-white bg-(--dark-blue-700) w-1/2">
                        Close
                    </Button>
                </div>
            </Modal>
        </>
    )
}