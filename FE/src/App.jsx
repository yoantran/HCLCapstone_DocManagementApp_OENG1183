import './App.css'

import { useState } from 'react'
import { getRequest } from './api/apiHelpers'
import Login from './pages/auth/Login'
import {ToastContainer} from "react-toastify";
import {CustomButton} from "./components/button/index.jsx";


function App() {
  const [testLoading, setTestLoading] = useState(false)
  const [testResult, setTestResult] = useState('')
  const [testError, setTestError] = useState('')

  const handleTestFetch = async () => {
    setTestLoading(true)
    setTestError('')
    setTestResult('')

    const response = await getRequest({ url: '/users/me' })

    if (response?.response) {
      setTestError(response.response.data?.message || response.message || 'API test failed')
    } else if (response?.message && !response?.email) {
      setTestError(response.message)
    } else {
      setTestResult(JSON.stringify(response, null, 2))
    }

    setTestLoading(false)
  }

  return (
    <>
      <div style={{ maxWidth: '360px', margin: '24px auto 0', padding: '24px' }}>

        <CustomButton onClick={handleTestFetch} disabled={testLoading}>
          {testLoading ? 'Fetching test data...' : 'Test GET /users/me'}
        </CustomButton>

        {testError ? <p style={{ color: 'crimson', marginTop: '12px' }}>{testError}</p> : null}
        {testResult ? (
          <pre
            style={{
              marginTop: '12px',
              padding: '12px',
              borderRadius: '8px',
              background: '#f4f4f5',
              overflowX: 'auto',
              whiteSpace: 'pre-wrap',
            }}
          >
            {testResult}
          </pre>
        ) : null}
      </div>
      <Login />
      <ToastContainer />
    </>
  )
}

export default App
