import decimal
import json
import random
import time
import uuid

import requests
from django.http import StreamingHttpResponse, HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.settings import MEDIA_ROOT
from change.models import ProjectLeaderChange, ProjectDelayChange, TechnicalRouteChange
from concluding.models import Acceptance, Researchers, Output, CheckList, ExpenditureStatement, AcceptanceOpinion
from contract.models import Contract, ContractContent
from funding.models import AllocatedSingle
from report.models import ProgressReport
from research.models import FieldResearch
from subject.models import Subject, SubjectInfo, ExpectedResults, FundingBudget, IntellectualProperty, \
    SubjectPersonnelInfo, ExpertOpinionSheet, SubjectOtherInfo, UnitCommitment, SubjectUnitInfo, OpinionSheet
from termination.models import Termination, TResearchers, TOutput, TReport, TCheckList, TExpenditureStatement, \
    TerminationOpinion
from tpl.template import mapping11, mapping21, mapping31, mapping41, mapping51, mapping61, mapping71, mapping81, \
    mapping91, mapping101, mapping111, mapping121, mapping131
import subprocess
import os

from users.utils import generate_numb_code
from utils.filldocx import FillDocx
from utils.oss import OSS
from utils.pdf import doc2pdf_linux


def read_file(file_name, size):
    with open(file_name, mode='rb') as fp:
        while True:
            c = fp.read(size)
            if c:
                yield c
            else:
                break


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)


