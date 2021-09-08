def get_data(params):
    def get_p9(val):
        tmp = list()
        index = 0
        for i in val:
            index += 1
            tmp.append({
                'c1': i['name'],
                'c2': i['unitName'],
                'c3': i['subjectScore']
            })
        while index < 5:
            index += 1
            tmp.append({
                'c1': '',
                'c2': '',
                'c3': '',

            })
        return tmp

    data = {
        'p1': params.planCategory,  # 计划类别
        'p2': params.unitName,  # 申报单位
        'p3': '',  # 项目编号
        'p4': params.subjectName,  # 课题名称
        'p5': params.subjectScore,  # 项目得分
        'p6': params.proposal,  # 立项建议
        'p7': "%.2f" % (params.proposalFunding/10000/100),  # 科技项目经费建议额度（万元）
        'p8': params.projectProposal,
        'p9': get_p9(params.expertsList),
    }
    return data
