import os

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from tpl.models import Template
from tpl.serializers import TemplateSerializers
from utils.oss import OSS


class PagingByPageAndSize(PageNumberPagination):
    page_size = 10
    max_page_size = 100
    page_size_query_param = 'size'
    page_query_param = 'page'


class UploadView(APIView):
    def get(self, request, _id=None):
        if _id:
            template = Template.objects.filter(pk=_id).first()
            if template:
                data = TemplateSerializers(instance=template, many=False).data
                return Response({'code': 10000, 'msg': 'Query successful!', 'data': data})
            return Response({'code': 40011, 'msg': 'The template does not exist!', 'data': None})
        templates = Template.objects.all()

        pg = PagingByPageAndSize()
        pgs = pg.paginate_queryset(queryset=templates, request=request, view=self)
        data = TemplateSerializers(instance=pgs, many=True).data
        res = pg.get_paginated_response(data)
        return Response({'code': 10000, 'msg': 'Query successful!', 'data': res.data})

    def post(self, request):
        file = request.FILES.get('file')
        if file:
            file_name = file.name
            file_bytes = file.read()
            url = OSS().put_tpl(file_name, file_bytes)
            template = Template(name=file_name, url=url)
            tpe = request.data.get('type')
            if tpe:
                template.type = tpe
            else:
                return Response({'code': 40022, 'msg': 'No type!', 'data': None})
            version = request.data.get('version')
            if version:
                template.version = version
            else:
                return Response({'code': 40023, 'msg': 'No version!', 'data': None})
            template.save()
            data = TemplateSerializers(instance=template, many=False).data
            return Response({'code': 10000, 'msg': 'Upload successful!', 'data': data})
        return Response({'code': 40021, 'msg': 'No file!', 'data': None})

    def delete(self, request, _id=None):
        if _id:
            template = Template.objects.filter(pk=_id).first()
            if template:
                file_name = os.path.basename(template.url)
                OSS().del_tpl(file_name)
                template.delete()
                data = TemplateSerializers(instance=template, many=False).data
                return Response({'code': 10000, 'msg': 'The template has deleted!', 'data': data})
            return Response({'code': 40042, 'msg': 'The template does not exist!', 'data': None})
        return Response({'code': 40041, 'msg': 'No template id!', 'data': None})
