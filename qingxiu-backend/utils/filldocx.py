# coding=utf-8
from io import BytesIO
from docxtpl import DocxTemplate


class FillDocx:
    """
    填充 docx
    """

    def handler(self, file_bytes, data):
        """
        :param file_bytes: docx 文件的二进制 bytes 数据
        :param data: 要填充的数据 dict
        return: 填充后的 docx 的 bytes 数据
        """
        tpl = DocxTemplate(file_bytes)  # 调用填充实体类
        tpl.render(data)
        f = BytesIO()
        tpl.save(f)
        return f


if __name__ == "__main__":
    file_bytes = '/Users/tuanzi/Downloads/1.docx'
    with open(file_bytes, 'rb') as p:
        file_bytes = p.read()
        f = BytesIO()
        f.write(file_bytes)
        data = {
            "subjectId": 1
        }
        FillDocx().handler(file_bytes=f, data=data)
    doc = DocxTemplate("/Users/tuanzi/Downloads/1.docx")

    # doc = DocxTemplate("/Users/tuanzi/Downloads/1.docx")
    # context = {'subjectId': "3"}
    # doc.render(context)
    # doc.save("generated_doc.docx")
