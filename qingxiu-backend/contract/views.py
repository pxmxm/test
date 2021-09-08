import re
from decimal import Decimal

from django.shortcuts import render

# Create your views here.

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework_mongoengine import viewsets as mongodb_viewsets

from contract.models import Contract, ContractContent, ContractAttachment
from contract.serializers import ContractSerializers, ContractContentSerializers, ContractAttachmentSerializers

# 项目下达
from funding.models import GrantSubject
from subject.models import Subject, SubjectUnitInfo, SubjectPersonnelInfo, SubjectInfo
from tpl.views_download import generate_contract_pdf

from utils.oss import OSS


class ContractViewSet(viewsets.ModelViewSet):
    queryset = Contract.objects.all()
    serializer_class = ContractSerializers

    # 生成合同编号
    @action(detail=False, methods=['post'], url_path='generate_contract_no')
    def generate_approval_money(self, request):
        instance = Subject.objects.get(id=request.data['subjectId'])
        annual_plan = instance.project.category.batch.annualPlan
        lists = []
        contract_no = self.queryset.filter().values('contractNo')
        for i in contract_no:
            if annual_plan == i['contractNo'][0:4]:
                lists.append(i['contractNo'])
        lists = sorted(lists)
        if lists:
            strs = int(lists[-1][-3:])
            num = "%03d" % (strs + 1)
            number = annual_plan + num
            return Response({'code': 0, 'message': number}, status=status.HTTP_200_OK)
        else:
            number = annual_plan + '001'
            return Response({'code': 0, 'message': number}, status=status.HTTP_200_OK)

    # 上传合同附件
    @action(detail=False, methods=['post'], url_path='contract_attachment')
    def contract_attachment(self, request):
        contract_id = request.data['contractId']
        file = request.data['file']
        file_name = request.data['fileName']
        queryset = self.queryset.get(id=contract_id)
        queryset.attachment = OSS().put_by_backend(path=file_name, data=file.read())
        queryset.contractState = '审核中'
        queryset.subject.state = '待审核'
        queryset.subject.save()
        queryset.save()
        return Response({'code': 0, 'message': '上传成功'}, status=status.HTTP_200_OK)

    # 合同PDF附件展示
    @action(detail=False, methods=['get'], url_path='attachmentPDF_show')
    def attachmentPDF_show(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        try:
            queryset = Contract.objects.get(subject_id=subject_id)
            if queryset.attachment:
                return Response({'code': 0, "message": "请求成功", "detail": queryset.attachment},
                                status=status.HTTP_200_OK)
            else:
                return Response({'code': 1, "message": "不存在附件"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'code': 2, "message": "课题不存在"}, status=status.HTTP_200_OK)

    # 合同档案展示
    @action(detail=False, methods=['get'], url_path='attachment_show')
    def attachment_show(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        try:
            queryset = Contract.objects.get(subject_id=subject_id)
            if queryset.attachment:
                return Response({'code': 0, "message": "请求成功", "detail": queryset.attachment},
                                status=status.HTTP_200_OK)
            else:
                return Response({'code': 1, "message": "不存在附件"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'code': 2, "message": "课题不存在"}, status=status.HTTP_200_OK)


class ContractContentViewSet(mongodb_viewsets.ModelViewSet):
    queryset = ContractContent.objects.all()
    serializer_class = ContractContentSerializers

    def create(self, request, *args, **kwargs):
        contract = Contract.objects.get(id=request.data['contractId'])
        if contract.contractContent:
            partial = kwargs.pop('partial', False)
            instance = self.queryset.get(id=contract.contractContent)
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            contract.contractContent = serializer.data['id']
            contract.state = '待提交'
            contract.save()
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)

    # 提交电子合同
    @action(detail=False, methods=['post'], url_path='submit')
    def submit(self, request, *args, **kwargs):
        contract = Contract.objects.get(id=request.data['contractId'])
        if contract.contractContent:
            partial = kwargs.pop('partial', False)
            instance = self.queryset.get(id=contract.contractContent)
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            queryset = self.queryset.get(id=serializer.data['id'])
            contract.state = '审核中'
            contract.subject.state = '待审核'
            contract.subject.returnReason = None
            if '-' in queryset.executionTime:
                contract.subject.executionTime = queryset.executionTime
                contract.subject.save()
            else:
                execution_time_list = queryset.executionTime.split('.')
                execution_time = execution_time_list[0] + '.' + execution_time_list[1] + '-' + execution_time_list[
                    2] + '.' + execution_time_list[3]
                contract.subject.executionTime = execution_time
                contract.subject.save()
            pdf_url = generate_contract_pdf(contract_id=contract.id)
            contract.attachment = pdf_url
            contract.save()
            return Response({"code": 0, "message": "电子合同提交成功"}, status=status.HTTP_200_OK)
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            queryset = self.queryset.get(id=serializer.data['id'])
            contract.contractContent = serializer.data['id']
            contract.state = '审核中'
            contract.subject.state = '待审核'
            contract.subject.executionTime = queryset.executionTime
            contract.subject.save()
            contract.save()
            pdf_url = generate_contract_pdf(contract_id=contract.id)
            contract.attachment = pdf_url
            contract.save()
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)

    # 电子合同展示
    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):

        subject_id = request.query_params.dict().get('subjectId')
        try:
            queryset = Contract.objects.get(subject_id=subject_id)
            contract_content = self.queryset.get(id=queryset.contractContent)
            serializer = self.get_serializer(contract_content)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({})

    # 填写合同初始数据
    @action(detail=False, methods=['get'], url_path='initial')
    def initial_data(self, request):
        subject_id = request.query_params.dict().get("subjectId")
        subject = Subject.objects.get(id=subject_id)
        unit = SubjectUnitInfo.objects.get(subjectId=subject_id)
        subject_personnel_info = SubjectPersonnelInfo.objects.get(subjectId=subject_id)
        contract = Contract.objects.get(subject_id=subject_id)
        subject_info = SubjectInfo.objects.get(subjectId=subject_id)
        unitFunding = []
        data = {
            "subjectName": subject.subjectName,
            "executionTime": subject.startStopYear,
            "unitName": [unit.unitInfo[0]['unitName'], unit.unitInfo[0]['industry'],
                         unit.unitInfo[0]['fundsAccounted']],
            "subjectTotalGoal": subject_info.overallGoal,  # 课题总体目标
            "subjectAssessmentIndicators": subject_info.assessmentIndicators,  # 课题考核指标
            "scienceFunding": contract.approvalMoney,
            "jointUnitName": [[i['unitName'], i['industry'], i['fundsAccounted']] for i in unit.jointUnitInfo],
            "subjectPersonnelInfo": {
                "head": {"name": subject_personnel_info.name, "idNumber": subject_personnel_info.idNumber,
                         "recordSchooling": subject_personnel_info.recordSchooling,
                         "workUnit": subject_personnel_info.workUnit,
                         "divisionSubject": subject_personnel_info.divisionSubject,
                         "gender": subject_personnel_info.gender,
                         "age": subject_personnel_info.age, "title": subject_personnel_info.title,
                         "professional": subject_personnel_info.professional},
                "researchDevelopmentPersonnel": subject_personnel_info.researchDevelopmentPersonnel},
            "firstParty": [
                {'name': contract.chargeUser.name, "phone": contract.chargeUser.phone, "QQ": contract.chargeUser.QQ,
                 "email": contract.chargeUser.email}],

            "secondParty": [{'unitName': unit.unitInfo[0]['unitName'],
                             'creditCode': unit.unitInfo[0]['creditCode'],
                             'accountName': unit.unitInfo[0]['accountName'],
                             'bank': unit.unitInfo[0]['bank'],
                             'bankAccount': unit.unitInfo[0]['bankAccount']}] + [{'unitName': i['unitName'],
                                                                                  'creditCode': i['creditCode'],
                                                                                  'accountName': i['accountName'],
                                                                                  'bank': i['bank'],
                                                                                  'bankAccount': i['bankAccount']} for i
                                                                                 in unit.jointUnitInfo],
            "secondPartyContact": [{'contact': unit.unitInfo[0]['contact'],
                                    'phone': unit.unitInfo[0]['phone'],
                                    'fax': unit.unitInfo[0]['fax'],
                                    'zipCode': unit.unitInfo[0]['zipCode'],
                                    'email': unit.unitInfo[0]['email'],
                                    'registeredAddress': unit.unitInfo[0]['registeredAddress'], }] + [
                                      {'contact': i['contact'],
                                       'phone': i['phone'],
                                       'fax': i['fax'],
                                       'zipCode': i['zipCode'],
                                       'email': i['email'],
                                       'registeredAddress': i['registeredAddress']} for i in unit.jointUnitInfo], }
        if len(unit.jointUnitInfo) == 0:
            if unit.unitInfo[0]['industry'] == '企业':
                unitFunding.append({"unitName": unit.unitInfo[0]['unitName'],
                                    "fundsAccounted": "100",
                                    "first": "%.2f" % (Decimal(contract.approvalMoney) / 100 * Decimal('0.6')),
                                    "last": "%.2f" % (Decimal(contract.approvalMoney) / 100 * Decimal('0.4'))})
            else:
                unitFunding.append({"unitName": unit.unitInfo[0]['unitName'],
                                    "fundsAccounted": "100",
                                    "first": "%.2f" % (Decimal(contract.approvalMoney) / 100),
                                    "last": '0.00'})
        else:
            if unit.unitInfo[0]['industry'] == "企业":
                unitFunding.append({"unitName": unit.unitInfo[0]['unitName'],
                                    "fundsAccounted": unit.unitInfo[0]['fundsAccounted'],
                                    "first": "%.2f" % (Decimal(contract.approvalMoney) / 100 * Decimal('0.6') * Decimal(
                                        unit.unitInfo[0]['fundsAccounted']) / 100),
                                    "last": "%.2f" % (Decimal(contract.approvalMoney) / 100 * Decimal('0.4') * Decimal(
                                        unit.unitInfo[0]['fundsAccounted']) / 100)})
            else:
                unitFunding.append({"unitName": unit.unitInfo[0]['unitName'],
                                    "fundsAccounted": unit.unitInfo[0]['fundsAccounted'],
                                    "first": "%.2f" % (Decimal(contract.approvalMoney) / 100 * Decimal(
                                        unit.unitInfo[0]['fundsAccounted']) / 100),
                                    "last": '0.00'})
            for j in unit.jointUnitInfo:
                if j['industry'] == "企业":
                    unitFunding.append({"unitName": j['unitName'],
                                        "fundsAccounted": j['fundsAccounted'],
                                        "first": "%.2f" % (
                                                Decimal(contract.approvalMoney) / 100 * Decimal('0.6') * Decimal(
                                            j['fundsAccounted']) / 100),
                                        "last": "%.2f" % (
                                                Decimal(contract.approvalMoney) / 100 * Decimal('0.4') * Decimal(
                                            j['fundsAccounted']) / 100)})
                else:
                    unitFunding.append({"unitName": j['unitName'],
                                        "fundsAccounted": j['fundsAccounted'],
                                        "first": "%.2f" % (Decimal(contract.approvalMoney) / 100 * Decimal(
                                            j['fundsAccounted']) / 100),
                                        "last": '0.00'})
        data['unitFunding'] = unitFunding
        return Response({"code": 0, "message": "上传成功", "detail": data}, status.HTTP_200_OK)

    # 合同档案展示
    @action(detail=False, methods=['get'], url_path='app_show')
    def app_show(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        try:
            lists = []
            queryset = Contract.objects.get(subject_id=subject_id)
            contract_content = self.queryset.get(id=queryset.contractContent)
            if queryset.attachment:
                lists.append({"attachment": queryset.attachment})
            else:
                serializer = self.get_serializer(contract_content)
                lists.append(serializer.data)
            if contract_content.jointAgreement:
                lists.append({"jointAgreement": contract_content.jointAgreement})
            return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({})

    # 计算金额
    @action(detail=False, methods=['post'], url_path='calculation')
    def calculation(self, request):
        unitFunding = []
        subject_id = request.data["subjectId"]
        funds_accounted = request.data["fundsAccounted"]
        unit_name = request.data["unitName"]
        contract = Contract.objects.get(subject_id=subject_id)
        unit = SubjectUnitInfo.objects.get(subjectId=subject_id)
        unit_obj = unit.unitInfo + unit.jointUnitInfo
        for i in unit_obj:
            if unit_name == i['unitName'] and i['industry'] == '企业':
                unitFunding.append({"unitName": unit.unitInfo[0]['unitName'],
                                    "fundsAccounted": funds_accounted,
                                    "first": "%.2f" % (Decimal(contract.approvalMoney) / 100 * Decimal('0.6') * Decimal(
                                        funds_accounted) / 100),
                                    "last": "%.2f" % (Decimal(contract.approvalMoney) / 100 * Decimal('0.4') * Decimal(
                                        funds_accounted) / 100)})
            else:
                if unit_name == i['unitName']:
                    unitFunding.append({"unitName": unit.unitInfo[0]['unitName'],
                                        "fundsAccounted": funds_accounted,
                                        "first": "%.2f" % (Decimal(contract.approvalMoney) / 100 * Decimal(
                                            funds_accounted) / 100),
                                        "last": '0.00'})
        return Response({"code": 0, "message": "请求成功", "detail": unitFunding}, status.HTTP_200_OK)


class ContractAttachmentViewSet(mongodb_viewsets.ModelViewSet):
    queryset = ContractAttachment.objects.all()
    serializer_class = ContractAttachmentSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 上传联合申报实施协议
    @action(detail=False, methods=['post'], url_path='update_joint_agreement')
    def update_joint_agreement(self, request):
        subject_id = request.data['subjectId']
        file = request.data['file']
        file_name = request.data['fileName']
        types = request.data['types']
        path = OSS().put_by_backend(path=file_name, data=file.read())
        try:
            queryset = Contract.objects.get(subject_id=subject_id)
            if self.queryset.filter(contract=queryset.id, types=types):
                attachment_path = self.queryset.get(contract=queryset.id, types=types)
                attachment_path.attachmentPath.append({"name": file_name, "path": path})
                attachment_path.save()
                return Response({"code": 0, "message": "上传成功"}, status=status.HTTP_200_OK)
            else:
                self.queryset.create(types=types, contract=queryset.id, attachmentShows=request.data['attachmentShows'],
                                     attachmentPath=[{"name": file_name, "path": path}])
                return Response({"code": 0, "message": "上传成功", "detail": path}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"code": 0, "message": "sa"}, status=status.HTTP_200_OK)

    # 展示
    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        try:
            queryset = Contract.objects.get(subject_id=subject_id)
            queryset = self.queryset.filter(contract=queryset.id)
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"code": 0, "message": "sa"}, status=status.HTTP_200_OK)

    # 删除附件
    @action(detail=False, methods=['delete'], url_path='delete_data')
    def delete_data(self, request):
        types = request.data['types']
        contract_id = request.data['contractId']
        attachment_path = request.data['attachmentPath']
        if attachment_path:
            queryset = self.queryset.get(contract=contract_id, types=types)
            for j in attachment_path:
                for i in queryset.attachmentPath:
                    if i['name'] == j['name'] and i['path'] == j['path']:
                        queryset.attachmentPath.remove(i)
                        queryset.save()
                        if len(queryset.attachmentPath) == 0:
                            queryset.delete()
                        file_name = j['path'].split("/")[-1]
                        OSS().delete(bucket_name='file', file_name=file_name)
            return Response({"code": 0, "message": "删除成功"}, status=status.HTTP_200_OK)
        return Response({"code": 0, "message": "蹦跶"}, status=status.HTTP_200_OK)
