import datetime

from dateutil.relativedelta import relativedelta
from django.shortcuts import render
# Create your views here.
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from blacklist.models import UnitBlacklist, ProjectLeader, ExpertsBlacklist, AgenciesBlacklist
from blacklist.serializers import UnitBlacklistSerializers, ProjectLeaderSerializers, ExpertsBlacklistSerializers, \
    AgenciesBlacklistSerializers
from contract.models import Contract
from subject.models import Subject, SubjectPersonnelInfo
from users.models import User


class UnitBlacklistViewSet(viewsets.ModelViewSet):
    queryset = UnitBlacklist.objects.all()
    serializer_class = UnitBlacklistSerializers

    def create(self, request, *args, **kwargs):
        self.queryset.filter(creditCode=request.data['creditCode'], isArchives=False).update(isArchives=True)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                        headers=headers)

    def list(self, request, *args, **kwargs):
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.order_by('-disciplinaryTime').filter(isArchives=False)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "请求成功", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "请求成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='details')
    def details(self, request):
        credit_code = request.query_params.dict().get('creditCode')
        queryset = self.queryset.filter(creditCode=credit_code)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='query')
    def query(self, request):
        json_data = request.data
        keys = {
            "unitName": "unitName__contains",
            "creditCode": "creditCode__contains",
            "degreeOf": "degreeOf"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = self.queryset.order_by('-disciplinaryTime').filter(**data, isArchives=False)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 失信单位根据信用代码精确查询（管理员系统）
    @action(detail=False, methods=['post'], url_path='username_query')
    def username_query(self, request):
        new_time = datetime.date.today()
        if self.queryset.filter(creditCode=request.data['creditCode'], disciplinaryTime__gte=new_time).exists():
            queryset = self.queryset.filter(disciplinaryTime__gte=new_time, creditCode=request.data['creditCode'])
            serializer = self.get_serializer(queryset, many=True)
            return Response({"code": 1, "message": "此单位已在黑名单", "detail": serializer.data}, status=status.HTTP_200_OK)
        else:
            try:
                queryset = User.objects.filter(username=request.data['creditCode'].values('name', 'username', 'contact', 'mobile'))
                return Response({"code": 0, "message": "ok", "detail": queryset}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"code": 2, "message": "不存在"}, status=status.HTTP_200_OK)

    # 课题名称模糊查询
    @action(detail=False, methods=['post'], url_path='subject_name_query')
    def subject_name_query(self, request):
        subject_name = request.data['subjectName']
        if subject_name:
            if not Subject.objects.filter(subjectName__contains=subject_name).exists():
                return Response({"code": 1, "message": "不存在"}, status=status.HTTP_200_OK)
            else:
                subject = Subject.objects.filter(subjectName__contains=subject_name).values('id',
                                                                                            'subjectName',
                                                                                            'declareTime',
                                                                                            'project__category__batch__annualPlan',
                                                                                            'contract_subject__contractNo'
                                                                                            )
                return Response({"code": 0, "message": "ok", "detail": subject}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 2, "message": "课题名称不能为空"}, status=status.HTTP_200_OK)


