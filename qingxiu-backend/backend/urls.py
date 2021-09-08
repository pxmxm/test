"""backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include
from django.views.static import serve
from rest_framework.routers import DefaultRouter

from article.views import ArticleViewSet, ArticlesViewSet
from backend.settings import MEDIA_ROOT
from blacklist.views import UnitBlacklistViewSet, ProjectLeaderViewSet, ExpertsBlacklistViewSet, \
    AgenciesBlacklistViewSet
from change.views import ChangeSubjectViewSet, ProjectLeaderChangeViewSet, ProjectDelayChangeViewSet, \
    TechnicalRouteChangeViewSet
from concluding.views import AcceptanceViewSet, ResearchersViewSet, OutputViewSet, CheckListViewSet, \
    ExpenditureStatementViewSet, AcceptanceAttachmentViewSet, KOpinionSheetViewSet, \
    SubjectConcludingViewSet, AcceptanceOpinionViewSet
from contract.views import ContractViewSet, ContractContentViewSet, ContractAttachmentViewSet
from expert.views import ExpertsViewSet
from funding.views2 import GrantSubjectViewSet, AllocatedSingleViewSet
from project.views import BatchViewSet, ProjectViewSet
from report.views import ProgressReportViewSet
from research.views import FieldResearchViewSet, ProposalViewSet
from sms.views import SendSMSViewSet, MessageRecordViewSet, TemporaryTemplateViewSet
from subject.views import SubjectViewSet, SubjectUnitViewSet, SubjectAdminViewSet, \
    SubjectChargeViewSet, SubjectOrganViewSet, PGExpertsSystemViewSet, OpinionSheetViewSet, PGOpinionSheetViewSet, \
    PGExpertsSubjectOpinionSheetViewSet, ExpectedResultsViewSet, FundingBudgetViewSet, \
    IntellectualPropertyViewSet, SubjectUnitInfoViewSet, SubjectPersonnelInfoViewSet, SubjectOtherInfoViewSet, \
    AttachmentListViewSet, UnitCommitmentViewSet, SubjectInfoViewSet, ProcessViewSet, AttachmentViewSet, \
    SubjectKExpertsViewSet, ExportDataViewSet
from termination.views import TerminationViewSet, TResearchersViewSet, TOutputViewSet, TCheckListViewSet, \
    TReportViewSet, TExpenditureStatementViewSet, TerminationAttachmentViewSet, \
    TKOpinionSheetViewSet, SubjectTerminationViewSet, ChargeTerminationViewSet, TerminationOpinionViewSet
from upload.views import UploadView, TemplatesViewSet, LoginLogViewSet

from users.views import ForgotPasswordViewSet, SMSCodeViewSet, \
    AccountSettingsViewSet, KExpertsViewSet, PExpertsViewSet, ObtainJSONWebToken, RegisteredViewSet, EnterpriseViewSet, \
    AccountObtainJSONWebToken, AgencyRegisteredViewSet, ResetPasswordViewSet, AgencyViewSet, PermissionsViewSet

router = DefaultRouter()

router.register(r'permissions', PermissionsViewSet, basename='permissions')

# users
# 管理服务机构注册
router.register(r'agency_register', AgencyRegisteredViewSet, basename='agency_register')
# 管理服务机构重置密码
router.register(r'reset_password', ResetPasswordViewSet, basename='reset_password')
# 管理服务机构
router.register(r'agency', AgencyViewSet, basename='agency')

# 管理服务机构=----专家
router.register(r'experts', ExpertsViewSet, basename='experts')


router.register(r'subject_expert', SubjectKExpertsViewSet, basename='subject_expert')



router.register(r'register', RegisteredViewSet, basename='register')
router.register(r'enterprise', EnterpriseViewSet, basename='enterprise')
router.register(r'forgot_password', ForgotPasswordViewSet, basename='forgot_password')
router.register(r'sms_code', SMSCodeViewSet, basename='sms_code')
router.register(r'account_settings', AccountSettingsViewSet, basename='account_settings')
router.register(r'k_experts', KExpertsViewSet, basename='k_experts')
router.register(r'p_experts', PExpertsViewSet, basename='p_experts')

# article
router.register(r'article', ArticleViewSet, r'article')
router.register(r'articles', ArticlesViewSet, r'articles')

# project
router.register(r'batch', BatchViewSet, basename='batch')
router.register(r'project', ProjectViewSet, basename='project')

# subject
router.register(r'attachment', AttachmentViewSet, basename='attachment')

router.register(r'subject', SubjectViewSet, basename='subject')
router.register(r'process', ProcessViewSet, basename='process')
router.register(r'subject_info', SubjectInfoViewSet, basename='subject_info')
router.register(r'subject_unit_info', SubjectUnitInfoViewSet, basename='subject_unit_info')
router.register(r'expected_results', ExpectedResultsViewSet, basename='expected_results')
router.register(r'funding_budget', FundingBudgetViewSet, basename='funding_budget')
router.register(r'intellectual_property', IntellectualPropertyViewSet, basename='intellectual_property')
router.register(r'subject_personnel_info', SubjectPersonnelInfoViewSet, basename='subject_personnel_info')
router.register(r'subject_other_info', SubjectOtherInfoViewSet, basename='subject_other_info')
router.register(r'unit_commitment', UnitCommitmentViewSet, basename='unit_commitment')
router.register(r'attachment_list', AttachmentListViewSet, basename='attachment_list')

router.register(r'subject_admin', SubjectAdminViewSet, basename='subject_admin')
router.register(r'subject_unit', SubjectUnitViewSet, basename='subject_unit')
router.register(r'subject_admin', SubjectAdminViewSet, basename='subject_admin')
router.register(r'subject_charge', SubjectChargeViewSet, basename='subject_charge')
router.register(r'subject_organ', SubjectOrganViewSet, basename='subject_organ')
router.register(r'pg_experts_subject_opinion_sheet', PGExpertsSubjectOpinionSheetViewSet,
                basename='pg_experts_subject_opinion_sheet')

router.register(r'pg_experts_system', PGExpertsSystemViewSet, basename='pg_experts_system')

router.register(r'opinion_sheet', OpinionSheetViewSet, basename='opinion_sheet')
router.register(r'pg_opinion_sheet', PGOpinionSheetViewSet, basename='pg_opinion_sheet')
# report
router.register(r'progress_report', ProgressReportViewSet, basename='progress_report')
# change
router.register(r'change_subject', ChangeSubjectViewSet, basename='change_subject')
router.register(r'project_leader_change', ProjectLeaderChangeViewSet, basename='project_leader_change')
router.register(r'technical_route_change', TechnicalRouteChangeViewSet, basename='technical_route_change')
router.register(r'project_delay_change', ProjectDelayChangeViewSet, basename='project_delay_change')
# research
router.register(r'field_research', FieldResearchViewSet, basename='field_research')
# router.register(r'city_opinion', CityOpinionViewSet, basename='city_opinion')
# router.register(r'public_opinion', PublicOpinionViewSet, basename='public_opinion')
router.register(r'proposal', ProposalViewSet, basename='proposal')
# contract
router.register(r'contract', ContractViewSet, basename='contract')
router.register(r'contract_content', ContractContentViewSet, basename='contract_content')
router.register(r'contract_attachment', ContractAttachmentViewSet, basename='contract_attachment')
# concluding
router.register(r'subject_concluding', SubjectConcludingViewSet, r'subject_concluding')
router.register(r'acceptance', AcceptanceViewSet, r'acceptance')
router.register(r'researchers', ResearchersViewSet, basename='researchers')
router.register(r'output', OutputViewSet, basename='output')
router.register(r'check_list', CheckListViewSet, basename='check_list')
router.register(r'acceptance_opinion', AcceptanceOpinionViewSet, basename='acceptance_opinion')
router.register(r'expenditure_statement', ExpenditureStatementViewSet, basename='expenditure_statement')
router.register(r'acceptance_attachment', AcceptanceAttachmentViewSet, basename='acceptance_attachment')
router.register(r'k_opinion_sheet', KOpinionSheetViewSet, basename='k_opinion_sheet')
# funding
router.register(r'grant_subject', GrantSubjectViewSet, basename='grant_subject')
router.register(r'allocated_single', AllocatedSingleViewSet, basename='allocated_single')
# blacklist
router.register(r'unit_blacklist', UnitBlacklistViewSet, basename='unit_blacklist')
router.register(r'project_leader', ProjectLeaderViewSet, basename='project_leader')
router.register(r'experts_blacklist', ExpertsBlacklistViewSet, basename='experts_blacklist')
router.register(r'agencies_blacklist', AgenciesBlacklistViewSet, basename='agencies_blacklist')
# termination
router.register(r'subject_termination', SubjectTerminationViewSet, r'subject_termination')
router.register(r'termination', TerminationViewSet, basename='termination')
router.register(r't_researchers', TResearchersViewSet, basename='t_researchers')
router.register(r't_output', TOutputViewSet, basename='termination_output')
router.register(r't_checklist', TCheckListViewSet, basename='t_checklist')
router.register(r'termination_opinion', TerminationOpinionViewSet, basename='termination_opinion')
router.register(r't_report', TReportViewSet, basename='t_report')
router.register(r't_expenditure_statement', TExpenditureStatementViewSet, basename='t_expenditure_statement')
router.register(r'termination_attachments', TerminationAttachmentViewSet, basename='termination_attachments')
router.register(r't_k_opinion_sheet', TKOpinionSheetViewSet, basename='t_k_opinion_sheet')
router.register(r'charge_termination', ChargeTerminationViewSet, basename='charge_termination')

router.register(r'templates', TemplatesViewSet, basename='templates')

router.register(r'sms', SendSMSViewSet, basename='sms')
router.register(r'message_record', MessageRecordViewSet, basename='message_record')
# 临时
router.register(r'temporary', TemporaryTemplateViewSet, basename='temporary')

router.register(r'log_data', LoginLogViewSet, basename='log_data')


router.register(r'export_data_object', ExportDataViewSet, basename='export_data_object')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('files/', UploadView.as_view(), name='files'),
    url(r'^api/login/account', AccountObtainJSONWebToken.as_view()),
    url(r'^api/login', ObtainJSONWebToken.as_view()),
    url(r'^api/', include(router.urls)),
    path('api/template/', include('tpl.urls')),
    path('api/v1/', include('expert.urls')),
    url(r'file/(?P<path>.*)$', serve, {'document_root': MEDIA_ROOT}),

]
