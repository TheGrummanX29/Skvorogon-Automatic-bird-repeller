import cv2
import numpy as np

print("OpenCV version:", cv2.__version__)

net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")
layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

with open("coco.names", "r") as f:
    classes = [line.strip() for line in f.readlines()]
    
bird_class_id = classes.index("bird")
print(f"Class 'bird' has ID: {bird_class_id}")

GROUP_DISTANCE = 100
MIN_FLOCK_SIZE = 3
BOX_PADDING = 15

def create_tracker():
    try:
        return cv2.TrackerCSRT.create()
    except AttributeError:
        try:
            return cv2.TrackerCSRT_create()
        except AttributeError:
            try:
                return cv2.TrackerMOSSE_create()
            except:
                return cv2.TrackerKCF_create()

tracker = None
tracking_active = False
target_flock_box = None
flock_id = None
flock_size = 0

cap = cv2.VideoCapture("Birds_Flying.mp4")
if not cap.isOpened():
    print("Error opening video file or camera")
    exit()

COLOR_INDIVIDUAL = (0, 255, 0)
COLOR_FLOCK = (0, 0, 255)
COLOR_TARGET = (255, 0, 0)

frame_count = 0
start_time = cv2.getTickCount()

while cap.isOpened():
    ret, frame = cap.read()
    frame_count += 1
    if not ret:
        print("End of video")
        break
        
    height, width = frame.shape[:2]
    
    if tracking_active and tracker is not None:
        success, box = tracker.update(frame)
        
        if success:
            x, y, w, h = [int(v) for v in box]
            cv2.rectangle(frame, (x, y), (x + w, y + h), COLOR_TARGET, 3)
            cv2.putText(frame, f"Tracked Flock ({flock_size} birds)", 
                        (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TARGET, 2)
            
            center_x = x + w // 2
            center_y = y + h // 2
            cv2.circle(frame, (center_x, center_y), 5, COLOR_TARGET, -1)
            
            cv2.putText(frame, f"Position: ({center_x}, {center_y})", 
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TARGET, 2)
        else:
            tracking_active = False
            tracker = None
            print("Tracker lost the flock! Switching to detection mode...")
    
    if not tracking_active:
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), (0, 0, 0), True, crop=False)
        
        net.setInput(blob)
        outs = net.forward(output_layers)
        
        bird_boxes = []
        
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                if confidence > 0.5 and class_id == bird_class_id:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    
                    bird_boxes.append([x, y, w, h])
        
        if not bird_boxes:
            cv2.imshow("Bird Flock Tracking", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27: break
            continue
        
        num_birds = len(bird_boxes)
        groups = [-1] * num_birds
        group_counter = 0
        
        def distance(box1, box2):
            cx1 = box1[0] + box1[2] / 2
            cy1 = box1[1] + box1[3] / 2
            cx2 = box2[0] + box2[2] / 2
            cy2 = box2[1] + box2[3] / 2
            return np.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)
        
        for i in range(num_birds):
            if groups[i] != -1:
                continue
                
            groups[i] = group_counter
            queue = [i]
            
            while queue:
                current = queue.pop(0)
                
                for j in range(num_birds):
                    if groups[j] != -1:
                        continue
                        
                    if distance(bird_boxes[current], bird_boxes[j]) < GROUP_DISTANCE:
                        groups[j] = group_counter
                        queue.append(j)
            
            group_counter += 1
        
        flock_dict = {}
        for i, group_id in enumerate(groups):
            if group_id not in flock_dict:
                flock_dict[group_id] = []
            flock_dict[group_id].append(bird_boxes[i])
        
        flocks_info = []
        for group_id, boxes in flock_dict.items():
            if group_id == -1 or len(boxes) < MIN_FLOCK_SIZE:
                continue
                
            x_min = min(box[0] for box in boxes)
            y_min = min(box[1] for box in boxes)
            x_max = max(box[0] + box[2] for box in boxes)
            y_max = max(box[1] + box[3] for box in boxes)
            
            x_min = max(0, x_min - BOX_PADDING)
            y_min = max(0, y_min - BOX_PADDING)
            x_max = min(width, x_max + BOX_PADDING)
            y_max = min(height, y_max + BOX_PADDING)
            
            width_flock = x_max - x_min
            height_flock = y_max - y_min
            
            flocks_info.append({
                'id': group_id,
                'box': (x_min, y_min, width_flock, height_flock),
                'size': len(boxes),
                'center': (x_min + width_flock // 2, y_min + height_flock // 2)
            })
        
        if flocks_info:
            target_flock = max(flocks_info, key=lambda x: x['size'])
            x, y, w, h = target_flock['box']
            
            if w > 0 and h > 0 and x < width and y < height:
                try:
                    tracker = create_tracker()
                    tracking_active = tracker.init(frame, (x, y, w, h))
                except Exception as e:
                    print(f"Error initializing tracker: {e}")
                    tracking_active = False
                    tracker = None
                
                if tracking_active:
                    flock_size = target_flock['size']
                    print(f"Tracking started for flock with {flock_size} birds!")
                else:
                    print("Failed to initialize tracker!")
            else:
                print(f"Invalid bounding box: ({x}, {y}, {w}, {h})")
            
        for flock in flocks_info:
            x, y, w, h = flock['box']
            cv2.rectangle(frame, (x, y), (x + w, y + h), COLOR_FLOCK, 2)
            cv2.putText(frame, f"Flock ({flock['size']} birds)", 
                       (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_FLOCK, 1)
    
    elapsed_time = (cv2.getTickCount() - start_time) / cv2.getTickFrequency()
    fps = frame_count / elapsed_time if elapsed_time > 0 else 0
    cv2.putText(frame, f"FPS: {fps:.1f}", (width - 150, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    
    cv2.imshow("Bird Flock Tracking", frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == 27:
        break
    elif key == ord('r'):
        tracking_active = False
        tracker = None
        print("Tracker reset by user!")

cap.release()
cv2.destroyAllWindows()