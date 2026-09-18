import { DOC_MULTIPART_ENDPOINTS } from "../constants";

export const buildFormData = (payload) => {
    const formData = new FormData();

    Object.entries(payload).forEach(([key, value]) => {
        if (Array.isArray(value)) {
            value.forEach((item) => formData.append(key, item));
        } else {
            formData.append(key, value);
        }
    });

    return formData;
};

export const buildMultipartFormPayload = ({ documentType, cards, proposedRepaymentAmount }) => {
    const files = cards.map((card) => card.file);
    const isMultiple = files.length > 1;

    const payload = isMultiple
        ? { type: documentType, files }
        : { type: documentType, file: files[0] };

    if (proposedRepaymentAmount) payload.proposedRepaymentAmount = proposedRepaymentAmount;

    return {
        url: isMultiple ? DOC_MULTIPART_ENDPOINTS.multiple : DOC_MULTIPART_ENDPOINTS.single,
        data: buildFormData(payload),
    };
};