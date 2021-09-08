def get_data(subject_members_change):
    data = {
        'p1': subject_members_change.name,  # 项目名称
        'p2': subject_members_change.contractNo,  # 合同编号
        'p3': subject_members_change.unit,  # 承担单位
        'p4': subject_members_change.head,  # 项目负责人
        'p5': subject_members_change.changeReasonHead,  # 变更理由及变更后课题人员
        'p6': subject_members_change.unitOpinion,  # 申请单位意见
        'p7': subject_members_change.kOpinion or '',  # 科技局意见
    }
    return data
