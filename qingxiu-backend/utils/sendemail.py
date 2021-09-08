import json
import smtplib
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
from multiprocessing import Process


class SendEmailProcess(Process):
    def __init__(self, email, title, content):
        super().__init__()
        self.email = email
        self.title = title
        self.content = content

    def run(self):
        self.send_email()

    def send_email(self):
        message = MIMEMultipart()
        content = MIMEText(self.content, 'html', 'utf-8')
        message.attach(content)
        # message['From'] = "{}".format('ahriknow@ahrimail.com')
        message['From'] = "{}".format('zhangqin@seimun.com')
        message['To'] = self.email
        message['Subject'] = self.title

        # 添加附件
        # file = MIMEApplication(open('1.txt', 'rb').read())
        # file.add_header('Content-Disposition', 'p_w_upload', filename='1.txt')
        # message.attach(file)
        KEY = os.getenv('KEY') if os.getenv('KEY') else 'YEUCBHQUVYHLKAZL'
        try:
            smtp_obj = smtplib.SMTP_SSL("smtp.yeah.net", 465)
            smtp_obj.login('ahriknow@yeah.net', KEY)
            smtp_obj.sendmail('ahriknow@yeah.net', self.email, message.as_string())
            print('ok', self.email)
        except smtplib.SMTPException as e:
            print(e)


if __name__ == "__main__":
    # print('rabbitmq starting...')
    # def callback(ch, method, properties, body):
    #     ch.basic_ack(delivery_tag=method.delivery_tag)
    #     data = json.loads(body.decode())
    #     SendEmailProcess(data['email'], data['title'], data['content']).start()
    #     print(data)

    # credentials = pika.PlainCredentials(MQ_USER, MQ_PASS)
    # connection = pika.BlockingConnection(pika.ConnectionParameters(host=MQ_HOST, port=int(MQ_PORT), virtual_host='/', credentials=credentials))
    # channel = connection.channel()
    # channel.queue_declare(queue='email', durable=False)
    # channel.basic_consume('email', callback)
    # channel.start_consuming()
    SendEmailProcess('libing@seimun.com', '测试', '<h1>1234</h1>').start()
