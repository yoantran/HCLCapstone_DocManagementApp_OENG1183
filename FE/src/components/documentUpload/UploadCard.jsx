import { useId, useRef } from "react";
import { Select, FileInput, Label, Button } from "flowbite-react";

import { DOCUMENT_ACCEPTED_FILE_TYPES } from "../../constants";


export const UploadCard = ({ value, onChange, onClear, isInvalid = false, isFirst = true, firstDocumentType = "", onDocumentTypeChange }) => {
    const uniqueId = useId().replace(/:/g, "");
    const selectId = `file-${uniqueId}`;
    const fileInputId = `dropzone-file-${uniqueId}`;
    const fileInputRef = useRef(null);
    const documentType = value.documentType;
    const selectedFile = value.file;
    const fileName = value.fileName;

    const handleFileChange = (event) => {
        const nextFile = event.target.files?.[0] ?? null;

        onChange({
            file: nextFile,
            fileName: nextFile?.name ?? "",
            // documentType: nextDocumentType,
        });
    };

    const handleClear = () => {
        onClear();

        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }

        onChange({
            file: null,
            fileName: "",
        })
    };

    const handleDocumentTypeChange = (event) => {
        const nextDocumentType = event.target.value;
        onDocumentTypeChange?.(nextDocumentType);

        onChange({
            file: selectedFile,
            fileName,
            // documentType: nextDocumentType,
        });
    };

    return (
        <div
            className={`rounded-md py-3 px-1 justify-items-center w-[97%] mx-auto my-2 border ${isInvalid ? "border-red-500 ring-2 ring-red-200" : "border-(--color-primary-200)"
                }`}
        >
            <div className="flex w-[95%] flex-col gap-4 text-left md:flex-row md:gap-x-1 md:gap-y-0">
                <div className="w-full md:w-1/2">
                    <Label className="mb-2 block cursor-pointer" htmlFor={selectId}>
                        Document Type
                    </Label>
                    <Select
                        id={selectId}
                        required
                        value={firstDocumentType}
                        onChange={handleDocumentTypeChange}
                        disabled={!isFirst}
                        className="font-[inherit] font-light"
                    >
                        <option value="" disabled className="">
                            Select document type
                        </option>
                        <option value="CONTRACT">CONTRACT</option>
                        <option value="BALANCE_SHEET">BALANCE SHEET</option>
                        <option value="PAY_SLIP">PAY SLIP</option>
                    </Select>
                </div>

                <div className="w-full md:w-1/2">
                    <div id="fileUpload" className="max-w-md">
                        <Label className="mb-2 block" htmlFor={fileInputId}>
                            Upload Document
                        </Label>
                        <Label
                            htmlFor={fileInputId}
                            className="flex w-full cursor-pointer flex-col items-center justify-center rounded-lg border border-gray-300 bg-gray-50 hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:hover:border-gray-500 dark:hover:bg-gray-600"
                        >
                            <div className="flex items-center justify-center w-full">
                                <div className="w-4/5 pl-3">
                                    <p className="mb-2 font-[inherit] font-light dark:text-gray-400">
                                        <span>{fileName || "Click to upload document"}</span>
                                    </p>
                                </div>

                                <div className="w-1/5 flex items-center justify-center">
                                    <svg
                                        className="my-2 h-6 w-6 text-gray-500 dark:text-gray-400"
                                        aria-hidden="true"
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 20 16"
                                    >
                                        <path
                                            stroke="currentColor"
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth="1.5"
                                            d="M13 13h3a3 3 0 0 0 0-6h-.025A5.56 5.56 0 0 0 16 6.5 5.5 5.5 0 0 0 5.207 5.021C5.137 5.017 5.071 5 5 5a4 4 0 0 0 0 8h2.167M10 15V6m0 0L8 8m2-2 2 2"
                                        />
                                    </svg>
                                </div>
                            </div>
                            <FileInput
                                ref={fileInputRef}
                                id={fileInputId}
                                className="hidden"
                                accept={DOCUMENT_ACCEPTED_FILE_TYPES}
                                onChange={handleFileChange}
                            />
                        </Label>
                    </div>
                </div>

            </div>
            <div className="mt-2 justify-items-end w-[95%]">
                <Button color="light" className="cursor-pointer" size="sm" onClick={handleClear}>
                    Clear
                </Button>
            </div>
        </div>

    )
};