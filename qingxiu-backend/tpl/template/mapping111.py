from decimal import Decimal

from subject.models import Subject


def get_data(acceptance, researchers, output, check_list, expenditure_statement, acceptance_opinion):
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

    def get_p16(val):
        tmp = list()
        index = 0
        for i in val:
            index += 1
            tmp.append({
                'c1': index,
                'c2': i['expected'],
                'c3': i['actual'],
            })
        return tmp

    def get_p18(val):
        tmp = list()
        index = 0
        for i in val:
            index += 1
            tmp.append({
                'c1': index,
                'c2': i['name'],
                'c3': i['gender'],
                'c4': i['birthday'],
                'c5': i['technicalTitles'],
                'c6': i['degree'],
                'c7': i['unit'],
                'c8': i['divisionOf'] if i['divisionOf'] is None else '',
            })
        return tmp

    def get_l7():
        subject = Subject.objects.filter(id=acceptance.subject).values('executionTime')
        return subject[0]['executionTime']

    def get_l27_l28():
        a = float(expenditure_statement.Combined[0].get('Combined')['spending']) - float(
            expenditure_statement.indirectCost[0].get('indirectCost')['spending'])
        b = float(expenditure_statement.Combined[0].get('Combined')['grant']) - float(
            expenditure_statement.indirectCost[0].get('indirectCost')['grant'])

        return str(a), str(b)

    data = {
        'p1': acceptance.contractNo,  # 合同编号
        'p2': acceptance.subjectName,  # 项目名称
        'p3': acceptance.unitName,
        'p4': acceptance.applyUnit,
        'p5': get_year(acceptance.declareTime),
        'p6': get_month(acceptance.declareTime),
        'p7': get_day(acceptance.declareTime),
        # 'p8': acceptance.applyUnit,
        # 'p9': acceptance.registeredAddress,

        'p8': acceptance.unitInfo,
        'p9': acceptance.jointUnitInfo if acceptance.jointUnitInfo else [],

        'p10': acceptance.contact,
        'p11': acceptance.mobile,
        'p12': acceptance.zipCode,
        'p13': acceptance.email,
        'p14': acceptance.industry,
        'p15': acceptance.startStopYear,
        'p16': get_p16(acceptance.indicatorsCompletion),
        'p17': acceptance.otherInstructions,
        'p18': get_p18(researchers.researcher),
        'p19': output.projectTeamPersonnelCombined,
        'p20': output.seniorTitle,
        'p21': output.intermediateTitle,
        'p22': output.primaryTitle,
        'p23': output.Dr,
        'p24': output.master,
        'p25': output.bachelor,
        'p26': "%.2f" % (output.fundingCombined/10000/100),
        'p27': "%.2f" % (output.cityFunding/10000/100),
        'p28': "%.2f" % (output.departmentFunding/10000/100),
        'p29': "%.2f" % (output.bankLoan/10000/100),
        'p30': "%.2f" % (output.unitSelfRaised/10000/100),
        'p31': "%.2f" % (output.otherSources/10000/100),
        'p32': output.importedTechnology,
        'p33': output.applicationTechnology,
        'p34': output.scientificTechnologicalAchievementsTransformed,
        'p35': "%.2f" % (output.technicalTrading/10000/100),
        'p36': output.newIndustrialProducts,
        'p37': output.newAgriculturalVariety,
        'p38': output.newProcess,
        'p39': output.newMaterial,
        'p40': output.newDevice,
        'p41': output.cs,
        'p42': output.researchPlatform,
        'p43': output.TS,
        # 'p44': output.aaa,
        'p45': output.pilotStudies,
        'p46': output.pilotLine,
        'p47': output.productionLine,
        'p48': output.experimentalBase,
        'p49': output.applyPatent,
        'p50': output.applyInventionPatent,
        'p51': output.applyUtilityModel,
        'p52': output.authorizedPatents,
        'p53': output.authorizedInventionPatent,
        'p54': output.authorizedUtilityModel,
        'p55': output.technicalStandards,
        'p56': output.internationalStandard,
        'p57': output.nationalStandard,
        'p58': output.industryStandard,
        'p59': output.localStandards,
        'p60': output.enterpriseStandard,
        'p61': output.thesisResearchReport,
        'p62': output.generalJournal,
        'p63': output.coreJournals,
        'p64': output.highLevelJournal,
        'p65': output.postdoctoralTraining,
        'p66': output.trainingDoctors,
        'p67': output.trainingMaster,
        'p68': output.monographs,
        'p69': output.academicReport,
        'p70': output.trainingCourses,
        'p71': output.trainingNumber,
        'p72': "%.2f" % (output.salesRevenue/10000/100),
        'p73': "%.2f" % (output.newProduction/10000/100),
        'p74': "%.2f" % (output.newTax/10000/100),
        'p75': "%.2f" % (output.export/10000/100),
        'p76': "%.2f" % (output.salesRevenue2/10000/100),
        'p77': "%.2f" % (output.newProduction2/10000/100),
        'p78': "%.2f" % (output.newTax2/10000/100),
        'p79': "%.2f" % (output.export2/10000/100),
        'p80': acceptance_opinion.unitOpinion,
        'p81': '',
        'p101': '',
        'p102': '',
        'p103': '',
        'p104': '',
        'p105': '',
        'p106': '',
        'p107': '',
        'p108': '',

        'd1': str(check_list.data)[:4],
        'd2': str(check_list.data)[5:7],
        'd3': check_list.name,
        'd4': check_list.unitName,
        'd5': acceptance.contractNo,
        'd6': check_list.startStopYear[:4],
        'd7': check_list.startStopYear[5:7],
        'd8': check_list.startStopYear[8:12],
        'd9': check_list.startStopYear[13:],
        'd10': check_list.headName,
        'd11': check_list.headTitle,

        'd12': "%.2f" % (check_list.totalBudget/10000/100),
        'd13': check_list.fundingSituation,

        'p120': "%.2f" % (Decimal(check_list.equipmentCosts[0]['totalBudget'])/10000/100),  # 出版/文献/信息传播/知识产权事务费用途说明
        'p121': "%.2f" % (Decimal(check_list.equipmentCosts[0]['actualMoney'])/10000/100),  # 劳务费合计
        'p122': "%.2f" % (Decimal(check_list.equipmentCosts[0]['actualDifferences'])/10000/100),  # 劳务费申请科技经费
        'p123': "%.2f" % (Decimal(check_list.equipmentCosts[0]['spendingMoney'])/10000/100),  # 劳务费其余经费
        'p124': "%.2f" % (Decimal(check_list.equipmentCosts[0]['spendingDifferences'])/10000/100),  # 劳务费用途说明
        'p125': "%.2f" % (Decimal(check_list.materialsCosts[0]['totalBudget'])/10000/100),  # 专家咨询费合计
        'p126': "%.2f" % (Decimal(check_list.materialsCosts[0]['actualMoney'])/10000/100),  # 专家咨询费申请科技经费
        'p127': "%.2f" % (Decimal(check_list.materialsCosts[0]['actualDifferences'])/10000/100),  # 专家咨询费其余经费
        'p128': "%.2f" % (Decimal(check_list.materialsCosts[0]['spendingMoney'])/10000/100),  # 专家咨询费用途说明
        'p129': "%.2f" % (Decimal(check_list.materialsCosts[0]['spendingDifferences'])/10000/100),  # 其他费用合计
        'p130': "%.2f" % (Decimal(check_list.testCosts[0]['totalBudget'])/10000/100),  # 其他费用申请科技经费
        'p131': "%.2f" % (Decimal(check_list.testCosts[0]['actualMoney'])/10000/100),  # 其他费用其余经费
        'p132': "%.2f" % (Decimal(check_list.testCosts[0]['actualDifferences'])/10000/100),  # 其他费用用途说明
        'p133': "%.2f" % (Decimal(check_list.testCosts[0]['spendingMoney'])/10000/100),  # 间接费用合计
        'p134': "%.2f" % (Decimal(check_list.testCosts[0]['spendingDifferences'])/10000/100),  # 间接费用申请科技经费
        'p135': "%.2f" % (Decimal(check_list.fuelCost[0]['totalBudget'])/10000/100),  # 间接费用其余经费
        'p136': "%.2f" % (Decimal(check_list.fuelCost[0]['actualMoney'])/10000/100),  # 间接费用用途说明
        'p137': "%.2f" % (Decimal(check_list.fuelCost[0]['actualDifferences'])/10000/100),  # 合计合计
        'p138': "%.2f" % (Decimal(check_list.fuelCost[0]['spendingMoney'])/10000/100),  # 合计申请科技经费
        'p139': "%.2f" % (Decimal(check_list.fuelCost[0]['spendingDifferences'])/10000/100),  # 合计其余经费
        'p140': "%.2f" % (Decimal(check_list.travelCost[0]['totalBudget'])/10000/100),  # 合计用途说明
        'p141': "%.2f" % (Decimal(check_list.travelCost[0]['actualMoney'])/10000/100),  # 申报单位专利申请总数
        'p142': "%.2f" % (Decimal(check_list.travelCost[0]['actualDifferences'])/10000/100),  # 申报单位专利授权总数
        'p143': "%.2f" % (Decimal(check_list.travelCost[0]['spendingMoney'])/10000/100),  # 申报单位发明申请
        'p144': "%.2f" % (Decimal(check_list.travelCost[0]['spendingDifferences'])/10000/100),  # 申报单位发明授权
        'p145': "%.2f" % (Decimal(check_list.meetingCost[0]['totalBudget'])/10000/100),  # 申报单位实用新型申请
        'p146': "%.2f" % (Decimal(check_list.meetingCost[0]['actualMoney'])/10000/100),  # 申报单位实用新型授权
        'p147': "%.2f" % (Decimal(check_list.meetingCost[0]['actualDifferences'])/10000/100),  # 申报单位软件版权
        'p148': "%.2f" % (Decimal(check_list.meetingCost[0]['spendingMoney'])/10000/100),  # 其中近三年专利申请总数
        'p149': "%.2f" % (Decimal(check_list.meetingCost[0]['spendingDifferences'])/10000/100),  # 其中近三年专利授权总数
        'p150': "%.2f" % (Decimal(check_list.internationalCost[0]['totalBudget'])/10000/100),  # 其中近三年发明申请
        'p151': "%.2f" % (Decimal(check_list.internationalCost[0]['actualMoney'])/10000/100),  # 其中近三年发明授权
        'p152': "%.2f" % (Decimal(check_list.internationalCost[0]['actualDifferences'])/10000/100),  # 其中近三年实用新型申请
        'p153': "%.2f" % (Decimal(check_list.internationalCost[0]['spendingMoney'])/10000/100),  # 其中近三年实用新型授权
        'p154': "%.2f" % (Decimal(check_list.internationalCost[0]['spendingDifferences'])/10000/100),  # 其中近三年软件版权
        'p155': "%.2f" % (Decimal(check_list.publishedCost[0]['totalBudget'])/10000/100),  # 专利申请总数申请
        'p156': "%.2f" % (Decimal(check_list.publishedCost[0]['actualMoney'])/10000/100),  # 专利授权总数
        'p157': "%.2f" % (Decimal(check_list.publishedCost[0]['actualDifferences'])/10000/100),  # 其中近三年软件版权
        'p158': "%.2f" % (Decimal(check_list.publishedCost[0]['spendingMoney'])/10000/100),  # 其中近三年软件版权
        'p159': "%.2f" % (Decimal(check_list.publishedCost[0]['spendingDifferences'])/10000/100),  # 其中近三年软件版权
        'p160': "%.2f" % (Decimal(check_list.personnelCost[0]['totalBudget'])/10000/100),  # 其中近三年软件版权
        'p161': "%.2f" % (Decimal(check_list.personnelCost[0]['actualMoney'])/10000/100),  # 软件版权
        'p162': "%.2f" % (Decimal(check_list.personnelCost[0]['actualDifferences'])/10000/100),  # 其他知识产权现状说明
        'p163': "%.2f" % (Decimal(check_list.personnelCost[0]['spendingMoney'])/10000/100),  # 课题负责人序号
        'p164': "%.2f" % (Decimal(check_list.personnelCost[0]['spendingDifferences'])/10000/100),  # 课题负责人序号
        'p165': "%.2f" % (Decimal(check_list.expertCost[0]['totalBudget'])/10000/100),  # 课题负责人序号
        'p166': "%.2f" % (Decimal(check_list.expertCost[0]['actualMoney'])/10000/100),  # 课题负责人序号
        'p167': "%.2f" % (Decimal(check_list.expertCost[0]['actualDifferences'])/10000/100),  # 课题负责人序号
        'p168': "%.2f" % (Decimal(check_list.expertCost[0]['spendingMoney'])/10000/100),  # 课题负责人序号
        'p169': "%.2f" % (Decimal(check_list.expertCost[0]['spendingDifferences'])/10000/100),  # 课题负责人序号
        'p170': "%.2f" % (Decimal(check_list.managementCost[0]['totalBudget'])/10000/100),  # 课题负责人序号
        'p171': "%.2f" % (Decimal(check_list.managementCost[0]['actualMoney'])/10000/100),  # 课题负责人序号
        'p172': "%.2f" % (Decimal(check_list.managementCost[0]['actualDifferences'])/10000/100),  # 课题负责人序号
        'p173': "%.2f" % (Decimal(check_list.managementCost[0]['spendingMoney'])/10000/100),  # 课题负责人序号
        'p174': "%.2f" % (Decimal(check_list.managementCost[0]['spendingDifferences'])/10000/100),  # 课题负责人序号
        'p175': "%.2f" % (Decimal(check_list.otherCost[0]['totalBudget'])/10000/100),  # 课题负责人序号
        'p176': "%.2f" % (Decimal(check_list.otherCost[0]['actualMoney'])/10000/100),  # 课题负责人序号
        'p177': "%.2f" % (Decimal(check_list.otherCost[0]['actualDifferences'])/10000/100),  # 课题负责人序号
        'p178': "%.2f" % (Decimal(check_list.otherCost[0]['spendingMoney'])/10000/100),  # 课题负责人序号
        'p179': "%.2f" % (Decimal(check_list.otherCost[0]['spendingDifferences'])/10000/100),  # 课题负责人序号
        'p180': "%.2f" % (Decimal(check_list.Combined[0]['totalBudget'])/10000/100),  # 课题负责人序号
        'p181': "%.2f" % (Decimal(check_list.Combined[0]['actualMoney'])/10000/100),  # 课题负责人序号
        'p182': "%.2f" % (Decimal(check_list.Combined[0]['actualDifferences'])/10000/100),  # 课题负责人序号
        'p183': "%.2f" % (Decimal(check_list.Combined[0]['spendingMoney'])/10000/100),  # 课题负责人序号
        'p184': "%.2f" % (Decimal(check_list.Combined[0]['spendingDifferences'])/10000/100),  # 课题负责人序号
        'p185': check_list.balance,  # 课题负责人序号
        'in4': check_list.conclusion,  # 课题负责人序号

        'l1': expenditure_statement.unit,
        'l2': str(expenditure_statement.fillFrom)[:4],
        'l3': str(expenditure_statement.fillFrom)[5:7],
        'l4': str(expenditure_statement.fillFrom)[8:10],
        'l5': expenditure_statement.subjectName,
        'l6': expenditure_statement.contractNo,
        # 'l7': acceptance.startStopYear,
        # [{"fiscalGrant": {"plan": "1000000.00", "actual": "1000000.00"}}]
        'l7': get_l7(),
        'l8': "%.2f" % (expenditure_statement.planFundingCombined/10000/100),
        'l9': "%.2f" % (expenditure_statement.fiscalGrantFunding/10000/100),
        'l10': "%.2f" % (expenditure_statement.remainingFunding/10000/100),
        'l11': "%.2f" % (Decimal(expenditure_statement.fiscalGrant[0].get('fiscalGrant')['plan'])/10000/100),
        'l12': "%.2f" % (Decimal(expenditure_statement.fiscalGrant[0].get('fiscalGrant')['actual'])/10000/100),
        'l13': expenditure_statement.yearMonth[0].get('yearMonth')['time'],
        # 'l14': '',
        'l15': "%.2f" % (Decimal(expenditure_statement.yearMonth[0].get('yearMonth')['plan'])/10000/100),
        'l16': "%.2f" % (Decimal(expenditure_statement.yearMonth[0].get('yearMonth')['actual'])/10000/100),
        'l17': "%.2f" % (Decimal(expenditure_statement.departmentProvide[0].get('departmentProvide')['plan'])/10000/100),
        'l18': "%.2f" % (Decimal(expenditure_statement.departmentProvide[0].get('departmentProvide')['actual'])/10000/100),
        'l19': "%.2f" % (Decimal(expenditure_statement.bankLoan[0].get('bankLoan')['plan'])/10000/100),
        'l20': "%.2f" % (Decimal(expenditure_statement.bankLoan[0].get('bankLoan')['actual'])/10000/100),
        'l21': "%.2f" % (Decimal(expenditure_statement.unitSelfRaised[0].get('unitSelfRaised')['plan'])/10000/100),
        'l22': "%.2f" % (Decimal(expenditure_statement.unitSelfRaised[0].get('unitSelfRaised')['actual'])/10000/100),
        'l23': "%.2f" % (Decimal(expenditure_statement.otherSources[0].get('otherSources')['plan'])/10000/100),
        'l24': "%.2f" % (Decimal(expenditure_statement.otherSources[0].get('otherSources')['actual'])/10000/100),
        'l25': "%.2f" % (Decimal(expenditure_statement.fundingCombined[0].get('fundingCombined')['spending'])/10000/100),
        'l26': "%.2f" % (Decimal(expenditure_statement.fundingCombined[0].get('fundingCombined')['grant'])/10000/100),
        # 'l27': get_l27_l28()[0],
        # 'l28': get_l27_l28()[1],
        # directFee
        'l27': "%.2f" % (Decimal(expenditure_statement.directFee[0].get('directFee')['spending']) / 10000 / 100),
        'l28': "%.2f" % (Decimal(expenditure_statement.directFee[0].get('directFee')['grant']) / 10000 / 100),
        'l29': "%.2f" % (Decimal(expenditure_statement.equipmentFee[0].get('equipmentFee')['spending'])/10000/100),
        'l30': "%.2f" % (Decimal(expenditure_statement.equipmentFee[0].get('equipmentFee')['grant'])/10000/100),
        'l31': "%.2f" % (Decimal(expenditure_statement.materialsCosts[0].get('materialsCosts')['spending'])/10000/100),
        'l32': "%.2f" % (Decimal(expenditure_statement.materialsCosts[0].get('materialsCosts')['grant'])/10000/100),
        'l33': "%.2f" % (Decimal(expenditure_statement.testCost[0].get('testCost')['spending'])/10000/100),
        'l34': "%.2f" % (Decimal(expenditure_statement.testCost[0].get('testCost')['grant'])/10000/100),
        'l35': "%.2f" % (Decimal(expenditure_statement.fuelCost[0].get('fuelCost')['spending'])/10000/100),
        'l36': "%.2f" % (Decimal(expenditure_statement.fuelCost[0].get('fuelCost')['grant'])/10000/100),
        'l37': "%.2f" % (Decimal(expenditure_statement.travelCost[0].get('travelCost')['spending'])/10000/100),
        'l38': "%.2f" % (Decimal(expenditure_statement.travelCost[0].get('travelCost')['grant'])/10000/100),
        'l39': "%.2f" % (Decimal(expenditure_statement.meetingCost[0].get('meetingCost')['spending'])/10000/100),
        'l40': "%.2f" % (Decimal(expenditure_statement.meetingCost[0].get('meetingCost')['grant'])/10000/100),
        'l41': "%.2f" % (Decimal(expenditure_statement.internationalCost[0].get('internationalCost')['spending'])/10000/100),
        'l42': "%.2f" % (Decimal(expenditure_statement.internationalCost[0].get('internationalCost')['grant'])/10000/100),
        'l43': "%.2f" % (Decimal(expenditure_statement.publishedCost[0].get('publishedCost')['spending'])/10000/100),
        'l44': "%.2f" % (Decimal(expenditure_statement.publishedCost[0].get('publishedCost')['grant'])/10000/100),
        'l45': "%.2f" % (Decimal(expenditure_statement.laborCost[0].get('laborCost')['spending'])/10000/100),
        'l46': "%.2f" % (Decimal(expenditure_statement.laborCost[0].get('laborCost')['grant'])/10000/100),
        'l47': "%.2f" % (Decimal(expenditure_statement.expertCost[0].get('expertCost')['spending'])/10000/100),
        'l48': "%.2f" % (Decimal(expenditure_statement.expertCost[0].get('expertCost')['grant'])/10000/100),
        'l49': "%.2f" % (Decimal(expenditure_statement.otherCost[0].get('otherCost')['spending'])/10000/100),
        'l50': "%.2f" % (Decimal(expenditure_statement.otherCost[0].get('otherCost')['grant'])/10000/100),
        'l51': "%.2f" % (Decimal(expenditure_statement.indirectCost[0].get('indirectCost')['spending'])/10000/100),
        'l52': "%.2f" % (Decimal(expenditure_statement.indirectCost[0].get('indirectCost')['grant'])/10000/100),
        'l53': "%.2f" % (Decimal(expenditure_statement.Combined[0].get('Combined')['spending'])/10000/100),
        'l54': "%.2f" % (Decimal(expenditure_statement.Combined[0].get('Combined')['grant'])/10000/100),
    }
    return data