class DownloadView(APIView):
    def get(self, request, _id=None):
        # 获取参数
        t = request.query_params.get('type')
        v = request.query_params.get('version', '1')
        if t == '1':
            # 查询数据
            subject = Subject.objects.filter(pk=_id).first()
            if not subject:
                return Response({'code': 2, 'msg': '没有数据', 'data': None})
            subject_info = SubjectInfo.objects.filter(subjectId=_id)[0]
            expected_results = ExpectedResults.objects.filter(subjectId=_id)[0]
            funding_budget = FundingBudget.objects.filter(subjectId=_id)[0]
            intellectual_property = IntellectualProperty.objects.filter(subjectId=_id)[0]
            subject_personnel_info = SubjectPersonnelInfo.objects.filter(subjectId=_id)[0]
            subject_other_info = SubjectOtherInfo.objects.filter(subjectId=_id)[0]
            unit_commitment = UnitCommitment.objects.filter(subjectId=_id)[0]
            subject_unit_info = SubjectUnitInfo.objects.filter(subjectId=_id)[0]
            # 得到要填充的数据
            data = mapping11.get_data(subject, subject_info, subject.enterprise.enterprise, expected_results,
                                      funding_budget, intellectual_property, subject_personnel_info, subject_other_info,
                                      unit_commitment, subject_unit_info)
        elif t == '2':
            contract = Contract.objects.filter(pk=_id).first()
            if not contract:
                return Response({'code': 2, 'msg': '没有数据', 'data': None})
            content = ContractContent.objects.filter(id=contract.contractContent)[0]
            data = mapping21.get_data(contract, content)
        elif t == '3':
            termination = Termination.objects.filter(id=_id)[0]
            data = mapping31.get_data(termination,
                                      TResearchers.objects.filter(termination=_id)[0],
                                      TOutput.objects.filter(termination=_id)[0],
                                      TReport.objects.filter(termination=_id)[0],
                                      TCheckList.objects.filter(termination=_id)[0],
                                      TExpenditureStatement.objects.filter(termination=_id)[0],
                                      TerminationOpinion.objects.filter(termination=_id)[0]
                                      )
            # TerminationOpinion.objects.filter(termination=_id)[0]
            # )
        elif t == '4':
            allocated_single = AllocatedSingle.objects.filter(id=_id)
            if not allocated_single:
                return Response({'code': 2, 'msg': '没有数据', 'data': None})
            data = mapping41.get_data(allocated_single)
        elif t == '5':
            expert_opinion_sheet = ExpertOpinionSheet.objects.filter(pk=_id).first()
            if not expert_opinion_sheet:
                return Response({'code': 2, 'msg': '没有数据', 'data': None})
            data = mapping51.get_data(expert_opinion_sheet)
        elif t == '6':
            opinion_sheet = OpinionSheet.objects.filter(pk=_id).first()
            if not opinion_sheet:
                return Response({'code': 2, 'msg': '没有数据', 'data': None})
            data = mapping61.get_data(opinion_sheet)
        elif t == '7':
            change_subject = TechnicalRouteChange.objects.filter(pk=_id).first()
            if not change_subject:
                return Response({'code': 2, 'msg': '没有数据', 'data': None})
            data = mapping71.get_data(change_subject)
        elif t == '8':
            project_leader_change = ProjectLeaderChange.objects.filter(pk=_id).first()
            if not project_leader_change:
                return Response({'code': 2, 'msg': '没有数据', 'data': None})
            data = mapping81.get_data(project_leader_change)
        elif t == '9':
            project_delay_change = ProjectDelayChange.objects.filter(pk=_id).first()
            if not project_delay_change:
                return Response({'code': 2, 'msg': '没有数据', 'data': None})
            data = mapping91.get_data(project_delay_change)
        # elif t == '10':
        #     subject_members_change = SubjectMembersChange.objects.filter(pk=_id).first()
        #     if not subject_members_change:
        #         return Response({'code': 2, 'msg': '没有数据', 'data': None})
        #     data = mapping101.get_data(subject_members_change)
        elif t == '11':
            acceptance = Acceptance.objects.filter(id=_id)[0]
            if not acceptance:
                return Response({'code': 2, 'msg': '没有数据', 'data': None})
            researchers = Researchers.objects.filter(acceptance=_id)[0]
            output = Output.objects.filter(acceptance=_id)[0]
            check_list = CheckList.objects.filter(acceptance=_id)[0]
            expenditure_statement = ExpenditureStatement.objects.filter(acceptance=_id)[0]
            acceptance_opinion = AcceptanceOpinion.objects.filter(acceptance=_id)[0]
            data = mapping111.get_data(acceptance, researchers, output, check_list, expenditure_statement,acceptance_opinion
                                       )
        elif t == '12':
            progress_report = ProgressReport.objects.filter(id=_id).first()
            if not progress_report:
                return Response({'code': 2, 'msg': '没有数据', 'data': None})
            data = mapping121.get_data(progress_report)
        elif t == '13':
            field_research = FieldResearch.objects.filter(id=_id).first()
            if not field_research:
                return Response({'code': 2, 'msg': '没有数据', 'data': None})
            data = mapping131.get_data(field_research)
        else:
            return Response({'code': 1, 'msg': '没有模板', 'data': None})
        ls = [
            '青秀区科技计划项目申报书',
            '青秀区科技计划项目合同书',
            '青秀区科技计划项目终止材料',
            '青秀区科技计划项目拨款申请单',
            '青秀区科技计划项目专家评审意见',
            '青秀区科技计划项目专家组评审意见',
            '青秀区科学研究与技术开发计划技术路线变更申请表',
            '青秀区科学研究与技术开发计划项目负责人变更申请表',
            '青秀区科学研究与技术开发计划项目延期申请表',
            '青秀区科学研究与技术开发计划课题人员变更申请表',
            '青秀区科技计划项目验收材料',
            '青秀区科学研究与技术开发计划项目进度表',
            '青秀区科学研究与技术开发计划实地调研意见表',
        ]
        n = ls[int(t) - 1] + '.docx'
        nn = request.query_params.get('name', None)
        if nn:
            n = nn
        e = request.query_params.get('ext', 'docx')
        v = '1'
        file = FillDocx().handler(file_bytes='./tpl/template/{}.docx'.format(t + v), data=data)
        if e == 'docx':
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            name = 'attachment; filename={0}'.format(n)
            response['Content-Disposition'] = name.encode("utf-8")
            response["Access-Control-Expose-Headers"] = "Content-Disposition"
            response.write(file.getvalue())
            return response
        elif e == 'pdf':
            name_pdf = time.strftime("%Y%m%d%H_", time.localtime()) + ''.join(
                random.sample('zyxwvutsrqponmlkjihgfedcba', 10))
            file_bytes = file.getvalue()
            with open(MEDIA_ROOT + name_pdf + '.docx', 'wb') as fp:
                fp.write(file_bytes)
            pdf_path = doc2pdf_linux(MEDIA_ROOT + name_pdf + '.docx', MEDIA_ROOT)
            if pdf_path:
                response = StreamingHttpResponse(read_file(pdf_path + name_pdf + '.pdf', 512),
                                                 content_type='application/pdf')
                name = 'attachment; filename={0}'.format(n)
                response['Content-Disposition'] = name.encode("utf-8")
                response["Access-Control-Expose-Headers"] = "Content-Disposition"
                return response
            return Response({'code': 3, 'msg': 'PDF 转换失败。', 'data': None})
        else:
            return Response({'code': 3, 'msg': '扩展名 ext 错误，只能是 pdf 或 docx。', 'data': None})


