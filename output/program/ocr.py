# import easyocr
# reader = easyocr.Reader(['vi', 'en'])  # Hỗ trợ tiếng Việt và Anh
# result = reader.readtext("/home/batien/Desktop/build_data/output/cropped/image_0001/crop_001_cls1.png")
# for detection in result:
#     print(detection[1])

# from paddleocr import PaddleOCR
# ocr = PaddleOCR(use_angle_cls=True, lang='vi')
# img_path = ''
# result = ocr.ocr(img_path, cls=True)
# text = ' '.join([line[1][0] for line in result[0]])
# print(text)

from vietocr.tool.predictor import Predictor
from vietocr.tool.config import Cfg
from PIL import Image
config = Cfg.load_config_from_name('vgg_transformer')
config['device'] = 'cpu'  # Hoặc 'cuda' nếu có GPU
detector = Predictor(config)
img = Image.open('/home/batien/Desktop/build_data/output/cropped_hdhtoan1_q4/image_0025/crop_000_cls1.png')
text = detector.predict(img)
print('Text:', text)