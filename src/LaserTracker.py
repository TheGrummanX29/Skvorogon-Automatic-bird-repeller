import cv2
import numpy as np

# Open video capture (0 is the default camera)
cap = cv2.VideoCapture(0)
# Define the color range for detecting the laser pointer (adjust values as needed)
# Assumes red laser pointer; adjust lower/upper bounds if laser color differs
lower_red = np.array([160, 100, 100])
upper_red = np.array([180, 255, 255])

# Set tolerance and distance thresholds in pixels
# Adjust based on camera resolution, calibration, and testing
tolerance_in_pixels = 10  # This represents ~10 cm tolerance
distance_threshold = 2.0  # Approximate distance threshold in meters

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    # Convert the frame to the HSV color space
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Create a mask for red color detection
    mask = cv2.inRange(hsv, lower_red, upper_red)

    # Apply Gaussian Blur to reduce noise
    mask = cv2.GaussianBlur(mask, (15, 15), 5)

    # Find contours in the mask
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        area = cv2.contourArea(contour)

        # Filter small contours to avoid false positives
        if area > 300:
            # Get the center of the detected laser dot
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])

                # Mark the detected laser pointer on the frame
                cv2.circle(frame, (cX, cY), 10, (0, 255, 0), -1)
                cv2.putText(frame, "Laser Detected", (cX - 20, cY - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                print(f"Laser detected at coordinates: ({cX}, {cY})")

    # Show the processed video frame
    cv2.imshow("Laser Pointer Detection", frame)

    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release video capture and close windows
cap.release()
cv2.destroyAllWindows()