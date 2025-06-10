import cv2
from doclayout_yolo import YOLOv10
from huggingface_hub import hf_hub_download
from vietocr.tool.predictor import Predictor
from vietocr.tool.config import Cfg
from PIL import Image
import json

# --- Load YOLO model ---
filepath = hf_hub_download(repo_id="juliozhao/DocLayout-YOLO-DocStructBench", filename="doclayout_yolo_docstructbench_imgsz1024.pt")
model = YOLOv10(filepath)

# --- Load VietOCR config ---
img_path = '/home/batien/Desktop/build_data/figures/figure_8_class_0.jpg'
img = Image.open(img_path).convert('RGB')

config = Cfg.load_config_from_name('vgg_seq2seq')
config['weights'] = 'https://vocr.vn/data/vietocr/vgg_seq2seq.pth'
config['device'] = 'cpu'
detector = Predictor(config)

# --- Perform YOLO prediction (get bounding boxes) ---
det_res = model.predict(
    img_path,    # Image to predict
    imgsz=1024,  # Prediction image size
    conf=0.2,    # Confidence threshold
    device="cuda" # Device to use (e.g., 'cuda:0' or 'cpu')
)

# --- Extract bounding boxes from YOLO results ---
bounding_boxes = []
for result in det_res[0].boxes:
    x1, y1, x2, y2 = result.xyxy[0].tolist()  # Coordinates of bounding box
    class_id = result.cls[0].item()  # Class of the detected object (e.g., 'text', 'title')
    confidence = result.conf[0].item()  # Confidence of the prediction

    # --- Crop the image using YOLO bounding box ---
    cropped_img = img.crop((x1, y1, x2, y2))

    # --- Perform OCR on the cropped image ---
    text = detector.predict(cropped_img)

    # Append result to bounding boxes list
    bounding_boxes.append({
        "class_id": class_id,
        "confidence": confidence,
        "bbox": [x1, y1, x2, y2],
        "text": text
    })
    print(f"Class ID: {class_id}, Confidence: {confidence}, Bounding Box: [{x1}, {y1}, {x2}, {y2}], Text: {text}")

# --- Save bounding boxes and OCR text to JSON file ---
with open("bounding_boxes_and_text.json", "w") as json_file:
    json.dump(bounding_boxes, json_file, ensure_ascii=False, indent=2)

# --- Annotate and save the result ---
annotated_frame = det_res[0].plot(pil=True, line_width=5, font_size=20)
cv2.imwrite("result_with_text.jpg", annotated_frame)
