import { describe, it, expect, vi, beforeEach } from 'vitest';

const { postMock, patchMock, putMock } = vi.hoisted(() => ({
    postMock: vi.fn().mockResolvedValue({ data: {} }),
    patchMock: vi.fn().mockResolvedValue({ data: {} }),
    putMock: vi.fn().mockResolvedValue({ data: {} }),
}));

vi.mock('../api/axiosInstance', () => ({
    default: { post: postMock, patch: patchMock, put: putMock },
}));

import { postFormDataRequest, patchFormDataRequest, putFormDataRequest } from '../api/apiHelpers';

// Real, confirmed bug: these helpers used to hardcode
// `headers: { "Content-Type": "multipart/form-data" }` (no boundary), which
// happened to work only because axios's XHR adapter overrode it. Removing
// the header outright (an earlier attempt at this same fix) broke uploads
// for real: axiosInstance's own default Content-Type ('application/json')
// leaked through instead, and the BE rejected it with
// HttpMediaTypeNotSupportedException (confirmed against the real live BE).
// The correct fix explicitly unsets Content-Type per-request so axios's own
// FormData detection can set the real multipart header with a boundary.
describe('FormData request helpers unset Content-Type instead of hardcoding or omitting it', () => {
    beforeEach(() => {
        postMock.mockClear();
        patchMock.mockClear();
        putMock.mockClear();
    });

    it('postFormDataRequest explicitly unsets Content-Type', async () => {
        await postFormDataRequest({ url: '/documents', data: new FormData() });
        const [, , config] = postMock.mock.calls[0];
        expect(config.headers['Content-Type']).toBeUndefined();
        expect('Content-Type' in config.headers).toBe(true);
    });

    it('patchFormDataRequest explicitly unsets Content-Type', async () => {
        await patchFormDataRequest({ url: '/documents/1', data: new FormData() });
        const [, , config] = patchMock.mock.calls[0];
        expect(config.headers['Content-Type']).toBeUndefined();
        expect('Content-Type' in config.headers).toBe(true);
    });

    it('putFormDataRequest explicitly unsets Content-Type', async () => {
        await putFormDataRequest({ url: '/documents/1', data: new FormData() });
        const [, , config] = putMock.mock.calls[0];
        expect(config.headers['Content-Type']).toBeUndefined();
        expect('Content-Type' in config.headers).toBe(true);
    });
});
