def get_data(project_leader_change):
    data = {
        'p1': project_leader_change.name,  # 项目名称
        'p2': project_leader_change.contractNo,  # 合同编号
        'p3': project_leader_change.unit,  # 承担单位
        'p4': project_leader_change.head,  # 项目负责人
        'p5': project_leader_change.changeHead,  # 变更后负责人
        'p9': project_leader_change.phone,  # 联系电话
        'p10': project_leader_change.idNumber,  # 课题负责人身份证号码
        'p6': project_leader_change.changeReason,  # 变更理由
        'p7': project_leader_change.unitOpinion,  # 申请单位意见
        'p8': project_leader_change.kOpinion or '',  # 科技局意见
    }
    return data
