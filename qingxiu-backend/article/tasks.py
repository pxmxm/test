import calendar
import datetime

from celery.schedules import crontab
from celery.task import periodic_task
from dateutil.relativedelta import relativedelta
from django.db.models import Q

from article.models import Article
from backend.celery import app

from project.models import Batch
from report.models import ProgressReport
from subject.models import Subject, Process

# 预约发送公告
from tpl.views_download import generate_declare_pdf
from utils.letter import SMS
from utils.sendemail import SendEmailProcess
from warehouse.models import DeclareProject


@periodic_task(run_every=crontab())
def article_task():
    queryset = Article.objects.filter(state='预约发布')
    time_list = {}
    for tm in queryset:
        time_list[tm.id] = tm.subscribe
    now_time = datetime.datetime.now()
    for k, v in time_list.items():
        if now_time < v:
            continue
        else:
            queryset = Article.objects.get(id=k)
            queryset.state = '已发布'
            queryset.save()
    return True


# 类别禁用
@periodic_task(run_every=crontab())
def category_disable_task():
    batch_dict = {}
    batch_obj = Batch.objects.filter(isActivation='启用')
    new_time = datetime.date.today()
    for i in batch_obj:
        declare_time_list = i.declareTime.split('-')
        stop_time = declare_time_list[1].split('.')
        last_day = datetime.date(year=int(stop_time[0]), month=int(stop_time[1]), day=int(stop_time[2]))
        batch_dict[i.id] = last_day
    for k, v in batch_dict.items():
        if v < new_time:
            batch = Batch.objects.get(id=k)
            batch.isActivation = '禁用'
            batch.save()
    return True


# 类别启用
@periodic_task(run_every=crontab())
def category_enable_task():
    batch_dict = {}
    batch_obj = Batch.objects.filter(isActivation='禁用')
    new_time = datetime.date.today()
    for i in batch_obj:
        declare_time_list = i.declareTime.split('-')
        start_time = declare_time_list[0].split('.')
        first_day = datetime.date(year=int(start_time[0]), month=int(start_time[1]), day=int(start_time[2]))
        stop_time = declare_time_list[1].split('.')
        last_day = datetime.date(year=int(stop_time[0]), month=int(stop_time[1]), day=int(stop_time[2]))
        batch_dict[i.id] = [first_day, last_day]
    for k, v in batch_dict.items():
        if v[0] <= new_time <= v[1]:
            batch = Batch.objects.get(id=k)
            batch.isActivation = '启用'
            batch.save()
    return True


# 创建进度报告
@periodic_task(run_every=crontab(minute='47', hour='16',  day_of_month='01', month_of_year='11'))
def progress_report_task():
    subject_obj = Subject.objects.filter(subjectState='项目执行')
    for subject in subject_obj:
        if subject.executionTime != '-':
            start_stop_year = subject.executionTime.split('-')
            start_time = start_stop_year[0].split('.')
            stop_time = start_stop_year[1].split('.')
            x, y = calendar.monthrange(int(stop_time[0]), int(stop_time[1]))
            first_day = datetime.date(year=int(start_time[0]), month=int(start_time[1]), day=1)
            last_day = datetime.date(year=int(stop_time[0]), month=int(stop_time[1]), day=y)
            new_time = datetime.date.today()
            if first_day < new_time < last_day:
                ProgressReport.objects.create(name=subject.subjectName,
                                              contractNo=subject.contract_subject.get().contractNo,
                                              unit=subject.unitName, head=subject.head,
                                              startStopYear=subject.executionTime,
                                              subject_id=subject.id)
                content = "您好，青秀区科技计划在研项目从今天开启填报实施进度报告，请于本月30日前完成填报".encode('gbk')
                SMS().send_sms(subject.mobile, content)
                # SMS().send_sms('15022704425', content)

    return True


# 关闭进度报告
@periodic_task(run_every=crontab(minute='32', hour='17', month_of_year='11', day_of_month='30'))
def shut_down_task():
    subject_obj = Subject.objects.filter(subjectState='项目执行')
    for subject in subject_obj:
        ProgressReport.objects.filter(subject=subject, state='待提交').update(state='未提交')
    return True


