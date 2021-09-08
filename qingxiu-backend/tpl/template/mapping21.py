from decimal import Decimal

from utils.big import numToBig


def get_data(contract, content):
    def get_i1(unit_funding):
        tmp = []
        unit_funding = unit_funding
        for i in unit_funding:
            first = numToBig(Decimal(i['first']) / 100)
            last = numToBig(Decimal(i['last']) / 100)
            tmp.append({
                'unit': i['unit'],
                'first': first,
                'last': last,
            })
        return tmp

    def get_p72(contractResearchersList):
        lists = []
        for i in contractResearchersList:
            if i['a']:
                name = i['name']
                a = "%.2f" % (Decimal(i['a']) / 10000 / 100)
                b = "%.2f" % (Decimal(i['b']) / 10000 / 100)
                c = "%.2f" % (Decimal(i['c']) / 10000 / 100)
                d = "%.2f" % (Decimal(i['d']) / 10000 / 100)
                e = "%.2f" % (Decimal(i['e']) / 10000 / 100)
                f = "%.2f" % (Decimal(i['f']) / 10000 / 100)
                g = "%.2f" % (Decimal(i['g']) / 10000 / 100)
                h = "%.2f" % (Decimal(i['h']) / 10000 / 100)
                i = "%.2f" % (Decimal(i['i']) / 10000 / 100)
                lists.append({
                    'name': name,
                    'a': a,
                    'b': b,
                    'c': c,
                    'd': d,
                    'e': e,
                    'f': f,
                    'g': g,
                    'h': h,
                    'i': i,
                })
        return lists

    data = {
        'p1': contract.contractNo,  # 合同编号
        'p2': contract.subject.project.category.planCategory,  # 计划类别
        'p3': content.subjectName,  # 项目名称
        'p4': '、'.join(content.unit),  # 承担单位（乙方）
        'p5': '、'.join(content.unit),  # 乙方
        'p6': content.subjectName,  # 本项目
        'p7': content.executionTime.split('-')[0][0:4],  # 项目实施开始年份
        'p8': content.executionTime.split('-')[0][5:7],  # 项目实施开始月份
        'p9': content.executionTime.split('-')[1][0:4],  # 项目实施结束年份
        'p10': content.executionTime.split('-')[1][5:7],  # 项目实施结束月份
        'p11': content.subjectTotalGoal or '',  # 总体目标
        'p12': '',  # 主要研究开发内容, 包括拟研究解决的问题、技术关键及创新内容
        'p13': content.subjectAssessmentIndicators or '',  # 考核指标
        'p14': content.subjectSchedule,  # 项目进度
        'p15': content.responsibility or '',  # 乙方分工
        'p16': content.personnel,  # 主要研究、开发人员及责任分工
        'i1': get_i1(unit_funding=content.unitFunding),
        'p17': numToBig(content.scienceFunding / 100),  # 甲方计划无偿资助乙方科技经费
        # 'p18': params['本合同生效后拨付乙方首款'],  # 本合同生效后拨付乙方首款
        # 'p19': params['乙方先行垫付该项目经费余款'],  # 乙方先行垫付该项目经费余款
        # 'p20': params['待项目验收通过后再拨付该项目经费余款'],  # 待项目验收通过后再拨付该项目经费余款
        # "%.2f" % (funding_budget.expertRestFunding / 10000 / 100)
        'p21': "%.2f" % (Decimal(content.combined[0].get('unitRaiseFunds')) / 10000 / 100),  # 合计单位自筹经费
        'p22': "%.2f" % (Decimal(content.combined[0].get('scienceFunding')) / 10000 / 100),  # 合计科技经费
        'p23': content.combined[0].get('spendingContent'),  # 合计开支内容
        'p24': content.combined[0].get('note'),  # 合计备注
        'p25': "%.2f" % (Decimal(content.directCosts[0].get('unitRaiseFunds')) / 10000 / 100),  # 直接费用单位自筹经费
        'p26': "%.2f" % (Decimal(content.directCosts[0].get('scienceFunding')) / 10000 / 100),  # 直接费用科技经费
        'p27': content.directCosts[0].get('spendingContent'),  # 直接费用开支内容
        'p28': content.directCosts[0].get('note'),  # 直接费用备注
        'p29': "%.2f" % (Decimal(content.equipmentCosts[0].get('unitRaiseFunds')) / 10000 / 100),  # 设备费单位自筹经费
        'p30': "%.2f" % (Decimal(content.equipmentCosts[0].get('scienceFunding')) / 10000 / 100),  # 设备费科技经费
        'p31': content.equipmentCosts[0].get('spendingContent'),  # 设备费开支内容
        'p32': content.equipmentCosts[0].get('note'),  # 设备费备注
        'p33': "%.2f" % (Decimal(content.materialsCosts[0].get('unitRaiseFunds')) / 10000 / 100),  # 材料费单位自筹经费
        'p34': "%.2f" % (Decimal(content.materialsCosts[0].get('scienceFunding')) / 10000 / 100),  # 材料费科技经费
        'p35': content.materialsCosts[0].get('spendingContent'),  # 材料费开支内容
        'p36': content.materialsCosts[0].get('note'),  # 材料费备注
        'p37': "%.2f" % (Decimal(content.testCosts[0].get('unitRaiseFunds')) / 10000 / 100),  # 测试化验加工费单位自筹经费
        'p38': "%.2f" % (Decimal(content.testCosts[0].get('scienceFunding')) / 10000 / 100),  # 测试化验加工费科技经费
        'p39': content.testCosts[0].get('spendingContent'),  # 测试化验加工费开支内容
        'p40': content.testCosts[0].get('note'),  # 测试化验加工费备注
        'p41': "%.2f" % (Decimal(content.fuelCost[0].get('unitRaiseFunds')) / 10000 / 100),  # 燃料动力费单位自筹经费
        'p42': "%.2f" % (Decimal(content.fuelCost[0].get('scienceFunding')) / 10000 / 100),  # 燃料动力费科技经费
        'p43': content.fuelCost[0].get('spendingContent'),  # 燃料动力费开支内容
        'p44': content.fuelCost[0].get('note'),  # 燃料动力费备注
        'p45': "%.2f" % (Decimal(content.travelCost[0].get('unitRaiseFunds')) / 10000 / 100),  # 差旅费单位自筹经费
        'p46': "%.2f" % (Decimal(content.travelCost[0].get('scienceFunding')) / 10000 / 100),  # 差旅费科技经费
        'p47': content.travelCost[0].get('spendingContent'),  # 差旅费开支内容
        'p48': "%.2f" % (Decimal(content.meetingCost[0].get('unitRaiseFunds')) / 10000 / 100),  # 会议费单位自筹经费
        'p49': "%.2f" % (Decimal(content.meetingCost[0].get('scienceFunding')) / 10000 / 100),  # 会议费科技经费
        'p50': content.meetingCost[0].get('spendingContent'),  # 会议费开支内容
        'p51': "%.2f" % (Decimal(content.internationalCost[0].get('unitRaiseFunds')) / 10000 / 100),  # 国际合作与交流费单位自筹经费
        'p52': "%.2f" % (Decimal(content.internationalCost[0].get('scienceFunding')) / 10000 / 100),  # 国际合作与交流费科技经费
        'p53': content.internationalCost[0].get('spendingContent'),  # 国际合作与交流费开支内容
        'p500': content.internationalCost[0].get('note'),  # 国际合作与交流费开支内容
        'p54': "%.2f" % (Decimal(content.publishedCost[0].get('unitRaiseFunds')) / 10000 / 100),
        # 出版/文献/信息传播/知识产权事务费单位自筹经费
        'p55': "%.2f" % (Decimal(content.publishedCost[0].get('scienceFunding')) / 10000 / 100),
        # 出版/文献/信息传播/知识产权事务费科技经费
        'p56': content.publishedCost[0].get('spendingContent'),  # 出版/文献/信息传播/知识产权事务费开支内容
        'p57': content.publishedCost[0].get('note'),  # 出版/文献/信息传播/知识产权事务费备注
        'p58': "%.2f" % (Decimal(content.laborCost[0].get('unitRaiseFunds')) / 10000 / 100),  # 劳务费单位自筹经费
        'p59': "%.2f" % (Decimal(content.laborCost[0].get('scienceFunding')) / 10000 / 100),  # 劳务费科技经费
        'p60': content.laborCost[0].get('spendingContent'),  # 劳务费开支内容
        'p600': content.laborCost[0].get('note'),  # 劳务费开支内容
        'p61': "%.2f" % (Decimal(content.expertCost[0].get('unitRaiseFunds')) / 10000 / 100),  # 专家咨询费单位自筹经费
        'p62': "%.2f" % (Decimal(content.expertCost[0].get('scienceFunding')) / 10000 / 100),  # 专家咨询费科技经费
        'p63': content.expertCost[0].get('spendingContent'),  # 专家咨询费开支内容
        'p700': content.expertCost[0].get('note'),  # 专家咨询费开支内容：
        'p64': "%.2f" % (Decimal(content.otherCost[0].get('unitRaiseFunds')) / 10000 / 100),  # 其他费用单位自筹经费
        'p65': "%.2f" % (Decimal(content.otherCost[0].get('scienceFunding')) / 10000 / 100),  # 其他费用科技经费
        'p66': content.otherCost[0].get('spendingContent'),  # 其他费用开支内容
        'p67': content.otherCost[0].get('note'),  # 其他费用备注
        'p68': "%.2f" % (Decimal(content.indirectCost[0].get('unitRaiseFunds')) / 10000 / 100),  # 间接费用单位自筹经费
        'p69': "%.2f" % (Decimal(content.indirectCost[0].get('scienceFunding')) / 10000 / 100),  # 间接费用科技经费
        'p70': content.indirectCost[0].get('spendingContent'),  # 间接费用开支内容
        'p800': content.indirectCost[0].get('note'),  # 间接费用开支内容
        'p71': "%.2f" % (Decimal(content.money) / 10000 / 100),  # 乙方负责落实项目总投资
        'p72': get_p72(contractResearchersList=content.contractResearchersList),  # 除甲方提供科技经费之外的其余经费
        'p73': content.secondParty,  # 乙方
        'p74': content.firstParty,   # 甲方
        'p75': content.secondPartyContact,  # 乙方联系人
    }
    return data
