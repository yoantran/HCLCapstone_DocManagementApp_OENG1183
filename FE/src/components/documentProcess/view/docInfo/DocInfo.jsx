import { useEffect, useState } from "react";
import { formatSize, formatDate, parseServerDate } from "../../../../utils/formatFields";

export const DocInfo = ({ document, aiResult }) => {
    if (!document) {
        return (
            <div className="rounded-lg border border-gray-200 p-4">
                <p className="text-gray-500">Document information unavailable.</p>
            </div>
        );
    }

    const {
        id,
        name,
        type,
        format,
        uploaderName,
        uploadedDateTime,
        latestViewedDateTime,
        byteSize,
        aiProcessed,
        aiProcessingFailed,
        aiFailureReason,
        requesterIsOwner,
    } = document;

    const fieldKeysByType = {
        BALANCE_SHEET: [
            "total_current_assets",
            "total_assets",
            "total_current_liabilities",
            "total_liabilities",
            "total_equity",
        ],

        PAY_SLIP: [
            "name",
            "address",
            "abn",
            "bsb",
            "account_number",
            "salary",
            "income",
            "annual_salary",
            "dates",
            "phone",
        ],

        CONTRACT: [
            "name",
            "address",
            "abn",
            "bsb",
            "account_number",
            "salary",
            "income",
            "income_basis",
            "annual_salary",
            "dates",
            "phone",
        ],
    };

    const visibleFieldKeys = fieldKeysByType[type] ?? [];

    const visibleFields = aiResult?.fields
        ? visibleFieldKeys
            .filter((key) => key in aiResult.fields)
            .map((key) => [key, aiResult.fields[key]])
            .filter(([, value]) => {
                if (value === null || value === undefined) return false;
                if (Array.isArray(value) && value.length === 0) return false;
                return true;
            })
        : [];

    const formatAiValue = (value) => {
        if (Array.isArray(value)) {
            return value.join(", ");
        }

        return String(value);
    };

    return (
        <div className="mb-10 rounded-xl bg-(--dark-blue-700) text-white">
            <p className="text-sm opacity-80">
                {type?.replaceAll("_", " ")}
            </p>

            <h2 className="font-extrabold">
                {name}
            </h2>

            <p className="text-sm opacity-80">
                ID: {id}
            </p>

            <div className="flex flex-row justify-between">
                <div className="mt-6 flex flex-wrap gap-3">
                    <Badge label="Format" value={format} />
                    <Badge label="File Size" value={formatSize(byteSize)} />
                    <Badge label="Uploaded by" value={uploaderName} />
                </div>
                <div className="mt-6 flex flex-wrap gap-5">
                    <Badge label="Uploaded At" value={formatDate(uploadedDateTime)} />
                    <Badge label="Last Viewed" value={formatDate(latestViewedDateTime)} />
                </div>
            </div>

            {/* analysis header */}
            <div className="border-gray-300 px-6 py-4 mt-3">
                <h3 className="text-lg font-bold">
                    Document Analysis
                </h3>
                <p className="mt-1 text-sm text-gray-500">
                    Extracted information and assessment result
                </p>
            </div>


            {!aiProcessed && !aiProcessingFailed && (
                <ProcessingIndicator uploadedDateTime={uploadedDateTime} />
            )}

            {aiProcessingFailed && (
                <div className="mt-2 border-t border-white/10 pt-4 text-sm text-red-300">
                    AI processing failed{aiFailureReason ? `: ${aiFailureReason}` : "."} Try re-uploading.
                </div>
            )}

            {aiProcessed && !aiResult && (
                <div className="mt-2 border-t border-white/10 pt-4 text-sm opacity-60 italic">
                    (AI analysis results are not available at this time)
                </div>
            )}

            {aiProcessed && aiResult && (
                <div className="mt-1 border-t border-white/10 pt-6">
                    <div className="rounded-md border border-gray-300 bg-white text-gray-900 shadow-sm">

                        {/* Extracted Fields */}
                        {visibleFields.length > 0 && (
                            <div className="px-6 py-5">
                                <h4 className="mb-3 text-sm font-bold uppercase tracking-wide text-gray-700">
                                    Extracted Fields
                                </h4>

                                <div className="overflow-hidden border border-gray-300">
                                    <table className="w-full text-sm">
                                        <tbody>
                                            {visibleFields.map(([key, value]) => (
                                                <FormRow
                                                    key={key}
                                                    label={key.replaceAll("_", " ")}
                                                    value={formatAiValue(value)}
                                                />
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {/* Loan Readiness */}
                        {aiResult.loan_readiness && (
                            <div className="border-t border-gray-300 px-6 py-5">
                                <h4 className="mb-3 text-sm font-bold uppercase tracking-wide text-gray-700">
                                    Loan Readiness Assessment
                                </h4>

                                <div className="overflow-hidden border border-gray-300">
                                    <table className="w-full text-sm">
                                        <tbody>
                                            <FormRow
                                                label="Verdict"
                                                value={
                                                    <Verdict value={aiResult.loan_readiness.verdict} />
                                                }
                                            />

                                            {aiResult.loan_readiness.income_source && (
                                                <FormRow
                                                    label="Income Source"
                                                    value={aiResult.loan_readiness.income_source.replaceAll("_", " ")}
                                                />
                                            )}

                                            {aiResult.loan_readiness.income_basis && (
                                                <FormRow
                                                    label="Income Basis"
                                                    value={aiResult.loan_readiness.income_basis.replaceAll("_", " ")}
                                                />
                                            )}

                                            {(aiResult.loan_readiness.checks?.repayment_ratio?.value != null ||
                                                aiResult.loan_readiness.checks?.repayment_ratio?.threshold != null) && (
                                                    <FormRow
                                                        label="Repayment Ratio"
                                                        value={
                                                            aiResult.loan_readiness.checks.repayment_ratio.value != null
                                                                ? `${(aiResult.loan_readiness.checks.repayment_ratio.value * 100).toFixed(1)}%`
                                                                : "N/A"
                                                        }
                                                        note={
                                                            aiResult.loan_readiness.checks.repayment_ratio.threshold != null
                                                                ? `Threshold: ${(aiResult.loan_readiness.checks.repayment_ratio.threshold * 100).toFixed(1)}%`
                                                                : undefined
                                                        }
                                                    />
                                                )}

                                            {(aiResult.loan_readiness.checks?.dti?.value != null ||
                                                aiResult.loan_readiness.checks?.dti?.threshold != null) && (
                                                    <FormRow
                                                        label="Debt to Income"
                                                        value={
                                                            aiResult.loan_readiness.checks.dti.value != null
                                                                ? `${(aiResult.loan_readiness.checks.dti.value * 100).toFixed(1)}%`
                                                                : "N/A"
                                                        }
                                                        note={
                                                            aiResult.loan_readiness.checks.dti.threshold != null
                                                                ? `Threshold: ${(aiResult.loan_readiness.checks.dti.threshold * 100).toFixed(1)}%`
                                                                : undefined
                                                        }
                                                    />
                                                )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {/* Balance Sheet Readiness */}
                        {aiResult.balance_sheet_readiness && (
                            <div className="border-t border-gray-300 px-6 py-5">
                                <h4 className="mb-3 text-sm font-bold uppercase tracking-wide text-gray-700">
                                    Balance Sheet Assessment
                                </h4>

                                <div className="overflow-hidden border border-gray-300">
                                    <table className="w-full text-sm">
                                        <tbody>
                                            <FormRow
                                                label="Verdict"
                                                value={
                                                    <Verdict value={aiResult.balance_sheet_readiness.verdict} />
                                                }
                                            />

                                            {(aiResult.balance_sheet_readiness.checks?.current_ratio?.value != null ||
                                                aiResult.balance_sheet_readiness.checks?.current_ratio?.threshold != null) && (
                                                    <FormRow
                                                        label="Current Ratio"
                                                        value={
                                                            aiResult.balance_sheet_readiness.checks.current_ratio.value != null
                                                                ? aiResult.balance_sheet_readiness.checks.current_ratio.value.toFixed(2)
                                                                : "N/A"
                                                        }
                                                        note={
                                                            aiResult.balance_sheet_readiness.checks.current_ratio.threshold != null
                                                                ? `Required: ≥ ${aiResult.balance_sheet_readiness.checks.current_ratio.threshold.toFixed(2)}`
                                                                : undefined
                                                        }
                                                    />
                                                )}

                                            {(aiResult.balance_sheet_readiness.checks?.debt_to_equity?.value != null ||
                                                aiResult.balance_sheet_readiness.checks?.debt_to_equity?.threshold != null) && (
                                                    <FormRow
                                                        label="Debt to Equity"
                                                        value={
                                                            aiResult.balance_sheet_readiness.checks.debt_to_equity.value != null
                                                                ? aiResult.balance_sheet_readiness.checks.debt_to_equity.value.toFixed(2)
                                                                : "N/A"
                                                        }
                                                        note={
                                                            aiResult.balance_sheet_readiness.checks.debt_to_equity.threshold != null
                                                                ? `Required: ≤ ${aiResult.balance_sheet_readiness.checks.debt_to_equity.threshold.toFixed(2)}`
                                                                : undefined
                                                        }
                                                    />
                                                )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {requesterIsOwner === false && (
                            <div className="border-t border-gray-300 bg-gray-50 px-6 py-3">
                                <p className="text-xs italic text-gray-500">
                                    Some sensitive fields are hidden because you are not the document owner.
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            )}

        </div>
    );
};

// Real per-stage progress would need the AI service to report intermediate
// state through BE -- not worth the backend lift here. This just proves the
// upload is alive and gives a rough ETA so users aren't staring at nothing.
const EXPECTED_PROCESSING_SECONDS = 200;

const ProcessingIndicator = ({ uploadedDateTime }) => {
    const [now, setNow] = useState(Date.now());

    useEffect(() => {
        const interval = setInterval(() => setNow(Date.now()), 1000);
        return () => clearInterval(interval);
    }, []);

    const uploadedAt = parseServerDate(uploadedDateTime);
    const elapsedSeconds = uploadedAt
        ? Math.max(0, Math.floor((now - uploadedAt.getTime()) / 1000))
        : 0;

    const minutes = Math.floor(elapsedSeconds / 60);
    const seconds = elapsedSeconds % 60;
    const elapsedLabel = `${minutes}:${String(seconds).padStart(2, "0")}`;

    const progressPct = Math.min(95, (elapsedSeconds / EXPECTED_PROCESSING_SECONDS) * 100);

    return (
        <div className="mt-2 border-t border-white/10 pt-4">
            <p className="text-sm opacity-80 italic">
                Processing… this page updates automatically once AI analysis finishes.
            </p>

            <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-white/10">
                <div
                    className="h-full rounded-full bg-(--light-blue) transition-all duration-1000 ease-linear"
                    style={{ width: `${progressPct}%` }}
                />
            </div>

            <p className="mt-1.5 text-xs opacity-60">
                Elapsed: {elapsedLabel} — usually takes about 3 minutes
            </p>
        </div>
    );
};

const Badge = ({ label, value, highlight }) => {
    const verdictColor =
        highlight === 'READY' ? 'text-emerald-400' :
            highlight === 'NOT_READY' ? 'text-red-400' :
                highlight === 'INSUFFICIENT_DATA' ? 'text-yellow-400' :
                    'text-white';

    return (
        <div>
            <p className="text-white capitalize">{label}</p>
            <p className={`font-bold ${verdictColor}`}>
                {value ?? 'N/A'}
            </p>
        </div>
    );
};

const FormRow = ({ label, value, note }) => (
    <tr className="border-b border-gray-300 last:border-b-0">
        <td className="w-2/5 bg-gray-100 px-4 py-3 font-medium capitalize text-gray-700">
            {label}
        </td>

        <td className="px-4 py-3 font-semibold text-gray-900">
            {value ?? "N/A"}

            {note && (
                <span className="ml-3 text-xs font-normal text-gray-500">
                    ({note})
                </span>
            )}
        </td>
    </tr>
);

const Verdict = ({ value }) => {
    const style =
        value === "READY"
            ? "border-green-600 text-green-700"
            : value === "NOT_READY"
                ? "border-red-600 text-red-700"
                : value === "INSUFFICIENT_DATA"
                    ? "border-yellow-600 text-yellow-700"
                    : "border-gray-500 text-gray-700";

    return (
        <span
            className={`inline-block border px-3 py-1 text-xs font-bold tracking-wide ${style}`}
        >
            {value ?? "N/A"}
        </span>
    );
};