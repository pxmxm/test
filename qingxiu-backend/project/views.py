# Create your views here.
import datetime
from ast import literal_eval

import xlrd
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from project.models import Category, Batch, Project
from project.serializers import BatchSerializers, ProjectSerializers
from subject.models import Subject


# 项目批次
class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.all()
    serializer_class = BatchSerializers

    # 系统设置 新增计划年度
    def create(self, request, *args, **kwargs):
        n = 0
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan_category = request.data['planCategory']
        new_time = datetime.date.today()
        if self.queryset.filter(annualPlan=serializer.validated_data['annualPlan'],
                                projectBatch=serializer.validated_data['projectBatch']).exists():
            return Response({"code": 1, "message": '%s' % serializer.validated_data['annualPlan'] + '年度下该批次已存在'},
                            status=status.HTTP_200_OK)
        if self.queryset.filter(annualPlan=serializer.validated_data['annualPlan']).exists():
            declare_time = [i.declareTime for i in
                            self.queryset.filter(annualPlan=serializer.validated_data['annualPlan'])]
            new = request.data['declareTime']
            new_list = new.split('-')
            start_new = new_list[0].split('.')
            start_new_time = datetime.date(year=int(start_new[0]), month=int(start_new[1]), day=int(start_new[2]))
            end_new = new_list[-1].split('.')
            end_new_time = datetime.date(year=int(end_new[0]), month=int(end_new[1]), day=int(end_new[2]))
            for i in declare_time:
                old_list = i.split('-')
                start_old = old_list[0].split('.')
                start_old_time = datetime.date(year=int(start_old[0]), month=int(start_old[1]), day=int(start_old[2]))
                end_old = old_list[-1].split('.')
                end_old_time = datetime.date(year=int(end_old[0]), month=int(end_old[1]), day=int(end_old[2]))

                if end_new_time < start_old_time or start_new_time > end_old_time:
                    n += 1
            if len(declare_time) == n:
                self.perform_create(serializer)
                queryset = self.queryset.get(id=serializer.data['id'])
                if start_new_time <= new_time <= end_new_time:
                    queryset.isActivation = '启用'
                    queryset.save()
                else:
                    queryset.isActivation = '禁用'
                    queryset.save()
                for category in plan_category:
                    Category.objects.create(planCategory=category, batch=queryset)
                return Response({"code": 0, "message": "新增成功", "detail": serializer.data},
                                status=status.HTTP_201_CREATED, )
            return Response({"code": 2, "message": "当前计划年度下已存在该项目批次，不允许重复保存"}, status=status.HTTP_200_OK, )
        else:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            queryset = self.queryset.get(id=serializer.data['id'])
            end_time_list = queryset.declareTime.split('-')
            start_time = end_time_list[0].split('.')
            start_time = datetime.date(year=int(start_time[0]), month=int(start_time[1]), day=int(start_time[2]))
            end_time = end_time_list[-1].split('.')
            end_time = datetime.date(year=int(end_time[0]), month=int(end_time[1]), day=int(end_time[2]))
            if start_time <= new_time <= end_time:
                queryset.isActivation = '启用'
                queryset.save()
            else:
                queryset.isActivation = '禁用'
                queryset.save()
            for category in plan_category:
                Category.objects.create(planCategory=category, batch=queryset)
            return Response({"code": 0, "message": "新增成功", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)

    @action(detail=False, methods=['post'], url_path='detection')
    def detection_plan_category(self, request):
        if Project.objects.filter(category__planCategory=request.data['planCategory'],
                                  category__batch__annualPlan=request.data['annualPlan'],
                                  category__batch__projectBatch=request.data['projectBatch']).exists():
            return Response({"code": 1, "message": "该类别已经有项目申报了不支持编辑移出"}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "ok"}, status=status.HTTP_200_OK)

    # 系统设置 编辑项目批次
    def update(self, request, *args, **kwargs):
        plan_category = request.data['planCategory']
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.get_object()
        if self.queryset.filter(annualPlan=serializer.validated_data['annualPlan'],
                                projectBatch=serializer.validated_data['projectBatch']).count() == 0 or \
                self.queryset.filter(
                    annualPlan=serializer.validated_data['annualPlan'],
                    projectBatch=serializer.validated_data['projectBatch']).count() == 1:

            instance.projectBatch = serializer.validated_data['projectBatch']
            category_list = [i.planCategory for i in Category.objects.filter(batch=instance)]
            if plan_category:
                category = (list(set(category_list).difference(set(plan_category))))
                Category.objects.filter(batch=instance, planCategory__in=category).delete()
                for j in plan_category:
                    if Category.objects.filter(batch=instance, planCategory=j).exists():
                        pass
                    else:
                        Category.objects.create(planCategory=j, batch=instance)
                instance.save()
                return Response({"code": 0, "message": "已保存"})
            else:
                return Response({"code": 0, "message": "请选择计划类别"})
        return Response({"code": 1, "message": '%s' % serializer.validated_data['annualPlan'] + "年度下该批次已存在"},
                        status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.order_by('-annualPlan', '-created').filter()
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 删除项目批次
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if Subject.objects.filter(project__category__batch=instance).exists():
            return Response({"code": 1, "message": "该批次下已有执行项目", }, status=status.HTTP_200_OK)
        else:
            Project.objects.filter(category__batch=instance).delete()
            Category.objects.filter(batch=instance).delete()
            self.perform_destroy(instance)
            return Response({"code": 0, "message": "已删除"}, status=status.HTTP_200_OK)

    # 项目批次条件查询
    @action(detail=False, methods=['post'], url_path='query')
    def get_batch_by_query(self, request):
        limit = request.query_params.dict().get('limit', None)
        json_data = request.data
        keys = {
            "annualPlan": "annualPlan",
            "projectBatch": "projectBatch",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = self.queryset.order_by('-annualPlan', '-created').filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 计划年度的展示
    @action(detail=False, methods=['get'], url_path='show_annual_plan')
    def show_annual_plan(self, request):
        instance = self.queryset.values('annualPlan')
        lists = sorted(list(set([i['annualPlan'] for i in instance])), reverse=True)
        return Response({"code": 0, "message": "计划年度列", "detail": lists}, status.HTTP_200_OK)

    # 计划年度下，批次的展示
    @action(detail=False, methods=['get'], url_path='show_project_batch')
    def show_project_batch(self, request):
        annual_plan = request.query_params.dict().get('annualPlan')
        instance = self.queryset.order_by('-created').filter(annualPlan=annual_plan).values('projectBatch')
        lists = [i['projectBatch'] for i in instance]
        return Response({"code": 0, "message": "项目批次列", "detail": lists}, status.HTTP_200_OK)

    # 所有启用计划年度的展示
    @action(detail=False, methods=['get'], url_path='enable_annual_show')
    def enable_annual_show(self, request):
        instance = self.queryset.values('annualPlan', 'isActivation')
        lists = sorted(list(set([i['annualPlan'] for i in instance if i['isActivation'] == '启用'])), reverse=True)
        return Response({"code": 0, "message": "计划年度列", "detail": lists}, status.HTTP_200_OK)

    # 所有启用项目类别的展示
    @action(detail=False, methods=['get'], url_path='enable_category_show')
    def enable_category_show(self, request):
        lists = []
        queryset = self.queryset.filter(annualPlan=request.query_params.dict().get('annualPlan'),
                                        isActivation='启用')
        for category in queryset:
            for i in category.batch_category.values('planCategory'):
                lists.append(i['planCategory'])
        return Response({"code": 0, "message": 'ok', "detail": lists}, status=status.HTTP_200_OK)

    # 计划年度下 所有类别展示
    @action(detail=False, methods=['get'], url_path='show_plan_category')
    def show_plan_category(self, request):
        lists = []
        queryset = self.queryset.filter(annualPlan=request.query_params.dict().get('annualPlan'))
        for category in queryset:
            for i in category.batch_category.values('planCategory'):
                lists.append(i['planCategory'])
        lists = set(lists)
        return Response({"code": 0, "message": 'ok', "detail": lists}, status=status.HTTP_200_OK)

    # 计划年度、 项目批次下所有类别展示
    @action(detail=False, methods=['get'], url_path='show_plan_category_a')
    def show_plan_category_a(self, request):
        lists = []
        json_data = request.query_params.dict()
        keys = {
            "annualPlan": "annualPlan",
            "projectBatch": "projectBatch",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部'}
        queryset = self.queryset.filter(**data)
        for category in queryset:
            for i in category.batch_category.values('planCategory'):
                lists.append(i['planCategory'])
        lists = set(lists)
        return Response({"code": 0, "message": 'ok', "detail": lists}, status=status.HTTP_200_OK)

    # 所有类别展示
    @action(detail=False, methods=['get'], url_path='show_plan_category_b')
    def show_plan_category_b(self, request):
        lists = set([i['planCategory'] for i in Category.objects.filter().values('planCategory')])
        return Response({"code": 0, "message": 'ok', "detail": lists}, status=status.HTTP_200_OK)

    # 小程序
    # 多选择计划年度查询类别
    @action(detail=False, methods=['post'], url_path='multi_select_category')
    def multi_select_category(self, request):
        annual_plan = request.data['annualPlan']
        annual_plan = literal_eval(annual_plan)
        lists = set([i.planCategory for i in Category.objects.filter(batch__annualPlan__in=annual_plan)])
        return Response({"code": 0, "message": 'ok', "detail": lists}, status=status.HTTP_200_OK)


# 项目名称
class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializers

    # 新增项目名称
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if self.queryset.filter(category__batch__annualPlan=request.data['annualPlan'],
                                category__batch__projectBatch=request.data['projectBatch'],
                                category__planCategory=request.data['planCategory'],
                                projectName=request.data['projectName']).exists():
            return Response({"code": 1, "message": '%s' % request.data['annualPlan'] + '年度下该项目名称已存在'},
                            status=status.HTTP_200_OK)
        else:
            category = Category.objects.get(planCategory=request.data['planCategory'],
                                            batch__annualPlan=request.data['annualPlan'],
                                            batch__projectBatch=request.data['projectBatch'])
            self.perform_create(serializer)
            queryset = self.queryset.get(id=serializer.data['id'])
            queryset.category = category
            queryset.save()
            return Response({"code": 0, "message": "新增项目名称成功"}, status=status.HTTP_200_OK)

    # 编辑项目名称
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        if self.queryset.filter(category__batch__annualPlan=request.data['annualPlan'],
                                category__batch__projectBatch=request.data['projectBatch'],
                                category__planCategory=request.data['planCategory'],
                                projectName=request.data['projectName']).exclude(id=instance.id).exists():
            return Response({'message': '%s' % request.data['annualPlan'] + '年度下该项目名称已存在'},
                            status=status.HTTP_200_OK)
        else:
            category = Category.objects.get(planCategory=request.data['planCategory'],
                                            batch__annualPlan=request.data['annualPlan'],
                                            batch__projectBatch=request.data['projectBatch'])
            self.perform_update(serializer)
            instance.category = category
            instance.save()
            return Response({'code': 0, 'message': '编辑项目名称成功'}, status=status.HTTP_200_OK)

    # 项目名称展示
    def list(self, request, *args, **kwargs):
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.order_by('-category__batch__annualPlan', '-created')
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 项目名称展示/某一年度 类别下
    @action(detail=False, methods=['get'], url_path='show_project_name')
    def show_project_name(self, request):
        json_data = request.query_params.dict()
        keys = {
            "annualPlan": "category__batch__annualPlan",
            "planCategory": "category__planCategory",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部'}
        queryset = self.queryset.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        lists = [i['projectName'] for i in serializers.data]
        return Response({"code": 0, "message": "ok", "detail": lists}, status.HTTP_200_OK)

    # 项目名称展示/某一年度 批次 类别下
    @action(detail=False, methods=['get'], url_path='show_project_name_a')
    def show_project_name_a(self, request):
        json_data = request.query_params.dict()
        keys = {
            "annualPlan": "category__batch__annualPlan",
            "projectBatch": "category__batch__projectBatch",
            "planCategory": "category__planCategory",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部'}
        queryset = self.queryset.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        lists = [i['projectName'] for i in serializers.data]
        return Response({"code": 0, "message": "ok", "detail": lists}, status.HTTP_200_OK)

    # 在特定年度、类别下启用的项目名称展示
    @action(detail=False, methods=['get'], url_path='show_enable_project_name')
    def show_enable_project_name(self, request):
        json_data = request.query_params.dict()
        keys = {
            "annualPlan": "category__batch__annualPlan",
            "planCategory": "category__planCategory",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部'}
        queryset = self.queryset.filter(**data, category__batch__isActivation='启用')
        serializers = self.get_serializer(queryset, many=True)
        lists = [i['projectName'] for i in serializers.data]
        return Response({"code": 0, "message": "ok", "detail": lists}, status.HTTP_200_OK)

    # 删除项目名称
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if Subject.objects.filter(project=instance).exists():
            return Response({"code": 0, "message": "该批次下已有执行项目"}, status=status.HTTP_200_OK)
        else:
            self.perform_destroy(instance)
            return Response({"code": 0, "message": "已删除"}, status=status.HTTP_200_OK)

    # 项目名称条件查询
    @action(detail=False, methods=['post'], url_path='query')
    def conditions(self, request):
        limit = request.query_params.dict().get('limit', None)
        json_data = request.data
        keys = {
            "annualPlan": "category__batch__annualPlan",
            "projectBatch": "category__batch__projectBatch",
            "planCategory": "category__planCategory",
            "projectName": "projectName__contains",
            "isActivation": "category__batch__isActivation",
            "charge": "charge__name__contains",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = self.queryset.filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='import_project')
    def import_project(self, request):
        file_excel = request.data['fileExcel']
        wb = xlrd.open_workbook(filename=None, file_contents=file_excel.read())
        table = wb.sheets()[0]
        repeat = []
        n = 1
        for line in range(n, table.nrows):
            row = table.row_values(line)
            if self.queryset.filter(category__batch__annualPlan=request.data['annualPlan'],
                                    category__batch__projectBatch=request.data['projectBatch'],
                                    category__planCategory=request.data['planCategory'],
                                    projectName=row[0]).exists():
                repeat.append(row)
                continue
            else:
                category = Category.objects.get(planCategory=request.data['planCategory'],
                                                batch__annualPlan=request.data['annualPlan'],
                                                batch__projectBatch=request.data['projectBatch'])
                self.queryset.create(category=category, projectName=row[0])
        if repeat:
            return Response({"code": 1, "message": "项目名称部分导入成功", "detail": repeat}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "项目名称全部导入成功"}, status=status.HTTP_200_OK)

    # 平台门户系统
    @action(detail=False, methods=['get'], url_path='declare_project_show')
    def declare_project_show(self, request):
        lists = []
        year = datetime.datetime.now().year
        new_time = datetime.date.today()
        batch = Batch.objects.filter(annualPlan=year)
        for i in batch:
            end_time_list = i.declareTime.split('-')
            end_time = end_time_list[-1].split('.')
            end_time = datetime.date(year=int(end_time[0]), month=int(end_time[1]), day=int(end_time[2]))
            data = {
                    "annualPlan": i.annualPlan,
                    "projectBatch": i.projectBatch,
                    }
            category = Category.objects.filter(batch=i)
            plan_category = []
            for j in category:
                project_name = [{"projectName": i['projectName']} for i in self.queryset.filter(category=j).values('projectName')]
                plan_category.append({
                    'planCategory': j.planCategory,
                    'projectName': project_name,
                })
            if new_time > end_time:
                data['declareTime'] = i.declareTime + '(已过期)'
                data['planCategory'] = plan_category
                lists.append(data)
            else:
                data['declareTime'] = i.declareTime
                data['planCategory'] = plan_category
                lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)
