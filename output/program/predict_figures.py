import cv2
from doclayout_yolo import YOLOv10
from huggingface_hub import hf_hub_download
import json

# Load the pre-trained model
filepath = hf_hub_download(repo_id="juliozhao/DocLayout-YOLO-DocStructBench", filename="doclayout_yolo_docstructbench_imgsz1024.pt")
# filepath = hf_hub_download(repo_id="juliozhao/DocLayout-YOLO-D4LA-from_scratch", filename="doclayout_yolo_d4la_imgsz1600_from_scratch.pt")
model = YOLOv10(filepath)

# Perform prediction
det_res = model.predict(
    "/home/batien/Desktop/build_data/ccst/ccst_page_031.png",   # Image to predict
    imgsz=1024,        # Prediction image size
    conf=0.2,          # Confidence threshold
    device="cuda"    # Device to use (e.g., 'cuda:0' or 'cpu')
)

# In ra các bounding box và thông tin
bounding_boxes = []
for result in det_res[0].boxes:
    x1, y1, x2, y2 = result.xyxy[0].tolist()  # Tọa độ bounding box
    class_id = result.cls[0].item()  # Lớp của bounding box
    confidence = result.conf[0].item()  # Độ tự tin của dự đoán
    bounding_boxes.append({
        "class_id": class_id,
        "confidence": confidence,
        "bbox": [x1, y1, x2, y2]
    })
    print(f"Class ID: {class_id}, Confidence: {confidence}, Bounding Box: [{x1}, {y1}, {x2}, {y2}]")

# Lưu kết quả bounding boxes vào file JSON
with open("bounding_boxes.json", "w") as json_file:
    json.dump(bounding_boxes, json_file, ensure_ascii=False, indent=2)

# Annotate and save the result
annotated_frame = det_res[0].plot(pil=True, line_width=5, font_size=20)
cv2.imwrite("result.jpg", annotated_frame)
