import { useState } from 'react';
import { postRequest } from '../../api/apiHelpers';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

import {Checkbox, Label} from 'flowbite-react';
import { CustomButton} from '../../components/button';
import {CustomTextInput} from "../../components/textInput/index.jsx";


// TODO: WIP Login
function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const navigate = useNavigate();
    const { login } = useAuth();

    const handleSubmit = async (event) => {
        event.preventDefault();
        setLoading(true);
        setError('');
        setSuccess('');

        try {
            const response = await postRequest({
                url: '/auth/login',
                data: { email, password },
            });

            if (response?.token) {
                // const role = response.role
                const userId = response.id || response._id || response.user?.id || response.user?._id;
                const role = response.role || response.user?.role;
                const name = response.name || response.user?.name;
                const userEmail = response.email || response.user?.email;

                if (!userId) {
                    throw new Error("Server response did not include a valid User ID attribute.");
                }
                login(
                    { id: userId, email: userEmail, name, role },
                    response.token
                );
                navigate(`/${userId}/submit-request`, { replace: true });
            } else {
                setError(response?.message || 'Login failed');
            }
        } catch (err) {
            setError(err?.response?.data?.message || 'Invalid credentials or connection dropped.');
            console.error('Login submission fault context:', err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen w-full">
            <form className="flex max-w-md flex-col gap-4" onSubmit={handleSubmit}>
                <div>
                    <div className="mb-2 block">
                        <Label htmlFor="email1">Your email</Label>
                    </div>
                    <CustomTextInput
                        id="email1"
                        type="email"
                        placeholder="yourEmail@gmail.com"
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                        required
                    />
                </div>
                <div>
                    <div className="mb-2 block">
                        <Label htmlFor="password1">Your password</Label>
                    </div>
                    <CustomTextInput
                        id="password1"
                        type="password"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                        required
                    />
                </div>
                <div className="flex items-center gap-2">
                    <Checkbox id="remember" />
                    <Label htmlFor="remember">Remember me</Label>
                </div>
                <CustomButton type="submit" disabled={loading}>
                    {loading ? 'Signing in...' : 'Submit'}
                </CustomButton>
            </form>
            {error ? <p style={{ color: 'crimson', marginTop: '12px' }}>{error}</p> : null}
            {success ? <p style={{ color: 'green', marginTop: '12px' }}>{success}</p> : null}
        </div>
    );
}

export default Login;
