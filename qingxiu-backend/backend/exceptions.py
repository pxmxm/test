from rest_framework import status
from rest_framework.exceptions import APIException, _get_error_details, Throttled
from rest_framework.response import Response
from rest_framework.utils.serializer_helpers import ReturnDict, ReturnList
from rest_framework.views import exception_handler


class CustomValidationError(APIException):
    status_code = status.HTTP_200_OK
    default_detail = ('Invalid input.')
    default_code = 'invalid'

    def __init__(self, detail=None, code=None, message=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        if message is None:
            code = self.default_detail

        # For validation failures, we may collect many errors together,
        # so the details should always be coerced to a list if not already.
        self.detail = _get_error_details(detail, code)


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)
    # if isinstance(exc, Throttled):  # check that a Throttled exception is raised
    #     custom_response_data = {  # prepare custom response data
    #         'error_code': '操作太快啦，请休息一下'
    #     }
    #     response.data = custom_response_data  # set the custom response data on response object
    if response:
        response.data['status_code'] = response.status_code
    return response