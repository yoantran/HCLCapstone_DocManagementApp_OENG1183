import { describe, it, expect, vi, beforeEach } from 'vitest';

const { toastMock } = vi.hoisted(() => ({
    toastMock: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}));

vi.mock('react-toastify', () => ({ toast: toastMock }));

import { pushWarning } from '../components/toast/index.jsx';

// Real, confirmed bug: pushWarning called toast.error instead of
// toast.warning -- every warning toast (e.g. DownloadButton's "Preview is
// still generating") was classed/announced as an error despite the custom
// warning icon/colors.
describe('pushWarning', () => {
    beforeEach(() => {
        toastMock.success.mockReset();
        toastMock.error.mockReset();
        toastMock.warning.mockReset();
    });

    it('calls toast.warning, not toast.error', () => {
        pushWarning('Preview is still generating.');

        expect(toastMock.warning).toHaveBeenCalledTimes(1);
        expect(toastMock.error).not.toHaveBeenCalled();
    });
});
