import { PdfViewer } from './PdfViewer';
import { CsvViewer } from './CsvViewer';
import { ImageViewer } from './ImageViewer';
import { DocxViewer } from './DocxViewer';
import { UnsupportedViewer } from './UnsupportedViewer';

export const PublicViewer = ({ fileUrl, fileType }) => {
    switch (fileType?.toLowerCase()) {
        case 'pdf':
            return <PdfViewer fileUrl={fileUrl} />;

        case 'csv':
            return <CsvViewer fileUrl={fileUrl} />;

        case 'doc':
        case 'docx':
            return <DocxViewer fileUrl={fileUrl} />

        case 'png':
        case 'jpg':
        case 'jpeg':
            return <ImageViewer fileUrl={fileUrl} />;

        default:
            return <UnsupportedViewer />;
    }
};