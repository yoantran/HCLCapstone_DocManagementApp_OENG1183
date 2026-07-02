import { useEffect, useRef, useState } from "react";
import { Label, Select } from "flowbite-react";
import avatar from "../../assets/avatar.svg";
import {pushError} from "../toast/index.jsx";
import {CustomTextInput} from "../textInput/index.jsx";
import {CustomButton} from "../button/index.jsx";

const MAX_AVATAR_BYTES = 10 * 1024 * 1024; // 10 MB

export function UserFormContent({
                                    initialData,
                                    onSave,
                                    saving,
                                    showDepartment = false,
                                    departments = [],
                                    layout = "stacked" // 'stacked' for Profile, 'split' for Admin Modal
                                }) {
    const [name, setName] = useState("");
    const [phoneNumber, setPhoneNumber] = useState("");
    const [selectedDepartment, setSelectedDepartment] = useState("");
    const [avatarFile, setAvatarFile] = useState(null);
    const [avatarPreview, setAvatarPreview] = useState(null);
    const fileInputRef = useRef(null);

    useEffect(() => {
        if (initialData) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setName(initialData.name || initialData.user || "");
            setPhoneNumber(initialData.phoneNumber || "");
            setSelectedDepartment(initialData.department || initialData.departmentName || "");
            setAvatarFile(null);
            setAvatarPreview(null);
        }
    }, [initialData]);

    const handleAvatarChange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        if (file.size > MAX_AVATAR_BYTES) {
            pushError("Avatar must be under 10 MB.");
            e.target.value = "";
            return;
        }
        setAvatarFile(file);
        setAvatarPreview(URL.createObjectURL(file));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        const formData = new FormData();
        if (name.trim()) formData.append("name", name.trim());
        if (phoneNumber.trim()) formData.append("phoneNumber", phoneNumber.trim());
        if (showDepartment && selectedDepartment) formData.append("department", selectedDepartment);
        if (avatarFile) formData.append("avatar", avatarFile);

        onSave(formData);
    };

    const displayAvatar = avatarPreview || initialData?.avatarSignedUrl || avatar;
    const hasChanges =
        name.trim() !== (initialData?.name || initialData?.user || "") ||
        phoneNumber.trim() !== (initialData?.phoneNumber || "") ||
        (showDepartment && selectedDepartment !== (initialData?.department || initialData?.departmentName || "")) ||
        avatarFile;

    const AvatarSection = () => (
        <div className="flex flex-col items-center gap-3 mb-6">
            <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="group relative h-24 w-24 overflow-hidden rounded-full border-2 border-(--dark-blue-300) cursor-pointer transition-all duration-160 ease-out hover:border-(--lighter-blue-500)"
            >
                <img src={displayAvatar} alt="Avatar" className="h-full w-full object-cover" />
                <span className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity duration-160 ease-out">
                    <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 10.5h.008v.008h-.008V10.5Z" />
                    </svg>
                </span>
            </button>
            <input ref={fileInputRef} type="file" accept="image/jpeg,image/png" className="hidden" onChange={handleAvatarChange} />
            {avatarFile && <p className="text-xs text-(--cool-gray-500) max-w-50 truncate">{avatarFile.name}</p>}
        </div>
    );

    const FormFields = () => (
        <div className="flex flex-col gap-5 w-full">
            <div>
                <Label className="mb-2 block" htmlFor="form-name">Change Name</Label>
                <CustomTextInput id="form-name" type="text" value={name} onChange={(e) => setName(e.target.value)} />
            </div>

            <div>
                <Label className="mb-2 block" htmlFor="form-phone">Change Phone Number</Label>
                <CustomTextInput id="form-phone" type="tel" value={phoneNumber} onChange={(e) => setPhoneNumber(e.target.value)} />
            </div>

            {showDepartment && (
                <div>
                    <Label className="mb-2 block" htmlFor="form-dept">Assigned Department</Label>
                    <Select id="form-dept" value={selectedDepartment} onChange={(e) => setSelectedDepartment(e.target.value)}>
                        <option value="">Select Department...</option>
                        {departments.map((dept, idx) => {
                            const dName = typeof dept === "string" ? dept : dept.name;
                            return <option key={idx} value={dName}>{dName}</option>;
                        })}
                    </Select>
                </div>
            )}

            <div className="flex justify-end mt-2">
                <CustomButton type="submit" disabled={saving || !hasChanges} className="w-full sm:w-fit">
                    {saving ? "Saving…" : "Apply"}
                </CustomButton>
            </div>
        </div>
    );

    if (layout === "split") {
        return (
            <form onSubmit={handleSubmit} className="w-full flex flex-col md:flex-row gap-8 items-start text-left">
                {/* eslint-disable-next-line react-hooks/static-components */}
                <div className="flex-1 w-full"><FormFields /></div>
                {/* eslint-disable-next-line react-hooks/static-components */}
                <div className="w-full md:w-1/3 flex justify-center bg-gray-900/30 p-4 rounded-lg border border-(--dark-blue-300)"><AvatarSection /></div>
            </form>
        );
    }

    return (
        <form onSubmit={handleSubmit} className="w-full max-w-sm flex flex-col items-center">
            {/* eslint-disable-next-line react-hooks/static-components */}
            <AvatarSection />
            {/* eslint-disable-next-line react-hooks/static-components */}
            <FormFields />
        </form>
    );
}