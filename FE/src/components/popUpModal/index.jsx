import {Modal, ModalBody, Spinner} from "flowbite-react";
import {CustomButton} from "../button/index.jsx";


export const PopUpModal = ({
                               isOpen = false,
                               onClose,
                               onConfirm,
                               title = "Are you sure you want to complete this action?",
                               description = "This cannot be undone.",
                               confirmText = "Yes",
                               cancelText = "No",
                               size = "xl",
                               isLoading = false,
                           }) => {
    return (
        <Modal
            show={isOpen}
            size={size}
            onClose={isLoading ? undefined : onClose}
            popup
            className="bg-slate-900/50 backdrop-blur-sm"
        >
            <ModalBody className="p-8 bg-(--ch-light-canvas) rounded-lg">
                <div className="text-center px-4 py-2">

                    <h3 className="text-3xl font-(--heading) font-serif text-(--dark-blue-800) mb-2">
                        {title}
                    </h3>

                    <p className="text-xl font-(--heading) font-serif text-(--dark-blue-800)">
                        {description}
                    </p>

                    {/* Center Separation Rule Line */}
                    <hr className="my-8 border-(--accent-border) max-w-lg mx-auto" />

                    <div className="flex justify-center items-center gap-16 mt-4">
                        <CustomButton
                            color="red"
                            onClick={onClose}
                            disabled={isLoading}
                            className="px-8 py-1 text-base min-w-25 rounded-xl"
                        >
                            {cancelText}
                        </CustomButton>

                        <CustomButton
                            color="green"
                            onClick={onConfirm}
                            disabled={isLoading}
                            className="px-8 py-1 text-base min-w-25 rounded-xl"
                        >
                            {isLoading ? (
                                <span className="flex items-center justify-center gap-3">
                                    <Spinner size="sm" light={true} />
                                    <span> Loading...</span>
                                </span>
                            ) : (
                                confirmText
                            )}
                        </CustomButton>

                    </div>
                </div>
            </ModalBody>
        </Modal>
    );
};

