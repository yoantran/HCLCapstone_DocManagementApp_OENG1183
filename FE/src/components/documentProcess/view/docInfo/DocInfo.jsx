import { formatSize, formatDate } from "../../../../utils/formatFields";

export const DocInfo = ({ document }) => {
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
    } = document;

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
                    <Badge
                        label="Uploaded At"
                        value={formatDate(uploadedDateTime)}
                    />

                    <Badge
                        label="Last Viewed"
                        value={formatDate(latestViewedDateTime)}
                    />
                </div>
            </div>


        </div>
    );
};

const Badge = ({ label, value }) => (
    <div>
        <p className="text-white">{label}</p>
        <p className="font-bold text-white">
            {value || 'N/A'}
        </p>
    </div>
);