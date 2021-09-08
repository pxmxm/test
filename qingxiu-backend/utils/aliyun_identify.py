import base64
import json
import os
import urllib.request
import urllib.parse

import fitz

from backend.settings import MEDIA_ROOT
from users.utils import generate_numb_code

# pdf转图片
def pyMuPDF_file(pdfPath):
    f_name = generate_numb_code(3)
    urllib.request.urlretrieve(pdfPath, filename=MEDIA_ROOT + f_name + '.pdf')
    pdfDoc = fitz.open(MEDIA_ROOT + f_name + '.pdf')
    for pg in range(pdfDoc.pageCount):
        page = pdfDoc[pg]
        rotate = int(0)
        # 每个尺寸的缩放系数为2，这将为我们生成分辨率提高四倍的图像。
        # 此处若是不做设置，默认图片大小为：792X612, dpi=96
        zoom_x = 2.0  # 设置图片相对于PDF文件在X轴上的缩放比例
        zoom_y = 2.0  # 设置图片相对于PDF文件在Y轴上的缩放比例
        mat = fitz.Matrix(zoom_x, zoom_y).preRotate(rotate)
        pix = page.getPixmap(matrix=mat, alpha=False)
        png_name = f_name + '.png'
        png_path = os.path.join(MEDIA_ROOT, png_name)
        pix.writePNG(png_path)
        with open(MEDIA_ROOT + f_name + '.png', 'rb') as fp:
            # os.remove(png_path)
            os.remove(MEDIA_ROOT + f_name + '.pdf')
            return png_path


AppSecret = '7qlb17Qt2xbQKk2SbNXPzZalnkUYPf4Z'
AppCode = '6c76a19a1ef745c0afb16fc8a8fccf61'
AppKey = '203872579'

host = 'https://dm-58.data.aliyun.com'
path = '/rest/160601/ocr/ocr_business_license.json'
method = 'POST'
appcode = '6c76a19a1ef745c0afb16fc8a8fccf61'
querys = ''
bodys = {}
url = host + path
ENCODING = 'utf-8'


def get_img_base64(img_file):
    with open(img_file, 'rb') as infile:
        s = infile.read()
        return base64.b64encode(s).decode(ENCODING)


def predict(url, appcode, img_base64, ):
    param = {}
    param['image'] = img_base64
    body = json.dumps(param)
    data = bytes(body, "utf-8")
    headers = {'Authorization': 'APPCODE ' + appcode}
    request = urllib.request.Request(url=url, headers=headers, data=data)
    try:
        # response = urllib.request.urlopen(request, timeout=10)
        response = urllib.request.urlopen(request)
        return response.code, response.headers, response.read()
    except urllib.request.HTTPError as e:
        return e.code, e.headers, e.read()


def demo():
    appcode = '6c76a19a1ef745c0afb16fc8a8fccf61'
    url = 'http://dm-58.data.aliyun.com/rest/160601/ocr/ocr_business_license.json'
    img_base64 = pyMuPDF_file('http://39.107.75.182:19000/file/112633949924.pdf')
    # img_base64 = pyMuPDF_file('http://39.107.75.182:11000/file/130803686216.pdf')#竖版
    # img_base64 =pyMuPDF_file('http://39.107.75.182:19000/file/145110322289.pdf')#横版
    # img_base64 = '/Users/tuanzi/Desktop/ce.png'


    img_base64data = get_img_base64(img_base64)
    stat, header, content = predict(url, appcode, img_base64data, )
    if stat != 200:
        print('Http status code: ', stat)
        print('Error msg in header: ', header['x-ca-error-message'] if 'x-ca-error-message' in header else '')
        print('Error msg in body: ', content)
        exit()
    result_str = content
    print(result_str.decode(ENCODING))
    result = json.loads(result_str)
    print(result['address'], result['reg_num'], result['name'])


if __name__ == '__main__':
    demo()