# 申报书
def generate_declare_pdf(subject_id):
    # 获取参数
    # t = request.query_params.get('type')
    # v = request.query_params.get('version', '1')
    # 查询数据
    subject = Subject.objects.filter(pk=subject_id).first()
    file_name = str(uuid.uuid4())
    if not subject:
        return Response({'code': 2, 'msg': '没有数据', 'data': None})
    subject_info = SubjectInfo.objects.filter(subjectId=subject_id)[0]
    expected_results = ExpectedResults.objects.filter(subjectId=subject_id)[0]
    funding_budget = FundingBudget.objects.filter(subjectId=subject_id)[0]
    intellectual_property = IntellectualProperty.objects.filter(subjectId=subject_id)[0]
    subject_personnel_info = SubjectPersonnelInfo.objects.filter(subjectId=subject_id)[0]
    subject_other_info = SubjectOtherInfo.objects.filter(subjectId=subject_id)[0]
    unit_commitment = UnitCommitment.objects.filter(subjectId=subject_id)[0]
    subject_unit_info = SubjectUnitInfo.objects.filter(subjectId=subject_id)[0]
    # 得到要填充的数据
    data = mapping11.get_data(subject, subject_info, subject.enterprise.enterprise, expected_results,
                              funding_budget, intellectual_property, subject_personnel_info, subject_other_info,
                              unit_commitment, subject_unit_info)
    file = FillDocx().handler(file_bytes='./tpl/template/{}.docx'.format('11'), data=data)
    file_bytes = file.getvalue()
    with open(MEDIA_ROOT + file_name + '.docx', 'wb') as fp:
        fp.write(file_bytes)
    pdf_path = doc2pdf_linux(MEDIA_ROOT + file_name + '.docx', MEDIA_ROOT)
    if pdf_path:
        pdf_url = OSS().put_pdfPath(pdf_path + file_name + '.pdf')
        os.remove(MEDIA_ROOT + file_name + '.docx')
        os.remove(MEDIA_ROOT + file_name + '.pdf')
        return pdf_url


# 合同
def generate_contract_pdf(contract_id):
    contract = Contract.objects.filter(pk=contract_id).first()
    if not contract:
        return Response({'code': 2, 'msg': '没有数据', 'data': None})
    content = ContractContent.objects.filter(id=contract.contractContent)[0]
    data = mapping21.get_data(contract, content)
    file = FillDocx().handler(file_bytes='./tpl/template/{}.docx'.format('21'), data=data)
    file_bytes = file.getvalue()
    with open(MEDIA_ROOT + 'one.docx', 'wb') as fp:
        fp.write(file_bytes)
    pdf_path = doc2pdf_linux(MEDIA_ROOT + 'one.docx', MEDIA_ROOT)
    pdf_url = OSS().put_pdfPath(pdf_path + 'one.pdf')
    os.remove(MEDIA_ROOT + 'one.docx')
    os.remove(MEDIA_ROOT + 'one.pdf')
    return pdf_url


# 评估机构专家评审单
def generate_experts_review_single_pdf(expert_opinion_sheet_id):
    experts_review_single = ExpertOpinionSheet.objects.filter(pk=expert_opinion_sheet_id).first()
    if not experts_review_single:
        return Response({'code': 2, 'msg': '没有数据', 'data': None})
    data = mapping51.get_data(experts_review_single)
    file = FillDocx().handler(file_bytes='./tpl/template/{}.docx'.format('51'), data=data)
    file_bytes = file.getvalue()
    with open(MEDIA_ROOT + 'one.docx', 'wb') as fp:
        fp.write(file_bytes)
    pdf_path = doc2pdf_linux(MEDIA_ROOT + 'one.docx', MEDIA_ROOT)
    pdf_url = OSS().put_pdfPath(pdf_path + 'one.pdf')
    os.remove(MEDIA_ROOT + 'one.docx')
    os.remove(MEDIA_ROOT + 'one.pdf')
    return pdf_url


