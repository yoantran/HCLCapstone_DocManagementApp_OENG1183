import { useState } from "react";
import { useNavigate } from 'react-router-dom';
import { UploadCard } from "./UploadCard";
import { Button } from "flowbite-react";
import { postFormDataRequest } from "../../api/apiHelpers";
import { buildMultipartFormPayload } from "../../utils/requestBuilder";
import { PopUpModal } from "../popUpModal";
import { pushSuccess, pushError } from "../toast";

export const DocumentUpload = () => {
    const createCard = (id) => ({
        id,
        file: null,
        fileName: "",
    });

    const [cards, setCards] = useState([createCard(0)]);
    const [nextCardId, setNextCardId] = useState(1);
    const [submitError, setSubmitError] = useState("");
    const [submitAttempted, setSubmitAttempted] = useState(false);
    const [documentType, setDocumentType] = useState("");
    const [showConfirmModal, setShowConfirmModal] = useState(false);
    const navigate = useNavigate();

    const handleAddDocument = () => {
        setCards((prev) => [...prev, { ...createCard(nextCardId), documentType }]);
        setNextCardId((prev) => prev + 1);
    };

    const handleRemoveDocument = (cardIdToRemove) => {
        setCards((prev) => prev.filter((card) => card.id !== cardIdToRemove));
    };

    const handleCardChange = (cardId, updates) => {
        setSubmitAttempted(false);
        setSubmitError("");

        setCards((prev) =>
            prev.map((card) => (card.id === cardId ? { ...card, ...updates } : card))
        );
    };

    const handleDocumentTypeChange = (type) => {
        setDocumentType(type);
        setCards((prev) => prev.map((card) => ({ ...card, documentType: type })));
    };

    const handleSubmit = () => {
        setSubmitAttempted(true);

        const hasIncompleteCard =
            cards.some(card => !card.file) || !documentType;

        if (hasIncompleteCard) {
            setSubmitError(
                "Please select the document type and upload a file for every card before submitting."
            );
            return;
        }

        setSubmitError("");
        setShowConfirmModal(true);
    };

    const handleConfirmSubmit = async () => {
        try {
            const { url, data } = buildMultipartFormPayload({
                documentType,
                cards,
            });

            await postFormDataRequest({ url, data });

            setShowConfirmModal(false);
            pushSuccess("Documents submitted successfully.");

            console.log("Submitted successfully");

            // success -> redirect
            navigate("../documents");
        }
        catch (err) {
            console.error(err);
            const message =
                err?.response?.data?.message ||
                "Failed to submit documents.";

            pushError(message);
            setSubmitError("Failed to submit request.");
            setShowConfirmModal(false);
        }
    };

    const handleClearAll = () => {
        setCards([createCard(0)]);
        setNextCardId(1);
        setDocumentType("");
        setSubmitError("");
        setSubmitAttempted(false);
    };

    return (
        <>
            <div className="w-full px-20 md:px-40 rounded-md py-10 bg-(--code-bg)">
                {/* title */}
                <div>
                    <h2 className="text-left">Add New Load Request</h2>
                </div>
                <hr className="dark:border-amber-50" />

                {/* upload cards */}
                <div>
                    {cards.map((card, index) => (
                        <div key={card.id} className="relative">
                            {cards.length > 1 && (
                                <button
                                    type="button"
                                    aria-label="Remove document"
                                    className="absolute right-0 top-1 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-gray-300 bg-white text-red-500 hover:border-red-400 hover:text-red-700 cursor-pointer"
                                    onClick={() => handleRemoveDocument(card.id)}
                                >
                                    x
                                </button>
                            )}
                            <div className="pt-2">
                                <UploadCard
                                    value={card}
                                    onChange={(updates) => handleCardChange(card.id, updates)}
                                    onClear={() => handleCardChange(card.id, createCard(card.id))}
                                    isInvalid={submitAttempted && ((index == 0 && !card.documentType) || !card.file)}
                                    isFirst={index === 0}
                                    firstDocumentType={documentType}
                                    onDocumentTypeChange={handleDocumentTypeChange}
                                />
                            </div>
                        </div>
                    ))}
                    <Button className="cursor-pointer w-full my-5 border text-(--text) hover:bg-gray-200 dark:bg-(--code-bg) bg-(--code-bg) dark:hover:bg-(--accent-bg)" size="sm" onClick={handleAddDocument}>
                        Add another document
                    </Button>
                </div>

                {/* button group */}
                <div className="flex gap-x-4 w-full">
                    <Button
                        className="cursor-pointer w-full bg-(--light-blue) dark:bg-(--light-blue) dark:hover:bg-(--code-bg) hover:text-(--light-blue) hover:bg-(--code-bg) border border-(--light-blue)"
                        size="sm"
                        onClick={handleSubmit}
                    >
                        Submit
                    </Button>

                    <Button
                        className="cursor-pointer w-full border border-red-700 text-red-700 dark:bg-(--code-bg) bg-(--code-bg) hover:border-red-800 hover:bg-red-800 hover:text-white focus:ring-red-300 dark:border-red-600 dark:text-red-500 dark:hover:border-red-700 dark:hover:bg-red-700 dark:hover:text-white dark:focus:ring-red-800"
                        size="sm"
                        onClick={handleClearAll}
                    >
                        Clear All
                    </Button>
                </div>

                {submitError && <p className="mt-3 text-left text-sm text-red-600">{submitError}</p>}
            </div>

            <PopUpModal
                isOpen={showConfirmModal}
                onClose={() => setShowConfirmModal(false)}
                onConfirm={handleConfirmSubmit}
                title="Submit document request?"
                description="Your documents will be uploaded and sent for processing."
                confirmText="Submit"
                cancelText="Cancel"
            />
        </>
    )
};