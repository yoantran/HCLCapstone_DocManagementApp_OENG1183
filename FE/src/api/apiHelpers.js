import axios from './axiosInstance';


export const getRequest = async ({ url, params = {} }) => {
    const res = await axios.get(url, { params });
    return res.data;
};

export const postRequest = async ({ url, data = {}, params = {} }) => {
    const res = await axios.post(url, data, { params });
    return res.data;
};

export const postFormDataRequest = async ({ url, data = {}, params = {} }) => {
    const res = await axios.post(url, data, {
        params,
        headers: {
            "Content-Type": "multipart/form-data"
        },
    });
    return res.data;
};

export const patchRequest = async ({ url, data = {}, params = {} }) => {
    const res = await axios.patch(url, data, { params });
    return res.data;
};

export const patchFormDataRequest = async ({ url, data = {}, params = {} }) => {
    const res = await axios.patch(url, data, {
        params,
        headers: {
            "Content-Type": "multipart/form-data"
        },
    });
    return res.data;
};

export const putRequest = async ({ url, data = {}, params = {} }) => {
    const res = await axios.put(url, data, { params });
    return res.data;
};

export const putFormDataRequest = async ({ url, data = {}, params = {} }) => {
    const res = await axios.put(url, data, {
        params,
        headers: {
            "Content-Type": "multipart/form-data"
        },
    });
    return res.data;
};

export const deleteRequest = async ({ url, params = {} }) => {
    const res = await axios.delete(url, { params });
    return res.data;
};