# 合同预警 celery
@periodic_task(run_every=crontab())
def warning_task():
    # queryset = Subject.objects.exclude(
    #     Q(subjectState='待提交') | Q(subjectState='验收通过') | Q(subjectState='验收不通过') | Q(subjectState='项目终止'))
    queryset = Subject.objects.exclude(executionTime='-').filter(subjectState='项目执行')
    time_list = {}
    new_time = datetime.date.today()
    for tm in queryset:
        print(tm.id)
        if tm.executionTime != '-':
            start_stop_year = tm.executionTime.split('-')
            stop_time = start_stop_year[1].split('.')
            x, y = calendar.monthrange(int(stop_time[0]), int(stop_time[1]))
            last_day = datetime.date(year=int(stop_time[0]), month=int(stop_time[1]), day=y)
            time_list[tm.id] = last_day
        for k, v in time_list.items():
            if v > new_time:
                if tm.id == k:
                    tm.warning = 1
                    tm.save()
            elif v - relativedelta(months=3) < new_time < v:
                if tm.id == k:
                    tm.warning = 2
                    tm.save()
                    content = "您好，您主持的青秀区科技计划在研项目”{code}“执行时间仅剩余3个月，请及时提交结题验收或延期申请。".format(
                        code=tm.subjectName).encode('gbk')
                    SMS().send_sms(tm.mobile, content)
                    # SMS().send_sms('15022704425', content)
            elif v - relativedelta(month=1) < new_time < v:
                if tm.id == k:
                    tm.warning = 3
                    tm.save()
            elif v < new_time < v + relativedelta(months=3):
                if tm.id == k:
                    tm.warning = 4
                    tm.save()
            elif v + relativedelta(months=3) < new_time:
                if tm.id == k:
                    tm.warning = 5
                    tm.save()
    return True


# 逾期未结题 overdue
@periodic_task(run_every=crontab())
def overdue_task():
    queryset = Subject.objects.filter(Q(subjectState='项目执行') | Q(subjectState='结题复核'))
    time_list = {}
    new_time = datetime.date.today()
    for tm in queryset:
        if tm.executionTime != '-':
            start_stop_year = tm.executionTime.split('-')
            stop_time = start_stop_year[1].split('.')
            x, y = calendar.monthrange(int(stop_time[0]), int(stop_time[1]))
            last_day = datetime.date(year=int(stop_time[0]), month=int(stop_time[1]), day=y)
            last_time = last_day + relativedelta(months=3)
            time_list[tm.id] = last_time
        for k, v in time_list.items():
            if v < new_time:
                tm.subjectState = '逾期未结题'
                tm.stateLabel = True
                tm.save()
                Process.objects.create(state='逾期未结题', subject=tm)
                return True
            else:
                continue


@app.task(name='pdf', retry_backoff=3, max_retries=10)
def pdf(subject_id):
    subject = Subject.objects.get(id=subject_id)
    pdf_url = generate_declare_pdf(subject_id=subject_id)
    subject.attachmentPDF = pdf_url
    subject.save()
    return True


@app.task(name='expert_register', retry_backoff=3, max_retries=10)
def expert_register(email, username, password):
        contents = '''
           <body>
               <div  style="width: 500px; height: 380px; box-shadow: 0px 0px 7px -3px #999999; margin: 100px auto;overflow: hidden;">
                   <div style="width: 90%; height: 90%; border-top: 1px solid #6969694a; margin: 30px auto;">
                       <div style="margin: 20px auto 40px auto; width: 100%; height: auto; font-size: 16px; font-weight: 500;">
                           <p>感谢您使用青秀区科技计划项目管理平台</p >
                           <p>您的电子邮箱:
                               <span>{}&nbsp;</span>
                           </p >
                       </div>
                       <div style=" width: 100%; height: 100px; background: #0064000d;overflow: hidden;">
                           <div style="width: 90%; height: auto; font-size: 14px; font-weight: 500; margin: 20px auto;">
                               <p>登录账号:
                                   <span>{}&nbsp;</span>
                               </p >登录密码:
                                    <span>{}&nbsp;</span>
                               <p></p >
                           </div>
                       </div>
                       <div style="margin-top: 20px; font-size: 14px; color: #999999;">
                           <p>(此邮件注册操作！)</p >
                           <p>此邮件由系统自动发出，请勿直接回复</p >
                       </div>
                   </div>
               </div>
           </body>
           '''.format(email, username, password)
        SendEmailProcess(email, '青秀区科技计划项目管理平台', contents).start()
        return True


