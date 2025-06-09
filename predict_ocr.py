from vietocr.tool.predictor import Predictor
from vietocr.tool.config import Cfg
from PIL import Image
img_path = '/home/batien/Desktop/build_data/figures/figure_8_class_0.jpg'
img = Image.open(img_path).convert('RGB')

config = Cfg.load_config_from_name('vgg_seq2seq')
config['weights'] = 'https://vocr.vn/data/vietocr/vgg_seq2seq.pth'
config['device'] = 'cpu'

detector = Predictor(config)
text = detector.predict(img)
print(text)
