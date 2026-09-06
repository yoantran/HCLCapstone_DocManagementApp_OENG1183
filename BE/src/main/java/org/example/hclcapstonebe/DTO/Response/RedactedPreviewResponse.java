package org.example.hclcapstonebe.DTO.Response;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.example.hclcapstonebe.Enums.RedactedPreviewStatus;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class RedactedPreviewResponse {
    private RedactedPreviewStatus status;
    private String previewUrl;    // set only when status == READY
    private String failureReason; // set only when status == FAILED
}