@app.task(name='expert_editor', retry_backoff=3, max_retries=10)
def expert_editor(email, username, password):
        contents = '''
           <body>
               <div  style="width: 500px; height: 380px; box-shadow: 0px 0px 7px -3px #999999; margin: 100px auto;overflow: hidden;">
                   <div style="width: 90%; height: 90%; border-top: 1px solid #6969694a; margin: 30px auto;">
                       <div style="margin: 20px auto 40px auto; width: 100%; height: auto; font-size: 16px; font-weight: 500;">
                           <p>感谢您使用青秀区科技计划项目管理平台</p >
                           <p>您的电子邮箱:
                               <span>{}&nbsp;</span>
                           </p >
                       </div>
                       <div style=" width: 100%; height: 100px; background: #0064000d;overflow: hidden;">
                           <div style="width: 90%; height: auto; font-size: 14px; font-weight: 500; margin: 20px auto;">
                               <p>登录账号:
                                   <span>{}&nbsp;</span>
                               </p >登录密码:
                                    <span>{}&nbsp;</span>
                               <p></p >
                           </div>
                       </div>
                       <div style="margin-top: 20px; font-size: 14px; color: #999999;">
                           <p>(此邮件编辑操作！)</p >
                           <p>此邮件由系统自动发出，请勿直接回复</p >
                       </div>
                   </div>
               </div>
           </body>
           '''.format(email, username, password)
        SendEmailProcess(email, '青秀区科技计划项目管理平台', contents).start()
        return True

# @periodic_task(run_every=crontab())
def remind_email():
    subject = Subject.objects.exclude(executionTime='-').filter(subjectState='项目执行')
    new_time = datetime.date.today()
    for i in subject:
        start_stop_year = i.executionTime.split('-')
        stop_time = start_stop_year[1].split('.')
        x, y = calendar.monthrange(int(stop_time[0]), int(stop_time[1]))
        last_day = datetime.date(year=int(stop_time[0]), month=int(stop_time[1]), day=y)
        last_time = last_day - relativedelta(months=3) + relativedelta(days=1)
        if new_time == last_day:

            contents = '''
               <body>
                   <div  style="width: 500px; height: 380px; box-shadow: 0px 0px 7px -3px #999999; margin: 100px auto;overflow: hidden;">
                       <div style="width: 90%; height: 90%; border-top: 1px solid #6969694a; margin: 30px auto;">
                           <div style="margin: 20px auto 40px auto; width: 100%; height: auto; font-size: 16px; font-weight: 500;">
                               <p>感谢您使用青秀区科技计划项目管理平台</p >
                               <p>您的电子邮箱:
                                   <span>{}&nbsp</span>
                               </p >
                           </div>
                           <div style=" width: 100%; height: 100px; background: #0064000d;overflow: hidden;">
                               <div style="width: 90%; height: auto; font-size: 14px; font-weight: 500; margin: 20px auto;">
                                   <p> </p >
                               </div>
                           </div>
                           <div style="margin-top: 20px; font-size: 14px; color: #999999;">
                               <p>(此邮件编辑操作！)</p >
                               <p>此邮件由系统自动发出，请勿直接回复</p >
                           </div>
                       </div>
                   </div>
               </body>
               '''.format(i.email)
            SendEmailProcess(i.email, '青秀区科技计划项目管理平台', contents).start()
        else:
            continue
    return True


