import {CustomButton} from "../button/index.jsx";
import {useState} from "react";

export const ManageAction = ({
                                 row,
                                 ModalComponent,
                                 modalProps = {},
                                 className = "",
                                 onSuccess,
                             }) => {
    const [showModal, setShowModal] = useState(false);

    return (
        <>
            <CustomButton
                className={`bg-slate-600/80 hover:bg-slate-500 text-white font-medium rounded-xl px-5 py-1.5 transition-all duration-150 border-none hover:cursor-pointer ${className}`}
                onClick={(e) => {
                    e.stopPropagation();
                    setShowModal(true);
                }}
            >
                Manage
            </CustomButton>

            {showModal && ModalComponent && (
                <ModalComponent
                    show={showModal}
                    onClose={() => setShowModal(false)}

                    row={row}
                    user={row}
                    department={row}

                    onUpdateSuccess={(updatedData) => {
                        onSuccess?.(updatedData);
                    }}

                    {...modalProps}
                />
            )}
        </>
    );
}