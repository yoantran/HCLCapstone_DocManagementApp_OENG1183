import { useState } from 'react';
import { postRequest } from '../../api/apiHelpers';

import {Checkbox, FloatingLabel, Label, TextInput} from 'flowbite-react';
import { CustomButton} from '../../components/button';
import {CustomLabel} from "../../components/label/index.jsx";
import {CustomTextInput} from "../../components/textInput/index.jsx";

function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

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
                localStorage.setItem('token', response.token);
                setSuccess('Login successful');
            } else {
                setError(response?.message || 'Login failed');
            }
        } catch (err) {
            setError('Login failed');
            console.error('Login error:', err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <form className="flex max-w-md flex-col gap-4" onSubmit={handleSubmit}>
                <div>
                    <div className="mb-2 block">
                        <Label htmlFor="email1">Your email</Label>
                    </div>
                    <CustomTextInput
                        id="email1"
                        type="email"
                        placeholder="name@flowbite.com"
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
                <CustomButton outline color={"red"} type="submit" disabled={loading}>
                    {loading ? 'Signing in...' : 'Submit'}
                </CustomButton>
            </form>

            {error ? <p style={{ color: 'crimson', marginTop: '12px' }}>{error}</p> : null}
            {success ? <p style={{ color: 'green', marginTop: '12px' }}>{success}</p> : null}
        </div>
    );
}

export default Login;
