import re

from sms.models import TextTemplate
from subject.models import Subject, SubjectKExperts, SubjectExpertsOpinionSheet
from utils.letter import SMS


# Recipient = (("1", "项目负责人"), ("2", "专家"), ("3", "单位联系人"))


def send_template(name, subject_id):
    text_template = TextTemplate.objects.filter(enable=True, name=name,)
    if text_template.exists():
        sms_template = text_template.first()
        recipient = sms_template.recipient.values('recipient')
        content = sms_template.template
        for j in recipient:
            subject = Subject.objects.get(id=subject_id)
            if j['recipient'] == '项目负责人':
                content = content.replace("{课题名称}", subject.subjectName).replace("{单位名称}", subject.unitName).\
                    replace("{姓名}", subject.head)
                SMS().send_sms(subject.mobile, content.encode('gbk'))
            if j['recipient'] == '专家':
                expert = SubjectExpertsOpinionSheet.objects.filter(subject_id=subject_id).values('pExperts__expert__mobile', 'pExperts__expert__name')
                # expert = SubjectKExperts.objects.filter(subject_id=subject_id).values("expert__mobile")
                # content = sms_template.template.encode('gbk')
                for i in expert:
                    content = content.replace("{课题名称}", subject.subjectName).replace("{单位名称}", subject.unitName). \
                        replace("{姓名}", i['pExperts__expert__name'])
                    SMS().send_sms(i['pExperts__expert__mobile'], content.encode('gbk'))
            if j['recipient'] == '单位联系人':
                content = content.replace("{课题名称}", subject.subjectName).replace("{单位名称}", subject.unitName). \
                    replace("{姓名}", subject.enterprise.contact)
                SMS().send_sms(subject.enterprise.mobile, content.encode('gbk'))
