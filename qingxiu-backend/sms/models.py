from django.db import models

# Create your models here.


class Recipient(models.Model):
    recipient = models.CharField(verbose_name='接受人', max_length=10)

    class Meta:
        db_table = 'recipient'


class TextTemplate(models.Model):
    # Recipient = (("1", "项目负责人"), ("2", "专家"), ("3", "单位联系人"))
    name = models.CharField(max_length=50, verbose_name='事件名称')
    template = models.CharField(max_length=402, verbose_name='模版')
    recipient = models.ManyToManyField(to=Recipient, verbose_name='收件人', related_name='recipient_text', blank=True)
    enable = models.BooleanField(default=False, verbose_name="是否启用")

    class Meta:
        db_table = 'text_template'


class MessageRecord(models.Model):
    name = models.CharField(max_length=50, verbose_name='姓名')
    mobile = models.CharField(max_length=50, verbose_name='手机号')
    unitName = models.CharField(max_length=50, verbose_name='所在单位')
    sendTime = models.DateTimeField(verbose_name='发送时间')
    sendContent = models.CharField(max_length=402, verbose_name='短信内容')
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', null=True)

    class Meta:
        db_table = 'message_record'


class TemporaryTemplate(models.Model):
    name = models.CharField(max_length=120, verbose_name='模版名称')
    center = models.CharField(max_length=120, verbose_name='模版内容')
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'temporary_template'