class ProjectLeaderViewSet(viewsets.ModelViewSet):
    queryset = ProjectLeader.objects.all()
    serializer_class = ProjectLeaderSerializers

    def create(self, request, *args, **kwargs):
        self.queryset.filter(idNumber=request.data['idNumber'], isArchives=False).update(isArchives=True)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                        headers=headers)

    def list(self, request, *args, **kwargs):
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.order_by('-disciplinaryTime').filter(isArchives=False)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='details')
    def details(self, request):
        id_number = request.query_params.dict().get('idNumber')
        queryset = self.queryset.filter(idNumber=id_number)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='query')
    def query(self, request):
        json_data = request.data
        keys = {
            "name": "name__contains",
            "idNumber": "idNumber__contains",
            "mobile": "mobile__contains",
            "degreeOf": "degreeOf"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = self.queryset.order_by('-disciplinaryTime').filter(**data, isArchives=False)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 失信项目负责人身份证号查询（管理员系统）
    @action(detail=False, methods=['post'], url_path='id_number_query')
    def id_number_query(self, request):
        new_time = datetime.date.today()
        if self.queryset.filter(idNumber=request.data['idNumber'], disciplinaryTime__gte=new_time).exists():
            queryset = self.queryset.filter(idNumber=request.data['idNumber'], disciplinaryTime__gte=new_time)
            serializer = self.get_serializer(queryset, many=True)
            return Response({"code": 1, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)
        else:
            instance = SubjectPersonnelInfo.objects.filter(idNumber=request.data['idNumber'])
            if instance:
                data = [{'name': i.name,
                         'idNumber': i.idNumber,
                         'mobile': Subject.objects.get(id=i.subjectId).mobile} for i in instance]
                return Response({"code": 0, "message": "ok", "detail": data}, status=status.HTTP_200_OK)
            else:
                return Response({"code": 3, "message": "不存在"})

    # 失信项目负责人身份证号查询（管理员系统）
    @action(detail=False, methods=['post'], url_path='automatic_create')
    def automatic_create(self, request):
        subject = Subject.objects.get(id=request.data['subjectId'])
        instance = SubjectPersonnelInfo.objects.get(subjectId=subject.id)
        project_leader = self.queryset.filter(idNumber=instance.idNumber, isArchives=False)
        if project_leader:
            queryset = self.queryset.get(idNumber=instance.idNumber, isArchives=False)
            disciplinary_time = queryset.disciplinaryTime
            self.queryset.filter(idNumber=instance.idNumber, isArchives=False).update(
                isArchives=True)
            ProjectLeader.objects.create(name=instance.name,
                                         unitName=instance.workUnit,
                                         idNumber=instance.idNumber,
                                         mobile=subject.mobile,
                                         degreeOf='一般失信',
                                         breachTime=datetime.date.today(),
                                         disciplinaryTime=disciplinary_time + relativedelta(years=1),
                                         returnReason='课题终止',
                                         subjectName=subject.subjectName,
                                         annualPlan=subject.project.category.batch.annualPlan,
                                         declareTime=subject.declareTime,
                                         contractNo=Contract.objects.get(subject=subject).contractNo
                                         )
        else:
            ProjectLeader.objects.create(name=instance.name,
                                         unitName=instance.workUnit,
                                         idNumber=instance.idNumber,
                                         mobile=subject.mobile,
                                         degreeOf='一般失信',
                                         breachTime=datetime.date.today(),
                                         disciplinaryTime=datetime.date.today() + relativedelta(years=2),
                                         returnReason='课题终止',
                                         subjectName=subject.subjectName,
                                         annualPlan=subject.project.category.batch.annualPlan,
                                         declareTime=subject.declareTime,
                                         contractNo=Contract.objects.get(subject=subject).contractNo
                                         )
        return Response({"code": 0, "message": "OK"}, status=status.HTTP_200_OK)


class ExpertsBlacklistViewSet(viewsets.ModelViewSet):
    queryset = ExpertsBlacklist.objects.all()
    serializer_class = ExpertsBlacklistSerializers

    def create(self, request, *args, **kwargs):
        self.queryset.filter(idNumber=request.data['idNumber'], isArchives=False).update(isArchives=True)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                        headers=headers)

    def list(self, request, *args, **kwargs):
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.order_by('-disciplinaryTime').filter(isArchives=False)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='details')
    def details(self, request):
        id_number = request.query_params.dict().get('idNumber')
        queryset = self.queryset.filter(idNumber=id_number)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='query')
    def query(self, request):
        json_data = request.data
        keys = {
            "name": "name__contains",
            "idNumber": "idNumber__contains",
            "mobile": "mobile__contains",
            "degreeOf": "degreeOf"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = self.queryset.order_by('-disciplinaryTime').filter(**data, isArchives=False)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 失信项目负责人身份证号查询（管理员系统）
    @action(detail=False, methods=['post'], url_path='id_number_query')
    def id_number_query(self, request):
        new_time = datetime.date.today()
        id_number = request.data['idNumber']
        if self.queryset.filter(idNumber=id_number, disciplinaryTime__gte=new_time).exists():
            queryset = self.queryset.filter(idNumber=id_number, disciplinaryTime__gte=new_time)
            serializer = self.get_serializer(queryset, many=True)
            return Response({"code": 1, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 2, "message": "不存在"})


class AgenciesBlacklistViewSet(viewsets.ModelViewSet):
    queryset = AgenciesBlacklist.objects.all()
    serializer_class = AgenciesBlacklistSerializers

    def create(self, request, *args, **kwargs):
        self.queryset.filter(creditCode=request.data['creditCode'], isArchives=False).update(isArchives=True)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                        headers=headers)

    def list(self, request, *args, **kwargs):
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.order_by('-disciplinaryTime').filter(isArchives=False)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='details')
    def details(self, request):
        credit_code = request.query_params.dict().get('creditCode')
        queryset = self.queryset.filter(creditCode=credit_code)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='query')
    def query(self, request):
        json_data = request.data
        keys = {
            "name": "name__contains",
            "creditCode": "creditCode__contains",
            "degreeOf": "degreeOf__contains"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = self.queryset.order_by('-disciplinaryTime').filter(**data, isArchives=False)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 失信机构信用代码查询（管理员系统）
    @action(detail=False, methods=['post'], url_path='username_query')
    def username_query(self, request):
        new_time = datetime.date.today()
        if self.queryset.filter(creditCode=request.data['creditCode']).exists():
            queryset = self.queryset.filter(creditCode=request.data['creditCode'], disciplinaryTime__gte=new_time)
            serializer = self.get_serializer(queryset, many=True)
            return Response({"code": 1, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)
        else:
            try:
                queryset = User.objects.filter(username=request.data['creditCode']).values('name', 'username', 'contact', 'mobile')
                return Response(
                    {"code": 0, "message": "ok", "detail": queryset}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"code": 2, "message": "不存在"}, status=status.HTTP_200_OK)
