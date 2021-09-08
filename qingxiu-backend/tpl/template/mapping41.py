from utils.big import numToBig


def get_data(allocated_single):
    def get_year(val):
        if val:
            return str(val)[:4]
        return ''

    def get_month(val):
        if val:
            return str(val)[5:7]
        return ''

    def get_day(val):
        if val:
            return str(val)[8:]
        return ''

    data = {
        'p1': allocated_single[0].approvalNumber or '',  # 批文编号
        'p2': allocated_single[0].projectNumber or '',  # 项目序号
        'p3': get_year(allocated_single[0].pleaseParagraphDate),  # 请款日期 年
        'p4': get_month(allocated_single[0].pleaseParagraphDate),  # 请款日期 月
        'p5': get_day(allocated_single[0].pleaseParagraphDate),  # 请款日期 日
        'p6': allocated_single[0].subjectName or '',  # 项目名称
        'p7': allocated_single[0].contractNo or '',  # 合同编号
        'p8': allocated_single[0].unitName or '',  # 项目承担单位
        'p9': allocated_single[0].head or '',  # 项目联系人
        'p10': allocated_single[0].mobile or '',  # 收款单位电话
        'p11': numToBig(allocated_single[0].money/100) or '',  # 请款金额
        'p12': allocated_single[0].sourcesFunds or '',  # 款项来源
        'p13': allocated_single[0].receivingUnit or '',  # 收款单位
        'p14': allocated_single[0].bankAccount or '',  # 开户账号
        'p15': allocated_single[0].bank or '',  # 开户银行
        'p16': "%.2f" % (allocated_single[0].money/100),  # 请款金额
    }
    return data
