"""
Image preprocessing utilities for AI models
"""
import cv2
import numpy as np
from typing import Tuple, Optional
from loguru import logger


class ImagePreprocessor:
    """Preprocess images for AI model input"""
    
    @staticmethod
    def resize_with_aspect_ratio(
        image: np.ndarray,
        target_size: Tuple[int, int],
        interpolation: int = cv2.INTER_AREA
    ) -> np.ndarray:
        """
        Resize image while maintaining aspect ratio
        
        Args:
            image: Input image
            target_size: (width, height)
            interpolation: OpenCV interpolation method
            
        Returns:
            Resized image
        """
        h, w = image.shape[:2]
        target_w, target_h = target_size
        
        # Calculate scaling factor
        scale = min(target_w / w, target_h / h)
        
        # Calculate new dimensions
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # Resize
        resized = cv2.resize(image, (new_w, new_h), interpolation=interpolation)
        
        # Create canvas and center image
        canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        y_offset = (target_h - new_h) // 2
        x_offset = (target_w - new_w) // 2
        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
        
        return canvas
    
    @staticmethod
    def normalize(
        image: np.ndarray,
        mean: Tuple[float, float, float] = (0.485, 0.456, 0.406),
        std: Tuple[float, float, float] = (0.229, 0.224, 0.225)
    ) -> np.ndarray:
        """
        Normalize image with ImageNet statistics
        
        Args:
            image: Input image (0-255)
            mean: Mean values for RGB channels
            std: Standard deviation for RGB channels
            
        Returns:
            Normalized image
        """
        # Convert to float and scale to [0, 1]
        normalized = image.astype(np.float32) / 255.0
        
        # Apply mean and std
        normalized = (normalized - mean) / std
        
        return normalized
    
    @staticmethod
    def denormalize(
        image: np.ndarray,
        mean: Tuple[float, float, float] = (0.485, 0.456, 0.406),
        std: Tuple[float, float, float] = (0.229, 0.224, 0.225)
    ) -> np.ndarray:
        """Reverse normalization"""
        denorm = (image * std) + mean
        denorm = np.clip(denorm * 255, 0, 255).astype(np.uint8)
        return denorm
    
    @staticmethod
    def enhance_contrast(
        image: np.ndarray,
        clip_limit: float = 2.0,
        tile_grid_size: Tuple[int, int] = (8, 8)
    ) -> np.ndarray:
        """
        Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        
        Args:
            image: Input BGR image
            clip_limit: Threshold for contrast limiting
            tile_grid_size: Size of grid for histogram equalization
            
        Returns:
            Enhanced image
        """
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        l_enhanced = clahe.apply(l)
        
        # Merge channels and convert back
        enhanced = cv2.merge([l_enhanced, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        return enhanced
    
    @staticmethod
    def adjust_brightness(
        image: np.ndarray,
        factor: float = 1.2
    ) -> np.ndarray:
        """
        Adjust image brightness
        
        Args:
            image: Input image
            factor: Brightness factor (>1 brighter, <1 darker)
            
        Returns:
            Adjusted image
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        
        v = np.clip(v * factor, 0, 255).astype(np.uint8)
        
        hsv = cv2.merge([h, s, v])
        adjusted = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        return adjusted
    
    @staticmethod
    def denoise(
        image: np.ndarray,
        strength: int = 10
    ) -> np.ndarray:
        """
        Apply denoising to image
        
        Args:
            image: Input image
            strength: Denoising strength
            
        Returns:
            Denoised image
        """
        return cv2.fastNlMeansDenoisingColored(image, None, strength, strength, 7, 21)
    
    @staticmethod
    def sharpen(image: np.ndarray, amount: float = 1.0) -> np.ndarray:
        """
        Sharpen image
        
        Args:
            image: Input image
            amount: Sharpening amount
            
        Returns:
            Sharpened image
        """
        kernel = np.array([
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ]) * amount
        
        sharpened = cv2.filter2D(image, -1, kernel)
        return sharpened
    
    @staticmethod
    def crop_to_bbox(
        image: np.ndarray,
        bbox: Tuple[int, int, int, int],
        padding: float = 0.0
    ) -> np.ndarray:
        """
        Crop image to bounding box with optional padding
        
        Args:
            image: Input image
            bbox: (x1, y1, x2, y2)
            padding: Padding ratio
            
        Returns:
            Cropped image
        """
        x1, y1, x2, y2 = bbox
        h, w = image.shape[:2]
        
        if padding > 0:
            width = x2 - x1
            height = y2 - y1
            
            x1 = max(0, int(x1 - width * padding))
            y1 = max(0, int(y1 - height * padding))
            x2 = min(w, int(x2 + width * padding))
            y2 = min(h, int(y2 + height * padding))
        
        return image[y1:y2, x1:x2]
    
    @staticmethod
    def align_face(
        image: np.ndarray,
        landmarks: dict,
        output_size: Tuple[int, int] = (112, 112)
    ) -> Optional[np.ndarray]:
        """
        Align face using landmarks (eyes, nose, mouth)
        
        Args:
            image: Input image
            landmarks: Dictionary with landmark coordinates
            output_size: Desired output size
            
        Returns:
            Aligned face image
        """
        try:
            # Get eye coordinates
            left_eye = landmarks.get('left_eye')
            right_eye = landmarks.get('right_eye')
            
            if not left_eye or not right_eye:
                return None
            
            # Calculate angle
            dY = right_eye[1] - left_eye[1]
            dX = right_eye[0] - left_eye[0]
            angle = np.degrees(np.arctan2(dY, dX))
            
            # Calculate desired eye positions
            desired_left_eye = (0.35 * output_size[0], 0.35 * output_size[1])
            desired_right_eye = (0.65 * output_size[0], 0.35 * output_size[1])
            
            # Get center point between eyes
            eyes_center = (
                (left_eye[0] + right_eye[0]) // 2,
                (left_eye[1] + right_eye[1]) // 2
            )
            
            # Get rotation matrix
            M = cv2.getRotationMatrix2D(eyes_center, angle, 1.0)
            
            # Calculate translation
            tX = output_size[0] * 0.5
            tY = output_size[1] * 0.35
            M[0, 2] += (tX - eyes_center[0])
            M[1, 2] += (tY - eyes_center[1])
            
            # Apply affine transformation
            aligned = cv2.warpAffine(
                image,
                M,
                output_size,
                flags=cv2.INTER_CUBIC
            )
            
            return aligned
            
        except Exception as e:
            logger.error(f"Face alignment failed: {e}")
            return None
    
    @staticmethod
    def augment_image(
        image: np.ndarray,
        rotation_range: int = 10,
        brightness_range: float = 0.2,
        flip_horizontal: bool = False
    ) -> np.ndarray:
        """
        Apply random augmentation for training
        
        Args:
            image: Input image
            rotation_range: Max rotation in degrees
            brightness_range: Brightness variation range
            flip_horizontal: Whether to randomly flip
            
        Returns:
            Augmented image
        """
        augmented = image.copy()
        h, w = augmented.shape[:2]
        
        # Random rotation
        if rotation_range > 0:
            angle = np.random.uniform(-rotation_range, rotation_range)
            M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
            augmented = cv2.warpAffine(augmented, M, (w, h))
        
        # Random brightness
        if brightness_range > 0:
            factor = np.random.uniform(1 - brightness_range, 1 + brightness_range)
            augmented = ImagePreprocessor.adjust_brightness(augmented, factor)
        
        # Random horizontal flip
        if flip_horizontal and np.random.rand() > 0.5:
            augmented = cv2.flip(augmented, 1)
        
        return augmented