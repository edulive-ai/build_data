import cv2
import json
import numpy as np
from PIL import Image, ImageDraw
from doclayout_yolo import YOLOv10
from huggingface_hub import hf_hub_download

# --- Load model ---
filepath = hf_hub_download(
    repo_id="juliozhao/DocLayout-YOLO-DocStructBench",
    filename="doclayout_yolo_docstructbench_imgsz1024.pt"
)
model = YOLOv10(filepath)

# --- Input image path ---
image_path = "/home/batien/Desktop/build_data/books_to_images/test_tq/test_tq_page_013.png"

# --- Predict ---
det_res = model.predict(
    image_path,
    imgsz=1024,
    conf=0.2,
    device="cuda"
)

# --- Collect raw bounding boxes ---
bounding_boxes = []
boxes_xywh = []   # [x, y, w, h]
confidences = []

for result in det_res[0].boxes:
    x1, y1, x2, y2 = result.xyxy[0].tolist()
    class_id = result.cls[0].item()
    confidence = result.conf[0].item()
    bounding_boxes.append({
        "class_id": class_id,
        "confidence": confidence,
        "bbox": [x1, y1, x2, y2]
    })

    w = x2 - x1
    h = y2 - y1
    boxes_xywh.append([int(x1), int(y1), int(w), int(h)])
    confidences.append(float(confidence))

# --- Save before NMS ---
with open("bounding_boxes_before.json", "w") as f:
    json.dump(bounding_boxes, f, indent=2)

# --- Apply global NMS (all boxes, all classes) ---
score_threshold = 0.2
nms_threshold = 0.5
indices = cv2.dnn.NMSBoxes(boxes_xywh, confidences, score_threshold, nms_threshold)

# --- Normalize indices to flat list ---
filtered_boxes = []
if len(indices) > 0:
    if isinstance(indices[0], (list, tuple, np.ndarray)):
        indices = [i[0] for i in indices]
    else:
        indices = list(indices)
    filtered_boxes = [bounding_boxes[i] for i in indices]

# --- Save after NMS ---
with open("bounding_boxes_after_nms.json", "w") as f:
    json.dump(filtered_boxes, f, indent=2)

# --- Print stats ---
print(f"Số lượng box ban đầu     : {len(bounding_boxes)}")
print(f"Số lượng box sau khi NMS : {len(filtered_boxes)}")
print(f"Đã loại bỏ                : {len(bounding_boxes) - len(filtered_boxes)} box trùng (IoU > {nms_threshold})")

# --- Annotate ảnh trước NMS ---
annotated_before = det_res[0].plot(pil=False, line_width=5, font_size=20)
cv2.imwrite("result_before_nms.jpg", annotated_before)

# --- Annotate ảnh sau NMS bằng PIL ---
if isinstance(annotated_before, np.ndarray):
    img_pil = Image.fromarray(cv2.cvtColor(annotated_before, cv2.COLOR_BGR2RGB))
else:
    img_pil = annotated_before.copy()

draw = ImageDraw.Draw(img_pil)
for box in filtered_boxes:
    x1, y1, x2, y2 = box["bbox"]
    draw.rectangle([x1, y1, x2, y2], outline="red", width=4)

img_pil.save("result_after_nms.jpg")
