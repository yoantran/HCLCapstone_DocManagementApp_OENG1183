import { useEffect, useRef, useState } from "react";
import { Label } from "flowbite-react";
import { CustomButton } from "../components/button";
import { CustomTextInput } from "../components/textInput";
import { getRequest, putFormDataRequest } from "../api/apiHelpers";
import { pushSuccess, pushError } from "../components/toast";
import defaultAvatar from "../assets/avatar.svg";

const MAX_AVATAR_BYTES = 10 * 1024 * 1024; // 10 MB

export default function Profile() {
    const [profile, setProfile] = useState(null);
    const [name, setName] = useState("");
    const [phoneNumber, setPhoneNumber] = useState("");
    const [avatarFile, setAvatarFile] = useState(null);
    const [avatarPreview, setAvatarPreview] = useState(null);
    const [saving, setSaving] = useState(false);
    const fileInputRef = useRef(null);

    useEffect(() => {
        getRequest({ url: "/users/me" })
            .then((data) => setProfile(data))
            .catch(() => pushError("Failed to load profile."));
    }, []);

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

    const handleApply = async () => {
        setSaving(true);
        try {
            const formData = new FormData();
            if (name.trim()) formData.append("name", name.trim());
            if (phoneNumber.trim()) formData.append("phoneNumber", phoneNumber.trim());
            if (avatarFile) formData.append("avatar", avatarFile);

            const updated = await putFormDataRequest({ url: "/users/me", data: formData });
            setProfile(updated);
            setAvatarFile(null);
            setAvatarPreview(null);
            setName("");
            setPhoneNumber("");
            pushSuccess("Profile updated.");
        } catch (err) {
            pushError(err?.response?.data?.message || "Failed to update profile.");
        } finally {
            setSaving(false);
        }
    };

    if (!profile) return null;

    const displayAvatar = avatarPreview || profile.avatarSignedUrl || defaultAvatar;

    const hasChanges = name.trim() || phoneNumber.trim() || avatarFile;

    return (
        <div className="w-full flex flex-col items-center justify-center text-left pt-10">

            {/* Avatar */}
            <div className="flex flex-col items-center gap-3 mb-8">
                <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="group relative h-24 w-24 overflow-hidden rounded-full border-2 border-(--dark-blue-300) cursor-pointer transition-all duration-[160ms] ease-out hover:border-(--lighter-blue-500)"
                    aria-label="Upload new profile picture"
                >
                    <img src={displayAvatar} alt="Avatar" className="h-full w-full object-cover" />
                    {/* hover overlay */}
                    <span className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity duration-[160ms] ease-out">
                        <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" />
                            <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 10.5h.008v.008h-.008V10.5Z" />
                        </svg>
                    </span>
                </button>


                <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/png"
                    className="hidden"
                    onChange={handleAvatarChange}
                />
                {avatarFile && (
                    <p className="text-xs text-(--cool-gray-500) max-w-[200px] truncate">{avatarFile.name}</p>
                )}
            </div>

            {/* Greeting */}
            <div className="w-full max-w-sm mb-1">
                <p className="text-sm text-(--text)">
                    Hi, <span className="font-semibold text-white">{profile.name}</span>
                    {profile.departmentName && (
                        <span className="text-(--cool-gray-500)"> · {profile.departmentName}</span>
                    )}
                </p>
            </div>

            <div className="w-full max-w-sm h-px bg-(--dark-blue-300) my-6" />

            {/* Form */}
            <form
                className="w-full max-w-sm flex flex-col gap-5"
                onSubmit={(e) => { e.preventDefault(); handleApply(); }}
            >
                <div>
                    <Label className="mb-2 block" htmlFor="profile-name">
                        Change Your Name
                    </Label>
                    <CustomTextInput
                        id="profile-name"
                        type="text"
                        placeholder={profile.name ?? ""}
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                    />
                </div>

                <div>
                    <Label className="mb-2 block" htmlFor="profile-phone">
                        Change Your Phone Number
                    </Label>
                    <CustomTextInput
                        id="profile-phone"
                        type="tel"
                        placeholder={profile.phoneNumber ?? "Enter phone number"}
                        value={phoneNumber}
                        onChange={(e) => setPhoneNumber(e.target.value)}
                    />
                </div>

                <div className="flex justify-end">
                    <CustomButton
                        type="submit"
                        disabled={saving || !hasChanges}
                        className="w-fit"
                    >
                        {saving ? "Saving…" : "Apply"}
                    </CustomButton>
                </div>
            </form>
        </div>
    );
}
