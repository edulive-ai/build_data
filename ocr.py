import easyocr
reader = easyocr.Reader(['vi', 'en'])  # Hỗ trợ tiếng Việt và Anh
result = reader.readtext("/home/batien/Desktop/build_data/output/cropped/image_0001/crop_001_cls1.png")
for detection in result:
    print(detection[1])