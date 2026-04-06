import cv2

print("Testing webcam...")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Windows specific

if not cap.isOpened():
    print("ERROR: Cannot open webcam!")
    print("Trying without CAP_DSHOW...")
    cap = cv2.VideoCapture(0)
    
if cap.isOpened():
    print("SUCCESS: Webcam opened")
    ret, frame = cap.read()
    if ret:
        print(f"SUCCESS: Got frame: {frame.shape}")
        cv2.imwrite("test_frame.jpg", frame)
        print("Saved test_frame.jpg")
    else:
        print("ERROR: Cannot read frame")
else:
    print("FAILED: Webcam not accessible")
    
cap.release()