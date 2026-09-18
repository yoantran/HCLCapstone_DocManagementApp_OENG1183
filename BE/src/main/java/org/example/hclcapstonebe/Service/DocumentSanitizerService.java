package org.example.hclcapstonebe.Service;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDDocumentCatalog;
import org.example.hclcapstonebe.Exception.BadRequestException;
import org.springframework.stereotype.Service;

import java.io.ByteArrayInputStream;
import java.util.Locale;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

// Structural-validation half of Huy's be/add-CDR branch (#247) -- non-mutating,
// inspects structure only, never touches the bytes actually stored/processed.
// That branch's sanitizeImage (mutating re-encode) stays unmerged: exhaustively
// re-verified against the real 25-image balance-sheet corpus, it gets wrong
// OCR-extracted values on 4/25 real images, a confirmed, deterministic
// regression -- not landed here.
@Service
public class DocumentSanitizerService {

    /**
     * Validates PDF structure to ensure it doesn't contain open actions or embedded files.
     *
     * @param pdfBytes Raw bytes of the PDF document.
     * @throws BadRequestException if the PDF contains open actions, embedded files, or is invalid.
     */
    public void validatePdfStructure(byte[] pdfBytes) {
        if (pdfBytes == null || pdfBytes.length == 0) {
            throw new BadRequestException("PDF content is empty");
        }

        try (PDDocument document = Loader.loadPDF(pdfBytes)) {
            PDDocumentCatalog catalog = document.getDocumentCatalog();
            if (catalog == null) {
                throw new BadRequestException("PDF catalog is missing");
            }

            if (catalog.getOpenAction() != null) {
                throw new BadRequestException("PDF contains forbidden open action execution elements");
            }

            if (catalog.getNames() != null && catalog.getNames().getEmbeddedFiles() != null) {
                throw new BadRequestException("PDF contains forbidden embedded files");
            }
        } catch (BadRequestException e) {
            throw e;
        } catch (Exception e) {
            throw new BadRequestException("Invalid PDF document structure: " + e.getMessage());
        }
    }

    /**
     * Validates DOCX zip structure to ensure it doesn't contain .bin entries or embedded objects.
     *
     * @param docxBytes Raw bytes of the DOCX document.
     * @throws BadRequestException if the DOCX contains .bin entries or word/embeddings/.
     */
    public void validateDocxStructure(byte[] docxBytes) {
        if (docxBytes == null || docxBytes.length == 0) {
            throw new BadRequestException("DOCX content is empty");
        }

        try (ByteArrayInputStream bais = new ByteArrayInputStream(docxBytes);
             ZipInputStream zipInput = new ZipInputStream(bais)) {

            ZipEntry entry;
            while ((entry = zipInput.getNextEntry()) != null) {
                String entryName = entry.getName();
                if (entryName != null) {
                    String lowerName = entryName.toLowerCase(Locale.ROOT);
                    if (lowerName.endsWith(".bin") || lowerName.contains("word/embeddings/")) {
                        throw new BadRequestException("DOCX file contains forbidden entry: " + entryName);
                    }
                }
                zipInput.closeEntry();
            }
        } catch (BadRequestException e) {
            throw e;
        } catch (Exception e) {
            throw new BadRequestException("Invalid DOCX zip structure: " + e.getMessage());
        }
    }
}
