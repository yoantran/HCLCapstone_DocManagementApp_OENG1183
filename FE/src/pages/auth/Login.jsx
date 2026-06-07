import { useState } from 'react';
import { postRequest } from '../../api/apiHelpers';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

import {Checkbox, Label} from 'flowbite-react';
import { CustomButton} from '../../components/button';
import {CustomTextInput} from "../../components/textInput/index.jsx";
import {PopUpModal} from "../../components/popUpModal/index.jsx";
import {pushSuccess} from "../../components/toast/index.jsx";

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
                const role = response.role
                login(
                    { email: response.email, name: response.name, role },
                    response.token
                );
                navigate(role === 'ADMIN' ? '/admin' : '/');
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

    const [showConfirmModal, setShowConfirmModal] = useState(false);

    const handleExecuteAction = () => {
        console.log("Action confirmed and executed successfully!");
        pushSuccess("Successfully submitted!");
        setShowConfirmModal(false); // Close modal when finished
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

            <div>
                <CustomButton color="primary" onClick={() => setShowConfirmModal(true)}>
                    Complete Action
                </CustomButton>

                <PopUpModal
                    isOpen={showConfirmModal}
                    onClose={() => setShowConfirmModal(false)}
                    onConfirm={handleExecuteAction}
                    title="Are you sure you want to complete this action?"
                    description="This cannot be undone."
                    confirmText="Yes"
                    cancelText="No"
                />
            </div>
            {error ? <p style={{ color: 'crimson', marginTop: '12px' }}>{error}</p> : null}
            {success ? <p style={{ color: 'green', marginTop: '12px' }}>{success}</p> : null}
        </div>
    );
}

export default Login;
