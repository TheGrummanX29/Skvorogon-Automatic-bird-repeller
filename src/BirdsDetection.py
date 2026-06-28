import cv2
import numpy as np

print("OpenCV version:", cv2.__version__)

# Загрузка модели YOLO
net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")
layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

# Загрузка классов объектов
with open("coco.names", "r") as f:
    classes = [line.strip() for line in f.readlines()]
    
# ID класса "птица"
bird_class_id = classes.index("bird")
print(f"Class 'bird' has ID: {bird_class_id}")

# Параметры группировки
GROUP_DISTANCE = 100  # Максимальное расстояние между птицами для объединения в стаю
MIN_FLOCK_SIZE = 3    # Минимальное количество птиц в стае
BOX_PADDING = 15      # Отступ вокруг стаи

# Функция для создания трекера (универсальная)
def create_tracker():
    # Пробуем разные методы создания трекера
    try:
        # Попробуем новый стиль
        return cv2.TrackerCSRT.create()
    except AttributeError:
        try:
            # Попробуем старый стиль
            return cv2.TrackerCSRT_create()
        except AttributeError:
            try:
                # Попробуем MOSSE как альтернативу
                return cv2.TrackerMOSSE_create()
            except:
                # Последняя попытка - KCF
                return cv2.TrackerKCF_create()

# Инициализация трекера
tracker = None
tracking_active = False
target_flock_box = None
flock_id = None
flock_size = 0

# Открытие видео
cap = cv2.VideoCapture("Birds_Flying.mp4")  # Используем веб-камеру для тестирования
if not cap.isOpened():
    print("Ошибка открытия видеофайла или камеры")
    exit()

# Цвета
COLOR_INDIVIDUAL = (0, 255, 0)  # Зеленый для отдельных птиц
COLOR_FLOCK = (0, 0, 255)       # Красный для стай
COLOR_TARGET = (255, 0, 0)      # Синий для отслеживаемой стаи

frame_count = 0
start_time = cv2.getTickCount()

