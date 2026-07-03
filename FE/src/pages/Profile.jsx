import { useEffect, useState } from "react";
import { getRequest, putFormDataRequest } from "../api/apiHelpers";
import { pushSuccess, pushError } from "../components/toast";
import { useAuth } from "../context/AuthContext";
import {UserFormContent} from "../components/userFormContent/index.jsx";

export default function Profile() {
    const { updateUser } = useAuth();
    const [profile, setProfile] = useState(null);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        getRequest({ url: "/users/me" })
            .then((data) => setProfile(data))
            .catch(() => pushError("Failed to load profile."));
    }, []);

    const handleApply = async (formData) => {
        setSaving(true);
        try {

            const updated = await putFormDataRequest({ url: "/users/me", data: formData });
            setProfile(updated);
            updateUser({ name: updated.name, avatarSignedUrl: updated.avatarSignedUrl });
            pushSuccess("Profile updated.");
        } catch (err) {
            pushError(err?.response?.data?.message || "Failed to update profile.");
        } finally {
            setSaving(false);
        }
    };

    if (!profile) return null;

    return (
        <div className="w-full flex flex-col items-center justify-center text-left pt-10">
            <div className="w-full max-w-sm mb-1">
                <p className="text-sm text-(--text)">
                    Hi, <span className="font-semibold text-white">{profile.name}</span>
                    {profile.departmentName && (
                        <span className="text-(--cool-gray-500)"> · {profile.departmentName}</span>
                    )}
                </p>
            </div>
            <div className="w-full max-w-sm h-px bg-(--dark-blue-300) my-6" />

            <UserFormContent
                initialData={profile}
                onSave={handleApply}
                saving={saving}
                layout="stacked"
            />
        </div>
    );
}
