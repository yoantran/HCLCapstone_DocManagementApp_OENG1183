// constants storing
export const API_BASE_URL = 'http://localhost:8080';

export const ACCEPTED_FILE_TYPES = {
    PDF: ".pdf,application/pdf",
    CSV: ".csv,text/csv",
    DOC: ".doc,.docx,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    PNG: "image/png",
    JPG: "image/jpeg",
};

export const DOC_MULTIPART_ENDPOINTS = {
    single: "/documents/upload",
    multiple: "/documents/upload/batch",
};