l = [(), ('a',), ('b',), ('c',), ('d',), ('a', 'b'), ('a', 'c'), ('a', 'd'), ('b', 'c'), ('b', 'd'), ('c', 'd'),
     ('a', 'b', 'c'), ('a', 'b', 'd'), ('a', 'c', 'd'), ('b', 'c', 'd')]


@app.task(name='add_declare', retry_backoff=3, max_retries=10)
def add_declare(annualPlan, projectBatch, planCategory, projectName):
    if DeclareProject.objects.filter(annualPlan=None, projectBatch=None, planCategory=None,
                                     projectName=None).exists():
        declare_project = DeclareProject.objects.get(annualPlan=None, projectBatch=None, planCategory=None,
                                                     projectName=None)
        declare_project.projectNumber = declare_project.projectNumber + 1
        declare_project.save()
    else:
        DeclareProject.objects.create(annualPlan=None, projectBatch=None, planCategory=None, projectName=None,
                                      projectNumber=1)
    if DeclareProject.objects.filter(annualPlan=annualPlan, projectBatch=None, planCategory=None,
                                     projectName=None).exists():
        declare_project1 = DeclareProject.objects.get(annualPlan=annualPlan, projectBatch=None, planCategory=None,
                                                      projectName=None)
        declare_project1.projectNumber = declare_project1.projectNumber + 1
        declare_project1.save()
    else:
        DeclareProject.objects.create(annualPlan=annualPlan, projectBatch=None, planCategory=None, projectName=None,
                                      projectNumber=1)
    if DeclareProject.objects.filter(annualPlan=None, projectBatch=projectBatch, planCategory=None,
                                     projectName=None).exists():
        declare_project2 = DeclareProject.objects.get(annualPlan=None, projectBatch=projectBatch, planCategory=None,
                                                      projectName=None)
        declare_project2.projectNumber = declare_project2.projectNumber + 1
        declare_project2.save()
    else:
        DeclareProject.objects.create(annualPlan=None, projectBatch=projectBatch, planCategory=None, projectName=None,
                                      projectNumber=1)
    if DeclareProject.objects.filter(annualPlan=None, projectBatch=None, planCategory=planCategory,
                                     projectName=None).exists():
        declare_project3 = DeclareProject.objects.get(annualPlan=None, projectBatch=None, planCategory=planCategory,
                                                      projectName=None)
        declare_project3.projectNumber = declare_project3.projectNumber + 1
        declare_project3.save()
    else:
        DeclareProject.objects.create(annualPlan=None, projectBatch=None, planCategory=planCategory, projectName=None,
                                      projectNumber=1)
    if DeclareProject.objects.filter(annualPlan=None, projectBatch=None, planCategory=None,
                                     projectName=projectName).exists():
        declare_project4 = DeclareProject.objects.get(annualPlan=None, projectBatch=None, planCategory=None,
                                                      projectName=projectName)
        declare_project4.projectNumber = declare_project4.projectNumber + 1
        declare_project4.save()
    else:
        DeclareProject.objects.create(annualPlan=None, projectBatch=None, planCategory=None, projectName=projectName,
                                      projectNumber=1)
    if DeclareProject.objects.filter(annualPlan=annualPlan, projectBatch=projectBatch, planCategory=None,
                                     projectName=None).exists():
        declare_project5 = DeclareProject.objects.get(annualPlan=annualPlan, projectBatch=projectBatch,
                                                      planCategory=None, projectName=None)
        declare_project5.projectNumber = declare_project5.projectNumber + 1
        declare_project5.save()
    else:
        DeclareProject.objects.create(annualPlan=annualPlan, projectBatch=projectBatch, planCategory=None,
                                      projectName=None, projectNumber=1)
    if DeclareProject.objects.filter(annualPlan=annualPlan, projectBatch=None, planCategory=planCategory,
                                     projectName=None).exists():
        declare_project6 = DeclareProject.objects.get(annualPlan=annualPlan, projectBatch=None,
                                                      planCategory=planCategory, projectName=None)
        declare_project6.projectNumber = declare_project6.projectNumber + 1
        declare_project6.save()
    else:
        DeclareProject.objects.create(annualPlan=annualPlan, projectBatch=None, planCategory=planCategory,
                                      projectName=None, projectNumber=1)
    if DeclareProject.objects.filter(annualPlan=annualPlan, projectBatch=None, planCategory=None,
                                     projectName=projectName).exists():
        declare_project7 = DeclareProject.objects.get(annualPlan=annualPlan, projectBatch=None, planCategory=None,
                                                      projectName=projectName)
        declare_project7.projectNumber = declare_project7.projectNumber + 1
        declare_project7.save()
    else:
        DeclareProject.objects.create(annualPlan=annualPlan, projectBatch=None, planCategory=None,
                                      projectName=projectName, projectNumber=1)
    if DeclareProject.objects.filter(annualPlan=None, projectBatch=projectBatch, planCategory=planCategory,
                                     projectName=None).exists():
        declare_project8 = DeclareProject.objects.get(annualPlan=None, projectBatch=projectBatch,
                                                      planCategory=planCategory,
                                                      projectName=None)
        declare_project8.projectNumber = declare_project8.projectNumber + 1
        declare_project8.save()
    else:
        DeclareProject.objects.create(annualPlan=None, projectBatch=projectBatch, planCategory=planCategory,
                                      projectName=None, projectNumber=1)

    if DeclareProject.objects.filter(annualPlan=None, projectBatch=projectBatch, planCategory=None,
                                     projectName=projectName).exists():
        declare_project9 = DeclareProject.objects.get(annualPlan=None, projectBatch=projectBatch, planCategory=None,
                                                      projectName=projectName)
        declare_project9.projectNumber = declare_project9.projectNumber + 1
        declare_project9.save()
    else:
        DeclareProject.objects.create(annualPlan=None, projectBatch=projectBatch, planCategory=None,
                                      projectName=projectName, projectNumber=1)
    if DeclareProject.objects.filter(annualPlan=None, projectBatch=None, planCategory=planCategory,
                                     projectName=projectName).exists():
        declare_project11 = DeclareProject.objects.get(annualPlan=None, projectBatch=None, planCategory=planCategory,
                                                       projectName=projectName)
        declare_project11.projectNumber = declare_project11.projectNumber + 1
        declare_project11.save()
    else:
        DeclareProject.objects.create(annualPlan=None, projectBatch=None, planCategory=planCategory,
                                      projectName=projectName, projectNumber=1)

    if DeclareProject.objects.filter(annualPlan=annualPlan, projectBatch=projectBatch, planCategory=planCategory,
                                     projectName=None).exists():
        declare_project12 = DeclareProject.objects.get(annualPlan=annualPlan, projectBatch=projectBatch,
                                                       planCategory=planCategory, projectName=None)
        declare_project12.projectNumber = declare_project12.projectNumber + 1
        declare_project12.save()
    else:
        DeclareProject.objects.create(annualPlan=annualPlan, projectBatch=projectBatch, planCategory=planCategory,
                                      projectName=None, projectNumber=1)

    if DeclareProject.objects.filter(annualPlan=annualPlan, projectBatch=projectBatch, planCategory=None,
                                     projectName=projectName).exists():
        declare_project13 = DeclareProject.objects.get(annualPlan=annualPlan, projectBatch=projectBatch,
                                                       planCategory=None, projectName=projectName)
        declare_project13.projectNumber = declare_project13.projectNumber + 1
        declare_project13.save()
    else:
        DeclareProject.objects.create(annualPlan=annualPlan, projectBatch=projectBatch, planCategory=None,
                                      projectName=projectName, projectNumber=1)

    if DeclareProject.objects.filter(annualPlan=annualPlan, projectBatch=None, planCategory=planCategory,
                                     projectName=projectName).exists():
        declare_project14 = DeclareProject.objects.get(annualPlan=annualPlan, projectBatch=None,
                                                       planCategory=planCategory, projectName=projectName)
        declare_project14.projectNumber = declare_project14.projectNumber + 1
        declare_project14.save()
    else:
        DeclareProject.objects.create(annualPlan=annualPlan, projectBatch=None, planCategory=planCategory,
                                      projectName=projectName, projectNumber=1)

    if DeclareProject.objects.filter(annualPlan=None, projectBatch=projectBatch, planCategory=planCategory,
                                     projectName=projectName).exists():
        declare_project15 = DeclareProject.objects.get(annualPlan=None, projectBatch=projectBatch,
                                                       planCategory=planCategory, projectName=projectName)
        declare_project15.projectNumber = declare_project15.projectNumber + 1
        declare_project15.save()
    else:
        DeclareProject.objects.create(annualPlan=None, projectBatch=projectBatch,
                                      planCategory=planCategory, projectName=projectName, projectNumber=1)

    if DeclareProject.objects.filter(annualPlan=annualPlan, projectBatch=projectBatch, planCategory=planCategory,
                                     projectName=projectName).exists():
        declare_project16 = DeclareProject.objects.get(annualPlan=annualPlan, projectBatch=projectBatch,
                                                       planCategory=planCategory, projectName=projectName)
        declare_project16.projectNumber = declare_project16.projectNumber + 1
        declare_project16.save()
    else:
        DeclareProject.objects.create(annualPlan=annualPlan, projectBatch=projectBatch,
                                      planCategory=planCategory, projectName=projectName, projectNumber=1)
    return True


