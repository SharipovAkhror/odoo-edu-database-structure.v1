/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { onMounted, onWillUnmount } from "@odoo/owl";

let mediaStream = null;

class CameraWizardFormController extends FormController {
    setup() {
        super.setup();
        
        onMounted(() => {
            this.setupCameraWidget();
        });
        
        onWillUnmount(() => {
            this.stopCamera();
        });
    }

    setupCameraWidget() {
        const self = this;
        const startBtn = document.getElementById('btn_start_camera');
        const captureBtn = document.getElementById('btn_capture_photo');
        const retakeBtn = document.getElementById('btn_retake');
        const startAttendanceBtn = document.getElementById('btn_start_attendance');
        const video = document.getElementById('camera_video');
        const canvas = document.getElementById('camera_canvas');
        const previewDiv = document.getElementById('preview_image');
        const capturedPhoto = document.getElementById('captured_photo');
        const placeholder = document.getElementById('camera_placeholder');

        if (!startBtn || !video || !canvas) {
            console.error('Camera widget elements not found');
            return;
        }

        // Start Camera Button
        if (startBtn) {
            startBtn.onclick = async function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                try {
                    mediaStream = await navigator.mediaDevices.getUserMedia({ 
                        video: { 
                            width: { ideal: 640 },
                            height: { ideal: 480 },
                            facingMode: "user"
                        } 
                    });
                    
                    video.srcObject = mediaStream;
                    video.style.display = 'block';
                    if (placeholder) placeholder.style.display = 'none';
                    if (previewDiv) previewDiv.style.display = 'none';
                    
                    startBtn.style.display = 'none';
                    captureBtn.style.display = 'inline-block';
                    retakeBtn.style.display = 'none';
                    startAttendanceBtn.style.display = 'none';
                    
                } catch (err) {
                    console.error('Camera access error:', err);
                    let errorMsg = 'Camera access denied. ';
                    if (err.name === 'NotAllowedError') {
                        errorMsg += 'Please allow camera access in your browser settings.';
                    } else if (err.name === 'NotFoundError') {
                        errorMsg += 'No camera found on this device.';
                    } else {
                        errorMsg += err.message;
                    }
                    alert(errorMsg);
                }
            };
        }

        // Capture Photo Button
        if (captureBtn) {
            captureBtn.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const context = canvas.getContext('2d');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                context.drawImage(video, 0, 0);
                
                canvas.toBlob((blob) => {
                    const reader = new FileReader();
                    reader.onloadend = function() {
                        const base64Data = reader.result.split(',')[1];
                        
                        // Update the model with the image
                        self.model.root.update({ teacher_image: base64Data });
                        
                        // Show preview
                        capturedPhoto.src = reader.result;
                        previewDiv.style.display = 'block';
                        video.style.display = 'none';
                        
                        // Stop camera
                        self.stopCamera();
                        
                        // Update buttons
                        captureBtn.style.display = 'none';
                        retakeBtn.style.display = 'inline-block';
                        startAttendanceBtn.style.display = 'inline-block';
                    };
                    reader.readAsDataURL(blob);
                }, 'image/jpeg', 0.85);
            };
        }

        // Retake Button
        if (retakeBtn) {
            retakeBtn.onclick = async function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                try {
                    mediaStream = await navigator.mediaDevices.getUserMedia({ 
                        video: { 
                            width: { ideal: 640 },
                            height: { ideal: 480 },
                            facingMode: "user"
                        } 
                    });
                    
                    video.srcObject = mediaStream;
                    video.style.display = 'block';
                    previewDiv.style.display = 'none';
                    
                    retakeBtn.style.display = 'none';
                    startAttendanceBtn.style.display = 'none';
                    captureBtn.style.display = 'inline-block';
                    
                } catch (err) {
                    console.error('Camera access error:', err);
                    alert('Camera access denied: ' + err.message);
                }
            };
        }
    }

    stopCamera() {
        if (mediaStream) {
            mediaStream.getTracks().forEach(track => track.stop());
            mediaStream = null;
        }
    }
}

registry.category("views").add("camera_wizard_form", {
    ...formView,
    Controller: CameraWizardFormController,
});