# 评估机构评审单
def generate_review_single_pdf(opinion_sheet_id):
    opinion_sheet = OpinionSheet.objects.filter(pk=opinion_sheet_id).first()
    if not opinion_sheet:
        return Response({'code': 2, 'msg': '没有数据', 'data': None})
    data = mapping61.get_data(opinion_sheet)
    file = FillDocx().handler(file_bytes='./tpl/template/{}.docx'.format('61'), data=data)
    file_bytes = file.getvalue()
    with open(MEDIA_ROOT + 'one.docx', 'wb') as fp:
        fp.write(file_bytes)
    pdf_path = doc2pdf_linux(MEDIA_ROOT + 'one.docx', MEDIA_ROOT)
    pdf_url = OSS().put_pdfPath(pdf_path + 'one.pdf')
    os.remove(MEDIA_ROOT + 'one.docx')
    os.remove(MEDIA_ROOT + 'one.pdf')
    return pdf_url


# 结题
def generate_concluding_pdf(acceptance_id):
    acceptance = Acceptance.objects.filter(id=acceptance_id)[0]
    if not acceptance:
        return Response({'code': 2, 'msg': '没有数据', 'data': None})
    researchers = Researchers.objects.filter(acceptance=acceptance_id)[0]
    output = Output.objects.filter(acceptance=acceptance_id)[0]
    check_list = CheckList.objects.filter(acceptance=acceptance_id)[0]
    expenditure_statement = ExpenditureStatement.objects.filter(acceptance=acceptance_id)[0]
    acceptance_opinion = AcceptanceOpinion.objects.filter(acceptance=acceptance_id)[0]

    data = mapping111.get_data(acceptance, researchers, output, check_list, expenditure_statement, acceptance_opinion)
    file = FillDocx().handler(file_bytes='./tpl/template/{}.docx'.format('111'), data=data)
    file_bytes = file.getvalue()
    with open(MEDIA_ROOT + 'one.docx', 'wb') as fp:
        fp.write(file_bytes)
    pdf_path = doc2pdf_linux(MEDIA_ROOT + 'one.docx', MEDIA_ROOT)
    pdf_url = OSS().put_pdfPath(pdf_path + 'one.pdf')
    os.remove(MEDIA_ROOT + 'one.docx')
    os.remove(MEDIA_ROOT + 'one.pdf')
    return pdf_url


# 终止
def generate_termination_pdf(termination_id):
    termination = Termination.objects.filter(id=termination_id)[0]
    data = mapping31.get_data(termination,
                              TResearchers.objects.filter(termination=termination_id)[0],
                              TOutput.objects.filter(termination=termination_id)[0],
                              TReport.objects.filter(termination=termination_id)[0],
                              TCheckList.objects.filter(termination=termination_id)[0],
                              TExpenditureStatement.objects.filter(termination=termination_id)[0],
                              TerminationOpinion.objects.filter(termination=termination_id)[0],
                              )
    # TerminationOpinion.objects.filter(termination=termination_id)[0]
    # )
    file = FillDocx().handler(file_bytes='./tpl/template/{}.docx'.format('31'), data=data)
    file_bytes = file.getvalue()
    with open(MEDIA_ROOT + 'one.docx', 'wb') as fp:
        fp.write(file_bytes)
    pdf_path = doc2pdf_linux(MEDIA_ROOT + 'one.docx', MEDIA_ROOT)
    pdf_url = OSS().put_pdfPath(pdf_path + 'one.pdf')
    os.remove(MEDIA_ROOT + 'one.docx')
    os.remove(MEDIA_ROOT + 'one.pdf')
    return pdf_url