@app.task(name='Reduction_declare', retry_backoff=3, max_retries=10)
def Reduction_declare(annualPlan, projectBatch, planCategory, projectName):
    if DeclareProject.objects.filter(annualPlan=None, projectBatch=None, planCategory=None,
                                     projectName=None).exists():
        declare_project = DeclareProject.objects.get(annualPlan=None, projectBatch=None, planCategory=None,
                                                     projectName=None)
        declare_project.projectNumber = declare_project.projectNumber - 1
        declare_project.save()
    else:
        pass
    if DeclareProject.objects.filter(annualPlan=annualPlan, projectBatch=None, planCategory=None,
                                     projectName=None).exists():
        declare_project1 = DeclareProject.objects.get(annualPlan=annualPlan, projectBatch=None, planCategory=None,
                                                      projectName=None)
        declare_project1.projectNumber = declare_project1.projectNumber - 1
        declare_project1.save()
    else:
        pass
    if DeclareProject.objects.filter(annualPlan=None, projectBatch=projectBatch, planCategory=None,
                                     projectName=None).exists():
        declare_project2 = DeclareProject.objects.get(annualPlan=None, projectBatch=projectBatch, planCategory=None,
                                                      projectName=None)
        declare_project2.projectNumber = declare_project2.projectNumber - 1
        declare_project2.save()
    else:
        pass
    if DeclareProject.objects.filter(annualPlan=None, projectBatch=None, planCategory=planCategory,
                                     projectName=None).exists():
        declare_project3 = DeclareProject.objects.get(annualPlan=None, projectBatch=None, planCategory=planCategory,
                                                      projectName=None)
        declare_project3.projectNumber = declare_project3.projectNumber - 1
        declare_project3.save()
    else:
        pass
    if DeclareProject.objects.filter(annualPlan=None, projectBatch=None, planCategory=None,
                                     projectName=projectName).exists():
        declare_project4 = DeclareProject.objects.get(annualPlan=None, projectBatch=None, planCategory=None,
                                                      projectName=projectName)
        declare_project4.projectNumber = declare_project4.projectNumber - 1
        declare_project4.save()
    else:
        pass
    if DeclareProject.objects.filter(annualPlan=annualPlan, projectBatch=projectBatch, planCategory=None,
                                     projectName=None).exists():
        declare_project5 = DeclareProject.objects.get(annualPlan=annualPlan, projectBatch=projectBatch,
                                                      planCategory=None, projectName=None)
        declare_project5.projectNumber = declare_project5.projectNumber - 1
        declare_project5.save()
    else:
        pass
    if DeclareProject.objects.filter(annualPlan=annualPlan, projectBatch=None, planCategory=planCategory,
                                     projectName=None).exists():
        declare_project6 = DeclareProject.objects.get(annualPlan=annualPlan, projectBatch=None,
                                                      planCategory=planCategory, projectName=None)
        declare_project6.projectNumber = declare_project6.projectNumber - 1
        declare_project6.save()
    else:
        pass
    if DeclareProject.objects.filter(annualPlan=annualPlan, projectBatch=None, planCategory=None,
                                     projectName=projectName).exists():
        declare_project7 = DeclareProject.objects.get(annualPlan=annualPlan, projectBatch=None, planCategory=None,
                                                      projectName=projectName)
        declare_project7.projectNumber = declare_project7.projectNumber - 1
        declare_project7.save()
    else:
        pass
    if DeclareProject.objects.filter(annualPlan=None, projectBatch=projectBatch, planCategory=planCategory,
                                     projectName=None).exists():
        declare_project8 = DeclareProject.objects.get(annualPlan=None, projectBatch=projectBatch,
                                                      planCategory=planCategory,
                                                      projectName=None)
        declare_project8.projectNumber = declare_project8.projectNumber - 1
        declare_project8.save()
    else:
        pass

    if DeclareProject.objects.filter(annualPlan=None, projectBatch=projectBatch, planCategory=None,
                                     projectName=projectName).exists():
        declare_project9 = DeclareProject.objects.get(annualPlan=None, projectBatch=projectBatch, planCategory=None,
                                                      projectName=projectName)
        declare_project9.projectNumber = declare_project9.projectNumber - 1
        declare_project9.save()
    else:
        pass
    if DeclareProject.objects.filter(annualPlan=None, projectBatch=None, planCategory=planCategory,
                                     projectName=projectName).exists():

        declare_project11 = DeclareProject.objects.get(annualPlan=None, projectBatch=None, planCategory=planCategory,
                                                       projectName=projectName)
        declare_project11.projectNumber = declare_project11.projectNumber - 1
        declare_project11.save()
    else:
        pass

    if DeclareProject.objects.filter(annualPlan=annualPlan, projectBatch=projectBatch, planCategory=planCategory,
                                     projectName=None).exists():
        declare_project12 = DeclareProject.objects.get(annualPlan=annualPlan, projectBatch=projectBatch,
                                                       planCategory=planCategory, projectName=None)
        declare_project12.projectNumber = declare_project12.projectNumber - 1
        declare_project12.save()
    else:
        pass

    if DeclareProject.objects.filter(annualPlan=annualPlan, projectBatch=projectBatch, planCategory=None,
                                     projectName=projectName).exists():
        declare_project13 = DeclareProject.objects.get(annualPlan=annualPlan, projectBatch=projectBatch,
                                                       planCategory=None, projectName=projectName)
        declare_project13.projectNumber = declare_project13.projectNumber - 1
        declare_project13.save()
    else:
        pass

    if DeclareProject.objects.filter(annualPlan=annualPlan, projectBatch=None, planCategory=planCategory,
                                     projectName=projectName).exists():
        declare_project14 = DeclareProject.objects.get(annualPlan=annualPlan, projectBatch=None,
                                                       planCategory=planCategory, projectName=projectName)
        declare_project14.projectNumber = declare_project14.projectNumber - 1
        declare_project14.save()
    else:
        pass

    if DeclareProject.objects.filter(annualPlan=None, projectBatch=projectBatch, planCategory=planCategory,
                                     projectName=projectName).exists():
        declare_project15 = DeclareProject.objects.get(annualPlan=None, projectBatch=projectBatch,
                                                       planCategory=planCategory, projectName=projectName)
        declare_project15.projectNumber = declare_project15.projectNumber - 1
        declare_project15.save()
    else:
        pass

    if DeclareProject.objects.filter(annualPlan=annualPlan, projectBatch=projectBatch, planCategory=planCategory,
                                     projectName=projectName).exists():
        declare_project16 = DeclareProject.objects.get(annualPlan=annualPlan, projectBatch=projectBatch,
                                                       planCategory=planCategory, projectName=projectName)
        declare_project16.projectNumber = declare_project16.projectNumber - 1
        declare_project16.save()
    else:
        pass
    return True
