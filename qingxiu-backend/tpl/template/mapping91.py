def get_data(project_delay_change):
    data = {
        'p1': project_delay_change.name,  # 项目名称
        'p2': project_delay_change.contractNo,  # 合同编号
        'p3': project_delay_change.unit,  # 承担单位
        'p4': project_delay_change.head,  # 项目负责人
        'p5': project_delay_change.delayTime,  # 延期时间
        'p6': project_delay_change.delayReason,  # 延期理由
        'p7': project_delay_change.unitOpinion,  # 申请单位意见
        'p8': project_delay_change.kOpinion or '',  # 科技局意见
    }
    return data
