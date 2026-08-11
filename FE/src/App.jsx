import './App.css'
import { RouterProvider } from "react-router-dom";
import { router } from './pages/routes';
import { ToastContainer } from 'react-toastify';

function App() {
  return (
    <>
        {/*<div className="h-screen w-screen overflow-hidden flex flex-col">*/}
        <RouterProvider router={router} />
        <ToastContainer />
        {/*</div>*/}
    </>
  )
}

export default App
