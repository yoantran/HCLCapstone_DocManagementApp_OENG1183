import {CustomButton} from "../../button/index.jsx";
import {Button, Card, Label, Modal, ModalBody, ModalHeader, Select} from "flowbite-react";
import {CustomTextInput} from "../../textInput/index.jsx";
import {useEffect, useState} from "react";
import {pushError, pushSuccess} from "../../toast/index.jsx";
import {putRequest} from "../../../api/apiHelpers.js";

export const DepartmentModal = ({
                                    show,
                                    onClose,
                                    department,
                                    users = [],
                                    onUpdateSuccess,
                                    position = "center"
                                }) => {
    const [depName, setDepName] = useState("");
    const [managerId, setManagerId] = useState("");
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (department) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setDepName(department.name || "");
            const currentManager = users.find(u => u.name === department.managerName);
            setManagerId(department.managerId || currentManager?.id || "");
        }
    }, [department, users]);

    if (!department) return null;

    // TODO: Can Staff be promoted to Manager?
    const handleSave = async (e) => {
        e.preventDefault();
        if (!depName.trim()) {
            pushError("Department name cannot be empty.");
            return;
        }

        setSaving(true);
        try {
            const jsonPayload = {};

            if (depName.trim() !== (department.name || "")) {
                jsonPayload.name = depName.trim();
            }

            if (managerId !== initialManagerId) {
                if (managerId === "") {
                    jsonPayload.managerId = "";
                } else {
                    jsonPayload.managerId = managerId;
                }
            }

            const updatedDep = await putRequest({
                url: `/admin/departments/${department.id}`,
                data: jsonPayload
            });

            pushSuccess("Department updated successfully.");
            onUpdateSuccess?.(updatedDep);
            onClose();
        } catch (err) {
            pushError(err.message || "Failed to update department records.");
        } finally {
            setSaving(false);
        }
    };

    const currentManagerObj = users.find(u => u.name === department.managerName);
    const initialManagerId = department.managerId || currentManagerObj?.id || "";

    const hasChanges =
        depName.trim() !== (department.name || "") ||
        managerId !== initialManagerId;

    return (
        <Modal dismissible show={show} onClose={onClose} position={position}>
            <ModalHeader className="bg-(--dark-blue-700)">
                <div className="text-white">Manage Department</div>
            </ModalHeader>

            <ModalBody className="bg-(--dark-blue-700) text-white flex justify-center">
                <Card className="w-full max-w-2xl bg-(--dark-blue-700) text-white">

                    <div className="mb-2">
                        <h5 className="text-2xl font-bold tracking-tight">{department.name || "_error Department"}</h5>
                        <p className="text-sm text-gray-400">
                            Department ID: {department.id}
                        </p>
                    </div>
                    <hr className="border-(--dark-blue-300) mb-6" />

                    <form onSubmit={handleSave} className="flex flex-col gap-5 text-left">

                        <div>
                            <Label className="mb-2 block text-gray-300" htmlFor="dep-name">
                                Rename Department
                            </Label>
                            <CustomTextInput
                                id="dep-name"
                                type="text"
                                value={depName}
                                onChange={(e) => setDepName(e.target.value)}
                                placeholder="Enter department name"
                            />
                        </div>

                        <div>
                            <Label className="mb-2 block text-gray-300" htmlFor="dep-manager">
                                Department Manager
                            </Label>
                            <Select
                                id="dep-manager"
                                value={managerId}
                                onChange={(e) => setManagerId(e.target.value)}
                                className="bg-(--code-bg)"
                            >
                                <option value="">Remove Current Manager</option>
                                {users.map((user) => (
                                    <option key={user.id} value={user.id}>
                                        {user.name} ({user.role || "unknown"})
                                    </option>
                                ))}
                            </Select>
                            <p className="text-xs text-gray-400 mt-1.5">
                                Setting this to "Remove Current Manager" will unassign current manager.
                            </p>
                        </div>

                        <div className="flex justify-end gap-4 mt-4 pt-4 border-t border-(--dark-blue-300)">
                            <Button
                                color="alternative"
                                onClick={onClose}
                                className="text-white border-white bg-(--dark-blue-700) px-4"
                            >
                                Cancel
                            </Button>
                            <CustomButton
                                type="submit"
                                disabled={saving || !hasChanges}
                                className="px-6"
                            >
                                {saving ? "Saving Changes…" : "Save Changes"}
                            </CustomButton>
                        </div>

                    </form>
                </Card>
            </ModalBody>
        </Modal>
    );
};