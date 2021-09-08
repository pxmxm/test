import os
import base64
from decimal import Decimal

import urllib.request
import fitz
from aip import AipOcr
from backend.settings import MEDIA_ROOT

from users.utils import generate_numb_code
from PIL import Image

# 扫码营业执照信息

""" 你的 APPID AK SK """
APP_ID = '21290164'
API_KEY = 'um1MoY7ul3uKulgdYd249roF'
SECRET_KEY = 'nINlTGqjRoABH6tAmQDvOzAnzbm28vG6'

client = AipOcr(APP_ID, API_KEY, SECRET_KEY)


# 图像数据，base64编码，要求base64编码后大小不超过4M，最短边至少15px，最长边最大4096px,支持jpg/png/bmp格式
# 读取图片
def get_file_content(filePath):
    with open(filePath, 'rb') as fp:
        return fp.read()  # 获取图片信息


def get_file_png(filePath):
    f_name = generate_numb_code(3)
    urllib.request.urlretrieve(filePath, filename=MEDIA_ROOT + f_name + '.png')
    im = Image.open(MEDIA_ROOT + f_name + '.png')
    print(im.size[0], im.size[1])
    with open(MEDIA_ROOT + f_name + '.png', 'rb') as fp:
        return fp.read()  # 获取图片信息


def get_base64_png(img_str):
    b64_data = img_str.split(';base64,')[1]
    img_data = base64.b64decode(b64_data)
    f_name = generate_numb_code(3)
    with open(MEDIA_ROOT + f_name + '.jpg', 'wb') as fp:
        fp.write(img_data)
    im = Image.open(MEDIA_ROOT + f_name + '.jpg')
    print(im.size[0], im.size[1])
    types = im.format
    if im.size[0] < im.size[1]:
        a = Decimal(format((3000 / im.size[1]), '.1f'))
        print(a)
        width = a*im.size[0]
        print(int(width))
        highly = a*im.size[1]
        print(int(highly))
        b = im.resize((width, highly), Image.ANTIALIAS)
        b.save(MEDIA_ROOT + f_name + '.jpg', types)
        print(b.size[0], b.size[1])
        with open(MEDIA_ROOT + f_name + '.jpg', 'rb') as fp:
            return fp.read()
    else:
        a = Decimal(format((3000 / im.size[0]), '.1f'))
        print(a)
        width = a * im.size[0]
        print(int(width))
        highly = a * im.size[1]
        print(int(highly))
        b = im.resize((width, highly), Image.ANTIALIAS)
        b.save(MEDIA_ROOT + f_name + '.jpg', types)
        print(b.size[0], b.size[1])
        with open(MEDIA_ROOT + f_name + '.jpg', 'rb') as fp:
            return fp.read()


""" 如果有可选参数 """
options = {}
options["language_type"] = "CHN_ENG"
options["detect_direction"] = "false"
options["detect_language"] = "true"
options["probability"] = "true"  # 配置相关参数


# pdf转图片
def pyMuPDF_fitz(pdfPath):
    f_name = generate_numb_code(3)
    # 将URL表示的网络对象复制到本地文件
    urllib.request.urlretrieve(pdfPath, filename=MEDIA_ROOT + f_name + '.pdf')
    #
    pdfDoc = fitz.open(MEDIA_ROOT + f_name + '.pdf')
    for pg in range(pdfDoc.pageCount):
        page = pdfDoc[pg]
        rotate = int(0)
        # 每个尺寸的缩放系数为2，这将为我们生成分辨率提高四倍的图像。
        # 此处若是不做设置，默认图片大小为：792X612, dpi=96
        pix = page.getPixmap(alpha=False)
        png_name = f_name + '.jpg'
        png_path = os.path.join(MEDIA_ROOT, png_name)
        pix.writePNG(png_path)
        im = Image.open(MEDIA_ROOT + f_name + '.jpg')
        print(im.size[0], im.size[1])
        if im.size[0] < im.size[1]:
            a = format((3400 / im.size[1]), '.1f')
            print(a)
            zoom_x = a  # 设置图片相对于PDF文件在X轴上的缩放比例
            zoom_y = a  # 设置图片相对于PDF文件在Y轴上的缩放比例
            mat = fitz.Matrix(zoom_x, zoom_y).preRotate(rotate)
            pix = page.getPixmap(matrix=mat, alpha=False)
            png_name = f_name + '.jpg'
            png_path = os.path.join(MEDIA_ROOT, png_name)
            pix.writePNG(png_path)
            with open(MEDIA_ROOT + f_name + '.jpg', 'rb') as fp:
                # os.remove(png_path)
                # os.remove(MEDIA_ROOT + f_name + '.jpg')
                return fp.read()
        else:
            a = format((3400 / im.size[0]), '.1f')
            print(a)
            zoom_x = a  # 设置图片相对于PDF文件在X轴上的缩放比例
            zoom_y = a  # 设置图片相对于PDF文件在Y轴上的缩放比例
            mat = fitz.Matrix(zoom_x, zoom_y).preRotate(rotate)
            pix = page.getPixmap(matrix=mat, alpha=False)
            png_name = f_name + '.jpg'
            png_path = os.path.join(MEDIA_ROOT, png_name)
            pix.writePNG(png_path)
            with open(MEDIA_ROOT + f_name + '.jpg', 'rb') as fp:
                # os.remove(png_path)
                # os.remove(MEDIA_ROOT + f_name + '.jpg')
                return fp.read()


