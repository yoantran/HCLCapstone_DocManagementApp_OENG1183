import { useState } from 'react';
import { postRequest } from '../../api/apiHelpers';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

import {Label} from 'flowbite-react';
import { CustomButton} from '../../components/button';
import {CustomTextInput} from "../../components/textInput/index.jsx";
import dmsLogo from "../../assets/DMSLogo.svg";


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
        <div className="w-full flex flex-col items-center justify-center text-left">
            <div className="flex justify-center">
                <div className="text-center">
                    <img
                        src={dmsLogo}
                        alt="DMS Icon"
                        className="w-[113px] object-contain"
                    />
                </div>
            </div>

            <div className="w-full max-w-sm mb-8">
                <h1 className="text-[38px] text-5xl-custom! font-serif leading-tight">
                    Log in
                </h1>
                <p className="text-base-custom! text-sm font-normal">
                    Welcome back! Please enter your details.
                </p>
            </div>

            <form className="w-full max-w-sm flex flex-col gap-5" onSubmit={handleSubmit}>
                <div>
                    <div className="flex flex-col gap-2">
                        <Label htmlFor="email1">Your email</Label>
                    </div>
                    <CustomTextInput
                        id="email1"
                        type="email"
                        placeholder="youremail@gmail.com"
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                        required
                    />
                </div>
                <div>
                    <div className="flex flex-col gap-2">
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

                <div className="w-full flex justify-end">
                    <button
                        type="button"
                        className="text-(--lighter-blue-500) hover:text-(--lighter-blue-300) text-xs font-medium transition-colors cursor-pointer"
                    >
                        Forgot my password
                    </button>
                </div>

                <div className=" flex justify-center">
                    <CustomButton type="submit" disabled={loading}
                                  className="w-fit"
                    >
                        {loading ? 'Signing in...' : 'Log In'}
                    </CustomButton>
                </div>
                {error ? <p style={{ color: 'crimson', marginTop: '12px' }}>{error}</p> : null}
                {success ? <p style={{ color: 'green', marginTop: '12px' }}>{success}</p> : null}
            </form>

            <div className="w-full max-w-sm mt-10">
                <div className="w-full h-px bg-(--dark-blue-300) mb-3" />
                <div className="text-center">
                    <button
                        type="button"
                        className="text-(--lighter-blue-500) hover:text-(--lighter-blue-300) text-xs font-medium tracking-wide transition-colors cursor-pointer"
                    >
                        Create a New Account
                    </button>
                </div>
            </div>
        </div>
    );
}

export default Login;
