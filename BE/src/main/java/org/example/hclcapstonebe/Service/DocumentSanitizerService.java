package org.example.hclcapstonebe.Service;

import com.drew.imaging.ImageMetadataReader;
import com.drew.metadata.Metadata;
import com.drew.metadata.exif.ExifIFD0Directory;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDDocumentCatalog;
import org.example.hclcapstonebe.Exception.BadRequestException;
import org.springframework.stereotype.Service;

import javax.imageio.IIOImage;
import javax.imageio.ImageIO;
import javax.imageio.ImageWriteParam;
import javax.imageio.ImageWriter;
import javax.imageio.stream.ImageOutputStream;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.geom.AffineTransform;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.Iterator;
import java.util.Locale;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

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

    /**
     * Sanitizes an image by re-encoding pixel data, baking EXIF rotation into the image matrix,
     * filling white background for transparency, and preserving maximum quality for OCR.
     *
     * @param imageBytes Raw bytes of the original image.
     * @param format     Image format string (e.g. "jpeg", "jpg", "png").
     * @return Sanitized image byte array.
     * @throws BadRequestException if image data is invalid or decoding/encoding fails.
     */
    public byte[] sanitizeImage(byte[] imageBytes, String format) {
        if (imageBytes == null || imageBytes.length == 0) {
            throw new BadRequestException("Image data is empty");
        }

        BufferedImage originalImage;
        try {
            originalImage = ImageIO.read(new ByteArrayInputStream(imageBytes));
        } catch (IOException e) {
            throw new BadRequestException("Failed to read image data: " + e.getMessage());
        }

        if (originalImage == null) {
            throw new BadRequestException("Invalid or unsupported image data");
        }

        // Read EXIF orientation tag from original bytes
        int orientation = 1;
        try {
            Metadata metadata = ImageMetadataReader.readMetadata(new ByteArrayInputStream(imageBytes));
            ExifIFD0Directory directory = metadata.getFirstDirectoryOfType(ExifIFD0Directory.class);
            if (directory != null && directory.containsTag(ExifIFD0Directory.TAG_ORIENTATION)) {
                orientation = directory.getInt(ExifIFD0Directory.TAG_ORIENTATION);
            }
        } catch (Exception ignored) {
            // Fallback to normal orientation (1) if EXIF parsing is not applicable or fails
        }

        int origW = originalImage.getWidth();
        int origH = originalImage.getHeight();

        int targetWidth = origW;
        int targetHeight = origH;
        AffineTransform transform = new AffineTransform();

        switch (orientation) {
            case 6: // 90 degrees CW
                targetWidth = origH;
                targetHeight = origW;
                transform.translate(targetWidth, 0);
                transform.rotate(Math.toRadians(90));
                break;
            case 3: // 180 degrees CW
                targetWidth = origW;
                targetHeight = origH;
                transform.translate(targetWidth, targetHeight);
                transform.rotate(Math.toRadians(180));
                break;
            case 8: // 270 degrees CW (90 degrees CCW)
                targetWidth = origH;
                targetHeight = origW;
                transform.translate(0, targetHeight);
                transform.rotate(Math.toRadians(270));
                break;
            case 2: // Flip horizontal
                transform.translate(targetWidth, 0);
                transform.scale(-1, 1);
                break;
            case 4: // Flip vertical
                transform.translate(0, targetHeight);
                transform.scale(1, -1);
                break;
            case 5: // Flip vertical + Rotate 270 CW
                targetWidth = origH;
                targetHeight = origW;
                transform.translate(targetWidth, targetHeight);
                transform.scale(-1, 1);
                transform.rotate(Math.toRadians(270));
                break;
            case 7: // Flip horizontal + Rotate 90 CW
                targetWidth = origH;
                targetHeight = origW;
                transform.scale(-1, 1);
                transform.rotate(Math.toRadians(90));
                break;
            default:
                // Normal (1) or unhandled orientation
                break;
        }

        // Create new BufferedImage with TYPE_INT_RGB and rotated dimensions
        BufferedImage sanitizedImage = new BufferedImage(targetWidth, targetHeight, BufferedImage.TYPE_INT_RGB);
        Graphics2D g2d = sanitizedImage.createGraphics();

        try {
            g2d.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
            g2d.setRenderingHint(RenderingHints.KEY_RENDERING, RenderingHints.VALUE_RENDER_QUALITY);
            g2d.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

            // CRITICAL: Fill background with white to prevent transparent PNGs from turning black
            g2d.setColor(Color.WHITE);
            g2d.fillRect(0, 0, targetWidth, targetHeight);

            // Draw transformed original image onto canvas
            g2d.drawImage(originalImage, transform, null);
        } finally {
            g2d.dispose();
        }

        // Determine target format
        String normalizedFormat = format != null ? format.toLowerCase(Locale.ROOT).trim() : "png";
        if (normalizedFormat.contains("/")) {
            normalizedFormat = normalizedFormat.substring(normalizedFormat.lastIndexOf('/') + 1);
        }
        if (normalizedFormat.startsWith(".")) {
            normalizedFormat = normalizedFormat.substring(1);
        }

        ByteArrayOutputStream baos = new ByteArrayOutputStream();

        if ("jpg".equals(normalizedFormat) || "jpeg".equals(normalizedFormat)) {
            Iterator<ImageWriter> writers = ImageIO.getImageWritersByFormatName("jpeg");
            if (!writers.hasNext()) {
                writers = ImageIO.getImageWritersByFormatName("jpg");
            }
            if (!writers.hasNext()) {
                throw new BadRequestException("No JPEG ImageWriter found");
            }

            ImageWriter writer = writers.next();
            try (ImageOutputStream ios = ImageIO.createImageOutputStream(baos)) {
                writer.setOutput(ios);
                ImageWriteParam param = writer.getDefaultWriteParam();
                if (param.canWriteCompressed()) {
                    param.setCompressionMode(ImageWriteParam.MODE_EXPLICIT);
                    param.setCompressionQuality(1.0f);
                }
                writer.write(null, new IIOImage(sanitizedImage, null, null), param);
            } catch (IOException e) {
                throw new BadRequestException("Failed to write JPEG image: " + e.getMessage());
            } finally {
                writer.dispose();
            }
        } else if ("png".equals(normalizedFormat)) {
            try {
                boolean written = ImageIO.write(sanitizedImage, "png", baos);
                if (!written) {
                    throw new BadRequestException("Failed to write PNG image");
                }
            } catch (IOException e) {
                throw new BadRequestException("Failed to write PNG image: " + e.getMessage());
            }
        } else {
            try {
                boolean written = ImageIO.write(sanitizedImage, normalizedFormat, baos);
                if (!written) {
                    baos.reset();
                    written = ImageIO.write(sanitizedImage, "png", baos);
                    if (!written) {
                        throw new BadRequestException("Unsupported image format: " + format);
                    }
                }
            } catch (IOException e) {
                throw new BadRequestException("Failed to write image with format " + format + ": " + e.getMessage());
            }
        }

        return baos.toByteArray();
    }
}
