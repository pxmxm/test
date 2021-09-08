import re
import time
from ast import literal_eval
from datetime import datetime
from functools import reduce

from django.shortcuts import render

# Create your views here.
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from expert.models import Expert
from sms.models import TextTemplate, MessageRecord, Recipient, TemporaryTemplate
from sms.serializers import TextTemplateSerializers, MessageRecordSerializers, TemporaryTemplateSerializers
from subject.models import Subject
from users.models import User
from utils.letter import SMS


class SendSMSViewSet(viewsets.ModelViewSet):
    queryset = TextTemplate.objects.all()
    serializer_class = TextTemplateSerializers

    # 通信录
    @action(detail=False, methods=['get'], url_path='people_show')
    def people_show(self, request):
        values = []
        new_data = []
        unit = User.objects.filter(type='企业')
        expert = Expert.objects.filter(state=3)
        project_leader = Subject.objects.exclude(subjectState='待提交')
        list0 = [{"name": i.contact, "mobile": i.mobile, "unitName": i.name} for i in unit]
        list1 = [{"name": i.name, "mobile": i.mobile, "unitName": i.company} for i in expert]
        list2 = [{"name": i.head, "mobile": i.mobile, "unitName": i.unitName} for i in project_leader]
        list3 = list0+list1+list2
        # 列表中的字典元素去重people_show
        run_function = lambda x, y: x if y in x else x + [y]
        new_data = reduce(run_function, [[], ] + list3)
        for i in range(len(new_data)):
            new_data[i].update({'id': i})

        # for dic in list3:
        #     if dic["mobile"] not in values:
        #         values.append(dic["mobile"])
        #         new_data.append(dic)
        if request.query_params.dict().get('name'):
            new_data = [i for i in new_data if request.query_params.dict().get('name') in i["name"]]
        if request.query_params.dict().get('mobile'):
            new_data = [i for i in new_data if request.query_params.dict().get('mobile') in i["mobile"]]
        if request.query_params.dict().get('unitName'):
            new_data = [i for i in new_data if request.query_params.dict().get('unitName') in i["unitName"]]
        return Response({"code": 0, "message": "请求成功", "detail": new_data}, status=status.HTTP_200_OK)

    # 发送短信
    @action(detail=False, methods=['post'], url_path='send_sms')
    def send_sms(self, request):
        try:
            data = request.data['data']
            # data = literal_eval(data)
            content = request.data['content']
            new_data = datetime.now()
            print(new_data)
            for i in data:
                a = SMS().send_sms(i['mobile'], content.encode('gbk'))

                b = a.content.decode('gbk')
                print(b)
                if re.search('\d',b,flags=0).group() == "7":
                    return Response({'code': 7, 'message': '发送失败，短信内容中含有非法关键字'}, status.HTTP_200_OK)
                else:
                    MessageRecord.objects.create(name=i['name'], mobile=i['mobile'], unitName=i['unitName'], sendContent=content, sendTime=new_data)

            return Response({'code': 0, 'message': '发送成功',}, status.HTTP_200_OK)
        except Exception as e:
            return Response({e})

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset().order_by('id'))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        data = request.data['data']
        # data = literal_eval(data)
        for i in data:
            instance = self.queryset.filter(id=i['id'])
            instance.update(template=i['template'], enable=i['enable'])
            instance.first().recipient.clear()
            for j in i['recipient']:
                instance.first().recipient.add(Recipient.objects.get(id=j))
        return Response({"code": 0, "message": "保存成功"}, status=status.HTTP_200_OK)


class MessageRecordViewSet(viewsets.ModelViewSet):
    queryset = MessageRecord.objects.all()
    serializer_class = MessageRecordSerializers

    def lists(self, request, *args, **kwargs):
        json_data = request.query_params.dict()
        keys = {
            "name": "name__contains",
            "mobile": "mobile__contains",
            "unitName": "unitName__contains",
            "sendTime": "sendTime"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = self.filter_queryset(self.get_queryset().order_by('-sendTime').filter(**data))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        lists = []
        page = int(request.query_params.dict().get('page'))
        limit = int(request.query_params.dict().get('limit'))
        json_data = request.query_params.dict()
        keys = {
            "name": "name__contains",
            "mobile": "mobile__contains",
            "unitName": "unitName__contains",
            "sendTime": "sendTime"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = self.queryset.order_by('-sendTime').filter(**data)
        send_time = list(set(i['sendTime'] for i in queryset.values('sendTime'))).sort(reverse = True)
        send_time.sort(reverse=True)
        for i in send_time:
            dict1 = {"sendTime": timezone.localtime(i).strftime("%Y-%m-%d %H:%M:%S")}
            list2 = []
            for j in queryset:
                if i == j.sendTime:
                    list2.append({"name": j.name, "mobile": j.mobile, "unitName": j.unitName, "sendContent": j.sendContent})
            dict1['acceptPeople'] = list2
            lists.append(dict1)
        list1 = lists
        if page == 1:
            lists = lists[0:limit]
        else:
            lists = lists[page*limit-limit: page*limit]

        return Response({"code": 0, "message": "请求成功", "count": len(list1), "detail": lists}, status=status.HTTP_200_OK)




class TemporaryTemplateViewSet(viewsets.ModelViewSet):
    queryset = TemporaryTemplate.objects.all()
    serializer_class = TemporaryTemplateSerializers