'''
营业执照识别
'''
import requests
import base64


def demo():
    request_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/business_license"
    # 二进制方式打开图片文件
    img = base64.b64encode(pyMuPDF_fitz('http://39.107.75.182:19000/file/133753427442.pdf'))
    params = {"image": img}
    access_token = 'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id=um1MoY7ul3uKulgdYd249roF&client_secret=nINlTGqjRoABH6tAmQDvOzAnzbm28vG6'
    response = requests.get(access_token)
    a = response.json()['access_token']
    request_url = request_url + "?access_token=" + a
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    response = requests.post(request_url, data=params, headers=headers)
    if response:
        results = response.json()
        return results



if __name__ == "__main__":
    # print(pyMuPDF_fitz('http://39.107.75.182:11000/file/130803686216.pdf'))
    # business_license = client.businessLicense(pyMuPDF_fitz('/Users/tuanzi/Documents/ceshi.pdf'))
    business_license = client.businessLicense(pyMuPDF_fitz('http://39.107.75.182:19000/file/132332829825.pdf'))
    # business_license = client.businessLicense(get_file_png('http://39.107.75.182:19000/file/183657138602.png'))
    # business_license = client.businessLicense(get_base64_png('http://39.107.75.182:19000/file/132332829825.pdf'))

    print(business_license)
    print(type(business_license))
    # print(business_license['words_result']['社会信用代码']['words'])
    for k, v in business_license['words_result'].items():
        if k == '社会信用代码' or k == '单位名称' or k == '地址':
            print(v['words'])



    # image = get_file_content('/Users/tuanzi/Documents/images_0.png')
    # business_license = client.businessLicense(image)
    # print(business_license)

    # image = get_file_content('/Users/tuanzi/Desktop/y.jpeg')
    # """ 调用通用文字识别, 图片参数为本地图片 """
    # print(client.basicGeneral(image))
    #
    # for i in client.basicGeneral(image)['words_result']:
    #     print(i)

    # import re
    # str = '123412455612'
    # if not re.match(r'^[a-zA-Z][0-9]{12,24}$', str):
    #     print(2)
    # else:
    #     print(1)
    #
    # s=['2020123','2020124']
    # print(s[-1][-3:])
    #
    # annual_plan = '2001001'
    # print(annual_plan[0:2])

import datetime
import calendar
from dateutil.relativedelta import relativedelta

# start_stop_year = '2020.10-2020.12'
# declare_time_list = start_stop_year.split('-')
# print(declare_time_list)
# stop_time = declare_time_list[1].split('.')
# print(stop_time)
# x, y = calendar.monthrange(int(stop_time[0]), int(stop_time[1]))
# last_day = datetime.date(year=int(stop_time[0]), month=int(stop_time[1]), day=y)
# print(last_day - re
# lativedelta(months=3)+relativedelta(days=1))
# print(last_day)
#
#
# a=4
# if a>3:
#     print(1)


a='测试1还'
b ='测'
if b in a:
    print(1)