while cap.isOpened():
    ret, frame = cap.read()
    frame_count += 1
    if not ret:
        print("Конец видео")
        break
        
    height, width = frame.shape[:2]
    
    # Если трекинг активен и трекер инициализирован, обновляем положение стаи
    if tracking_active and tracker is not None:
        success, box = tracker.update(frame)
        
        if success:
            # Рисуем отслеживаемую стаю
            x, y, w, h = [int(v) for v in box]
            cv2.rectangle(frame, (x, y), (x + w, y + h), COLOR_TARGET, 3)
            cv2.putText(frame, f"Tracked Flock ({flock_size} birds)", 
                        (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TARGET, 2)
            
            # Показываем центр стаи
            center_x = x + w // 2
            center_y = y + h // 2
            cv2.circle(frame, (center_x, center_y), 5, COLOR_TARGET, -1)
            
            # Показываем направление движения
            cv2.putText(frame, f"Position: ({center_x}, {center_y})", 
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TARGET, 2)
        else:
            # Если трекер потерял стаю, переключаемся в режим детекции
            tracking_active = False
            tracker = None
            print("Tracker lost the flock! Switching to detection mode...")
    
    # Если трекинг не активен, ищем стаи с помощью YOLO
    if not tracking_active:
        # Подготовка изображения для YOLO
        blob = cv2.dnn.blobFromImage(
            frame, 
            1/255.0, 
            (416, 416), 
            (0, 0, 0), 
            True, 
            crop=False
        )
        
        # Детекция объектов
        net.setInput(blob)
        outs = net.forward(output_layers)
        
        # Сбор обнаруженных птиц
        bird_boxes = []
        
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                if confidence > 0.5 and class_id == bird_class_id:
                    # Вычисление координат
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    
                    # Координаты углов
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    
                    bird_boxes.append([x, y, w, h])
        
        # Если птиц не обнаружено, переходим к следующему кадру
        if not bird_boxes:
            # Показываем кадр без трекера
            cv2.imshow("Bird Flock Tracking", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27: break
            continue
        
        # Создаем матрицу расстояний между птицами
        num_birds = len(bird_boxes)
        groups = [-1] * num_birds  # Группа для каждой птицы (-1 = не назначена)
        group_counter = 0
        
        # Функция расчета расстояния между двумя птицами
        def distance(box1, box2):
            # Центры прямоугольников
            cx1 = box1[0] + box1[2] / 2
            cy1 = box1[1] + box1[3] / 2
            cx2 = box2[0] + box2[2] / 2
            cy2 = box2[1] + box2[3] / 2
            
            # Евклидово расстояние
            return np.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)
        
        # Группируем птиц по близости
        for i in range(num_birds):
            if groups[i] != -1:
                continue  # Уже в группе
                
            # Начинаем новую группу
            groups[i] = group_counter
            queue = [i]
            
            while queue:
                current = queue.pop(0)
                
                # Проверяем соседей
                for j in range(num_birds):
                    if groups[j] != -1:
                        continue  # Уже в группе
                        
                    # Проверяем расстояние
                    if distance(bird_boxes[current], bird_boxes[j]) < GROUP_DISTANCE:
                        groups[j] = group_counter
                        queue.append(j)
            
            group_counter += 1
        
        # Собираем птиц по группам
        flock_dict = {}
        for i, group_id in enumerate(groups):
            if group_id not in flock_dict:
                flock_dict[group_id] = []
            flock_dict[group_id].append(bird_boxes[i])
        
        # Обрабатываем группы (стаи)
        flocks_info = []
        for group_id, boxes in flock_dict.items():
            if group_id == -1 or len(boxes) < MIN_FLOCK_SIZE:
                continue  # Пропускаем одиночных птиц и не назначенных
                
            # Находим общий ограничивающий прямоугольник
            x_min = min(box[0] for box in boxes)
            y_min = min(box[1] for box in boxes)
            x_max = max(box[0] + box[2] for box in boxes)
            y_max = max(box[1] + box[3] for box in boxes)
            
            # Добавляем отступ
            x_min = max(0, x_min - BOX_PADDING)
            y_min = max(0, y_min - BOX_PADDING)
            x_max = min(width, x_max + BOX_PADDING)
            y_max = min(height, y_max + BOX_PADDING)
            
            width_flock = x_max - x_min
            height_flock = y_max - y_min
            
            # Сохраняем информацию о стае
            flocks_info.append({
                'id': group_id,
                'box': (x_min, y_min, width_flock, height_flock),
                'size': len(boxes),
                'center': (x_min + width_flock // 2, y_min + height_flock // 2)
            })
        
        # Если нашли стаи, выбираем одну для трекинга
        if flocks_info:
            # Выбираем самую большую стаю (по количеству птиц)
            target_flock = max(flocks_info, key=lambda x: x['size'])
            x, y, w, h = target_flock['box']
            
            # Убедимся, что прямоугольник валиден
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
            
        # Рисуем все обнаруженные стаи (красным)
        for flock in flocks_info:
            x, y, w, h = flock['box']
            cv2.rectangle(frame, (x, y), (x + w, y + h), COLOR_FLOCK, 2)
            cv2.putText(frame, f"Flock ({flock['size']} birds)", 
                       (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_FLOCK, 1)
    
    # Рассчет и отображение FPS
    elapsed_time = (cv2.getTickCount() - start_time) / cv2.getTickFrequency()
    fps = frame_count / elapsed_time if elapsed_time > 0 else 0
    cv2.putText(frame, f"FPS: {fps:.1f}", (width - 150, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    
    # Показ результата
    cv2.imshow("Bird Flock Tracking", frame)
    
    # Выход по ESC
    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        break
    elif key == ord('r'):  # Принудительный сброс трекера
        tracking_active = False
        tracker = None
        print("Tracker reset by user!")

cap.release()
cv2.destroyAllWindows()