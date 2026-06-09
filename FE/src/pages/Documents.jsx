import { useAuth } from '../context/AuthContext';

export default function Documents() {
    const { user, loading } = useAuth();
    console.log("user: ", user)

    return (
        <>
            DOCUMENTSSSS
        </>
    );
}