def get_data(expert_opinion_sheet):
    data = {
        'p1': expert_opinion_sheet.planCategory or '',  # 计划类别
        'p2': expert_opinion_sheet.unitName or '',  # 申报单位
        'p3': '',  # 项目编号
        'p4': expert_opinion_sheet.subjectName or '',  # 课题名称
        'p5': expert_opinion_sheet.subjectScore or '',  # 项目得分
        'p6': expert_opinion_sheet.proposal or '',  # 立项建议
        'p7': "%.2f" % (expert_opinion_sheet.proposalFunding/10000/100),  # 科技项目经费建议额度（万元）
        'p8': expert_opinion_sheet.projectProposal or '',
        'p9': expert_opinion_sheet.expertName or '',  # 姓名
        'p10': expert_opinion_sheet.expertUnit or '',  # 工作单位
    }
    return data