# 实时进度
def generate_progress_report_pdf(progress_report_id):
    progress_report = ProgressReport.objects.filter(id=progress_report_id).first()
    if not progress_report:
        return Response({'code': 2, 'msg': '没有数据', 'data': None})
    data = mapping121.get_data(progress_report)
    file = FillDocx().handler(file_bytes='./tpl/template/{}.docx'.format('121'), data=data)
    file_bytes = file.getvalue()
    with open(MEDIA_ROOT + 'one.docx', 'wb') as fp:
        fp.write(file_bytes)
    pdf_path = doc2pdf_linux(MEDIA_ROOT + 'one.docx', MEDIA_ROOT)
    pdf_url = OSS().put_pdfPath(pdf_path + 'one.pdf')
    os.remove(MEDIA_ROOT + 'one.docx')
    os.remove(MEDIA_ROOT + 'one.pdf')
    return pdf_url


# 实时进度
def generate_field_research_pdf(field_research_id):
    f_name = generate_numb_code(3)
    field_research = FieldResearch.objects.filter(id=field_research_id).first()
    if not field_research:
        return Response({'code': 2, 'msg': '没有数据', 'data': None})
    data = mapping131.get_data(field_research)
    file = FillDocx().handler(file_bytes='./tpl/template/{}.docx'.format('131'), data=data)
    file_bytes = file.getvalue()
    with open(MEDIA_ROOT + f_name + '.docx', 'wb') as fp:
        fp.write(file_bytes)
    pdf_path = doc2pdf_linux(MEDIA_ROOT + f_name + '.docx', MEDIA_ROOT)
    pdf_url = OSS().put_pdfPath(pdf_path + f_name + '.pdf')
    os.remove(MEDIA_ROOT + f_name + '.docx')
    os.remove(MEDIA_ROOT + f_name + '.pdf')
    return pdf_url


# 项目负责人变更
def generate_project_leader_change_pdf(project_leader_change_id):
    project_leader_change = ProjectLeaderChange.objects.filter(pk=project_leader_change_id).first()
    if not project_leader_change:
        return Response({'code': 2, 'msg': '没有数据', 'data': None})
    data = mapping81.get_data(project_leader_change)
    file = FillDocx().handler(file_bytes='./tpl/template/{}.docx'.format('81'), data=data)
    file_bytes = file.getvalue()
    with open(MEDIA_ROOT + 'one.docx', 'wb') as fp:
        fp.write(file_bytes)
    pdf_path = doc2pdf_linux(MEDIA_ROOT + 'one.docx', MEDIA_ROOT)
    pdf_url = OSS().put_pdfPath(pdf_path + 'one.pdf')
    os.remove(MEDIA_ROOT + 'one.docx')
    os.remove(MEDIA_ROOT + 'one.pdf')
    return pdf_url


# 重大技术路线变更
def generate_technical_route_change_pdf(technical_route_change_id):
    technical_route_change = TechnicalRouteChange.objects.filter(pk=technical_route_change_id).first()
    if not technical_route_change:
        return Response({'code': 2, 'msg': '没有数据', 'data': None})
    data = mapping71.get_data(technical_route_change)
    file = FillDocx().handler(file_bytes='./tpl/template/{}.docx'.format('71'), data=data)
    file_bytes = file.getvalue()
    with open(MEDIA_ROOT + 'one.docx', 'wb') as fp:
        fp.write(file_bytes)
    pdf_path = doc2pdf_linux(MEDIA_ROOT + 'one.docx', MEDIA_ROOT)
    pdf_url = OSS().put_pdfPath(pdf_path + 'one.pdf')
    os.remove(MEDIA_ROOT + 'one.docx')
    os.remove(MEDIA_ROOT + 'one.pdf')
    return pdf_url


# 项目延期申请
def generate_project_delay_change_pdf(project_delay_change_id):
    project_delay_change = ProjectDelayChange.objects.filter(pk=project_delay_change_id).first()
    if not project_delay_change:
        return Response({'code': 2, 'msg': '没有数据', 'data': None})
    data = mapping91.get_data(project_delay_change)
    file = FillDocx().handler(file_bytes='./tpl/template/{}.docx'.format('91'), data=data)
    file_bytes = file.getvalue()
    with open(MEDIA_ROOT + 'one.docx', 'wb') as fp:
        fp.write(file_bytes)
    pdf_path = doc2pdf_linux(MEDIA_ROOT + 'one.docx', MEDIA_ROOT)
    pdf_url = OSS().put_pdfPath(pdf_path + 'one.pdf')
    os.remove(MEDIA_ROOT + 'one.docx')
    os.remove(MEDIA_ROOT + 'one.pdf')
    return pdf_url
