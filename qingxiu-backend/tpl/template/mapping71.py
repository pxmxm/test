def get_data(change_subject):
    data = {
        'p1': change_subject.name,  # 项目名称
        'p2': change_subject.contractNo,  # 合同编号
        'p3': change_subject.unit,  # 承担单位
        'p4': change_subject.head,  # 项目负责人
        'p5': change_subject.adjustmentContent,  # 调整前内容
        'p6': change_subject.adjustmentAfter,  # 调整后内容
        'p7': change_subject.adjustmentReason,  # 科技项目经费建议额度（万元）
        'p8': change_subject.unitOpinion,  # 申请单位意见
        'p9': change_subject.kOpinion or '',  # 科技局意见
    }
    return data
