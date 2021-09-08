from decimal import Decimal


def get_data(termination, TResearchers, TOutput, TReport, TCheckList, TExpenditureStatement, TerminationOpinion):

    def get_p19(val):
        tmp = list()
        index = 0
        for i in val:
            index += 1
            tmp.append({
                'c1': index,
                'c2': i['actual'],
                'c3': i['expected'],
            })
        return tmp

    def get_p23(val):
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
                'c8': i['divisionOf'] if not i['divisionOf'] is None else '',
            })
        return tmp

    data = {
        'p1': termination.contractNo,  # 合同书编号
        'p2': termination.subjectName,  # 项目名称
        'p3': termination.unitName,  # 申请单位
        'p4': str(termination.declareTime),  # 申请日期
        # 'p5': termination.unitName,  # 单位名称
        # 'p6': termination.registeredAddress,  # 课题负责人
        'p5': termination.unitInfo,  # 单位名称
        'p6': termination.jointUnitInfo if termination.jointUnitInfo else [],

        'p7': termination.contact,  # 联系电话
        'p8': termination.mobile,  # 手机
        'p9': termination.zipCode,  # 电子邮箱
        'p10': termination.email,  # 起止年限年
        'p11': termination.industry,  # 起止年限月
        'p12': termination.startStopYear[:4],  # 起止年限年
        'p13': termination.startStopYear[5:7],  # 起止年限月
        'p14': termination.startStopYear[8:12],  # 申报日期年
        'p15': termination.startStopYear[13:],  # 申报日期月
        # 'p16': str(termination.grantAmount).split('.')[0],  # 申报日期日
        # 'p17': str(termination.useFunds).split('.')[0],  # 课题名称
        # 'p18': str(termination.surplusFunds).split('.')[0],  # 产学研联合
        'p16': "%.2f" % (Decimal(termination.grantAmount)/10000/100),  # 申报日期日
        'p17': "%.2f" % (Decimal(termination.useFunds)/10000/100),  # 课题名称
        'p18': "%.2f" % (Decimal(termination.surplusFunds)/10000/100),  # 产学研联合
        'p19': get_p19(termination.indicatorsCompletion or []),  # 创新类型
        'p20': termination.terminationReason,  # 合作形式
        # 'p21': termination.terminationReason,  # 所处阶段
        'p22': termination.fileDirectory,  # 课题总体目标
        'p23': get_p23(TResearchers.researcher or []),  # 主要承担人
        'p24': TOutput.unitsNumber,  # 单位名称
        'p25': TOutput.projectTeamPersonnelCombined,  # 统一社会信用代码或组织机构代码
        'p26': TOutput.seniorTitle,  # 法人代表姓名
        'p27': TOutput.intermediateTitle,  # 单位地址
        'p28': TOutput.primaryTitle,  # 邮编
        'p29': TOutput.Dr,  # 单位联系人
        'p30': TOutput.master,  # 联系电话
        'p31': TOutput.bachelor,  # 手机
        'p32': "%.2f" % (TOutput.fundingCombined/10000/100),  # 传真
        'p33': "%.2f" % (TOutput.cityFunding/10000/100),  # 电子邮箱
        'p34': "%.2f" % (TOutput.departmentFunding/10000/100),  # 单位类别
        'p35': "%.2f" % (TOutput.unitSelfRaised/10000/100),  # 材料费开支内容
        'p36': "%.2f" % (TOutput.bankLoan/10000/100),  # 材料费备注
        'p37': "%.2f" % (TOutput.otherSources/10000/100),  # 测试化验加工费单位自筹经费
        'p38': TOutput.importedTechnology,  # 测试化验加工费科技经费
        'p39': TOutput.applicationTechnology,  # 测试化验加工费开支内容
        'p40': TOutput.scientificTechnologicalAchievementsTransformed,  # 测试化验加工费备注
        'p41': "%.2f" % (TOutput.technicalTrading/10000/100),  # 燃料动力费单位自筹经费
        'p42': TOutput.newIndustrialProducts,  # 发明专利
        'p43': TOutput.newAgriculturalVariety,  # 工业新产品
        'p44': TOutput.newProcess,  # 创新/示范基地
        'p45': TOutput.newMaterial,  # 实用新型专利
        'p46': TOutput.newDevice,  # 农业新品种
        'p47': TOutput.cs,  # 申请登记计算机软件
        'p48': TOutput.researchPlatform,  # 个数
        'p49': TOutput.TS,  # 引进技术
        'p50': TOutput.pilotStudies,  # 研发平台
        'p51': TOutput.pilotLine,  # 技术交易额
        'p52': TOutput.productionLine,  # 集成应用技术
        'p53': TOutput.experimentalBase,  # 示范点
        'p54': TOutput.applyPatent,  # 国际标准
        'p55': TOutput.applyInventionPatent,  # 新技术（工艺、方法、模式）
        'p56': TOutput.applyUtilityModel,  # 培养博士后
        'p57': TOutput.authorizedPatents,  # 国家标准
        'p58': TOutput.authorizedInventionPatent,  # 新材料
        'p59': TOutput.authorizedUtilityModel,  # 培养博士
        'p60': TOutput.technicalStandards,  # 行业标准
        'p61': TOutput.internationalStandard,  # 新装置
        'p62': TOutput.nationalStandard,  # 培养硕士
        'p63': TOutput.industryStandard,  # 地方标准
        'p64': TOutput.localStandards,  # 生产线
        'p65': TOutput.enterpriseStandard,  # 一般期刊
        'p66': TOutput.thesisResearchReport,  # 企业标准
        'p67': TOutput.generalJournal,  # 中试线
        'p68': TOutput.coreJournals,  # 核心期刊
        'p69': TOutput.highLevelJournal,  # 举办培训班
        'p70': TOutput.postdoctoralTraining,  # 科技信息服务平台
        'p71': TOutput.trainingDoctors,  # 高水平期刊
        'p72': TOutput.trainingMaster,  # 参加培训人数
        'p73': TOutput.monographs,  # 专著
        'p74': TOutput.trainingCourses,  # 学术报告
        'p75': TOutput.trainingNumber,  # 新增产值
        'p76': "%.2f" % (TOutput.salesRevenue/10000/100),  # 新增税收
        'p77': "%.2f" % (TOutput.newProduction/10000/100),  # 出口创汇
        'p78': "%.2f" % (TOutput.newTax/10000/100),  # 合计
        'p79': "%.2f" % (TOutput.export/10000/100),  # 申请科技经费
        'p80': "%.2f" % (TOutput.salesRevenue2/10000/100),  # 单位自筹
        'p81': "%.2f" % (TOutput.newProduction2/10000/100),  # （国家）部门提供经费
        'p82': "%.2f" % (TOutput.newTax2/10000/100),  # （自治区）部门提供经费
        'p83': "%.2f" % (TOutput.export2/10000/100),  # (市级)部门提供经费
        'p84': TerminationOpinion.unitOpinion,  # 申请单位意见
        # 'p85': '',  # 科技局意见
        'p86': TReport.subjectName,  # 直接费用申请科技经费
        'p87': TReport.contractNo,  # 直接费用其余经费
        'p88': TReport.userName,  # 直接费用用途说明
        'p89': TReport.registeredAddress,  # 设备费合计
        'p90': TReport.contact,  # 设备费申请科技经费
        'p91': TReport.mobile,  # 设备费其余经费
        'p92': TReport.economicBenefits[0]['annual'][0],  # 设备费用途说明
        'p93': TReport.economicBenefits[0]['annual'][1],  # 材料费合计
        'p94': "%.2f" % (Decimal(TReport.economicBenefits[0]['value'][0])/10000/100),  # 材料费申请科技经费
        'p95': "%.2f" % (Decimal(TReport.economicBenefits[0]['value'][1])/10000/100),  # 材料费其余经费
        'p96': "%.2f" % ((Decimal(TReport.economicBenefits[0]['value'][0]) + Decimal(TReport.economicBenefits[0]['value'][1]))/10000/100),  # 材料费用途说明
        'p97': "%.2f" % (Decimal(TReport.economicBenefits[0]['addValue'][0])/10000/100),  # 测试化验加工费合计
        'p98': "%.2f" % (Decimal(TReport.economicBenefits[0]['addValue'][1])/10000/100),  # 测试化验加工费申请科技经费
        'p99': "%.2f" % ((Decimal(TReport.economicBenefits[0]['addValue'][0]) + Decimal(TReport.economicBenefits[0]['addValue'][1]))/10000/100),  # 测试化验加工费其余经费
        'p100': "%.2f" % (Decimal(TReport.economicBenefits[0]['yearsIncome'][0])/10000/100),  # 测试化验加工费用途说明
        'p101': "%.2f" % (Decimal(TReport.economicBenefits[0]['yearsIncome'][1])/10000/100),  # 燃料动力费合计
        'p102': "%.2f" % ((Decimal(TReport.economicBenefits[0]['yearsIncome'][0]) + Decimal(TReport.economicBenefits[0]['yearsIncome'][1]))/10000/100),  # 燃料动力费申请科技经费
        'p103': TReport.socialBenefits,  # 燃料动力费其余经费
        'p104': TCheckList.name,  # 燃料动力费用途说明
        'p105': TCheckList.name,  # 差旅费合计
        'in1': str(TCheckList.data)[:4],
        'in2': str(TCheckList.data)[5:7],
        'p106': TCheckList.name,  # 差旅费申请科技经费
        # 'p107': TCheckList.head,  # 差旅费其余经费
        'p107': termination.unitName,
        'p108': termination.contractNo,  # 差旅费用途说明
        'p109': TCheckList.startStopYear[:4],  # 会议费合计
        'p110': TCheckList.startStopYear[5:7],  # 出口会议费申请科技经费创汇
        'p111': TCheckList.startStopYear[8:12],  # 会议费其余经费
        'p112': TCheckList.startStopYear[13:],  # 会议费用途说明
        'p113': TCheckList.headName,  # 国际合作与交流费合计
        'in3': TCheckList.headTitle,  # 国际合作与交流费申请科技经费
        'p114': "%.2f" % (Decimal(TCheckList.totalBudget)/10000/100),  # 国际合作与交流费申请科技经费
        'p115': "%.2f" % (Decimal(TCheckList.financialAid)/10000/100),  # 财政科技补助经费
        'p116': "%.2f" % (Decimal(TCheckList.departmentSelfRaised)/10000/100),  # 部门提供经费
        'p117': "%.2f" % (Decimal(TCheckList.selfRaised)/10000/100),  # 出版/文献/信息传播/知识产权事务费合计
        'p118': "%.2f" % (Decimal(TCheckList.actualFunding)/10000/100),  # 出版/文献/信息传播/知识产权事务费申请科技经费
        'p119': "%.2f" % (Decimal(TCheckList.scienceFunding)/10000/100),  # 出版/文献/信息传播/知识产权事务费其余经费
        'p120': "%.2f" % (Decimal(TCheckList.equipmentCosts[0]['totalBudget'])/10000/100),  # 出版/文献/信息传播/知识产权事务费用途说明
        'p121': "%.2f" % (Decimal(TCheckList.equipmentCosts[0]['actualMoney'])/10000/100),  # 劳务费合计
        'p122': "%.2f" % (Decimal(TCheckList.equipmentCosts[0]['actualDifferences'])/10000/100),  # 劳务费申请科技经费
        'p123': "%.2f" % (Decimal(TCheckList.equipmentCosts[0]['spendingMoney'])/10000/100),  # 劳务费其余经费
        'p124': "%.2f" % (Decimal(TCheckList.equipmentCosts[0]['spendingDifferences'])/10000/100),  # 劳务费用途说明
        'p125': "%.2f" % (Decimal(TCheckList.materialsCosts[0]['totalBudget'])/10000/100),  # 专家咨询费合计
        'p126': "%.2f" % (Decimal(TCheckList.materialsCosts[0]['actualMoney'])/10000/100),  # 专家咨询费申请科技经费
        'p127': "%.2f" % (Decimal(TCheckList.materialsCosts[0]['actualDifferences'])/10000/100),  # 专家咨询费其余经费
        'p128': "%.2f" % (Decimal(TCheckList.materialsCosts[0]['spendingMoney'])/10000/100),  # 专家咨询费用途说明
        'p129': "%.2f" % (Decimal(TCheckList.materialsCosts[0]['spendingDifferences'])/10000/100),  # 其他费用合计
        'p130': "%.2f" % (Decimal(TCheckList.testCosts[0]['totalBudget'])/10000/100),  # 其他费用申请科技经费
        'p131': "%.2f" % (Decimal(TCheckList.testCosts[0]['actualMoney'])/10000/100),  # 其他费用其余经费
        'p132': "%.2f" % (Decimal(TCheckList.testCosts[0]['actualDifferences'])/10000/100),  # 其他费用用途说明
        'p133': "%.2f" % (Decimal(TCheckList.testCosts[0]['spendingMoney'])/10000/100),  # 间接费用合计
        'p134': "%.2f" % (Decimal(TCheckList.testCosts[0]['spendingDifferences'])/10000/100),  # 间接费用申请科技经费
        'p135': "%.2f" % (Decimal(TCheckList.fuelCost[0]['totalBudget'])/10000/100),  # 间接费用其余经费
        'p136': "%.2f" % (Decimal(TCheckList.fuelCost[0]['actualMoney'])/10000/100),  # 间接费用用途说明
        'p137': "%.2f" % (Decimal(TCheckList.fuelCost[0]['actualDifferences'])/10000/100),  # 合计合计
        'p138': "%.2f" % (Decimal(TCheckList.fuelCost[0]['spendingMoney'])/10000/100),  # 合计申请科技经费
        'p139': "%.2f" % (Decimal(TCheckList.fuelCost[0]['spendingDifferences'])/10000/100),  # 合计其余经费
        'p140': "%.2f" % (Decimal(TCheckList.travelCost[0]['totalBudget'])/10000/100),  # 合计用途说明
        'p141': "%.2f" % (Decimal(TCheckList.travelCost[0]['actualMoney'])/10000/100),  # 申报单位专利申请总数
        'p142': "%.2f" % (Decimal(TCheckList.travelCost[0]['actualDifferences'])/10000/100),  # 申报单位专利授权总数
        'p143': "%.2f" % (Decimal(TCheckList.travelCost[0]['spendingMoney'])/10000/100),  # 申报单位发明申请
        'p144': "%.2f" % (Decimal(TCheckList.travelCost[0]['spendingDifferences'])/10000/100),  # 申报单位发明授权
        'p145': "%.2f" % (Decimal(TCheckList.meetingCost[0]['totalBudget'])/10000/100),  # 申报单位实用新型申请
        'p146': "%.2f" % (Decimal(TCheckList.meetingCost[0]['actualMoney'])/10000/100),  # 申报单位实用新型授权
        'p147': "%.2f" % (Decimal(TCheckList.meetingCost[0]['actualDifferences'])/10000/100),  # 申报单位软件版权
        'p148': "%.2f" % (Decimal(TCheckList.meetingCost[0]['spendingMoney'])/10000/100),  # 其中近三年专利申请总数
        'p149': "%.2f" % (Decimal(TCheckList.meetingCost[0]['spendingDifferences'])/10000/100),  # 其中近三年专利授权总数
        'p150': "%.2f" % (Decimal(TCheckList.internationalCost[0]['totalBudget'])/10000/100),  # 其中近三年发明申请
        'p151': "%.2f" % (Decimal(TCheckList.internationalCost[0]['actualMoney'])/10000/100),  # 其中近三年发明授权
        'p152': "%.2f" % (Decimal(TCheckList.internationalCost[0]['actualDifferences'])/10000/100),  # 其中近三年实用新型申请
        'p153': "%.2f" % (Decimal(TCheckList.internationalCost[0]['spendingMoney'])/10000/100),  # 其中近三年实用新型授权
        'p154': "%.2f" % (Decimal(TCheckList.internationalCost[0]['spendingDifferences'])/10000/100),  # 其中近三年软件版权
        'p155': "%.2f" % (Decimal(TCheckList.publishedCost[0]['totalBudget'])/10000/100),  # 专利申请总数申请
        'p156': "%.2f" % (Decimal(TCheckList.publishedCost[0]['actualMoney'])/10000/100),  # 专利授权总数
        'p157': "%.2f" % (Decimal(TCheckList.publishedCost[0]['actualDifferences'])/10000/100),  # 其中近三年软件版权
        'p158': "%.2f" % (Decimal(TCheckList.publishedCost[0]['spendingMoney'],)/10000/100),  # 其中近三年软件版权
        'p159': "%.2f" % (Decimal(TCheckList.publishedCost[0]['spendingDifferences'])/10000/100),  # 其中近三年软件版权
        'p160': "%.2f" % (Decimal(TCheckList.personnelCost[0]['totalBudget'])/10000/100),  # 其中近三年软件版权
        'p161': "%.2f" % (Decimal(TCheckList.personnelCost[0]['actualMoney'])/10000/100),  # 软件版权
        'p162': "%.2f" % (Decimal(TCheckList.personnelCost[0]['actualDifferences'])/10000/100),  # 其他知识产权现状说明
        'p163': "%.2f" % (Decimal(TCheckList.personnelCost[0]['spendingMoney'])/10000/100),  # 课题负责人序号
        'p164': "%.2f" % (Decimal(TCheckList.personnelCost[0]['spendingDifferences'])/10000/100),  # 课题负责人序号
        'p165': "%.2f" % (Decimal(TCheckList.expertCost[0]['totalBudget'])/10000/100),  # 课题负责人序号
        'p166': "%.2f" % (Decimal(TCheckList.expertCost[0]['actualMoney'])/10000/100),  # 课题负责人序号
        'p167': "%.2f" % (Decimal(TCheckList.expertCost[0]['actualDifferences'])/10000/100),  # 课题负责人序号
        'p168': "%.2f" % (Decimal(TCheckList.expertCost[0]['spendingMoney'])/10000/100),  # 课题负责人序号
        'p169': "%.2f" % (Decimal(TCheckList.expertCost[0]['spendingDifferences'])/10000/100),  # 课题负责人序号
        'p170': "%.2f" % (Decimal(TCheckList.managementCost[0]['totalBudget'])/10000/100),  # 课题负责人序号
        'p171': "%.2f" % (Decimal(TCheckList.managementCost[0]['actualMoney'])/10000/100),  # 课题负责人序号
        'p172': "%.2f" % (Decimal(TCheckList.managementCost[0]['actualDifferences'])/10000/100),  # 课题负责人序号
        'p173': "%.2f" % (Decimal(TCheckList.managementCost[0]['spendingMoney'])/10000/100),  # 课题负责人序号
        'p174': "%.2f" % (Decimal(TCheckList.managementCost[0]['spendingDifferences'])/10000/100),  # 课题负责人序号
        'p175': "%.2f" % (Decimal(TCheckList.otherCost[0]['totalBudget'])/10000/100),  # 课题负责人序号
        'p176': "%.2f" % (Decimal(TCheckList.otherCost[0]['actualMoney'])/10000/100),  # 课题负责人序号
        'p177': "%.2f" % (Decimal(TCheckList.otherCost[0]['actualDifferences'])/10000/100),  # 课题负责人序号
        'p178': "%.2f" % (Decimal(TCheckList.otherCost[0]['spendingMoney'])/10000/100),  # 课题负责人序号
        'p179': "%.2f" % (Decimal(TCheckList.otherCost[0]['spendingDifferences'])/10000/100),  # 课题负责人序号
        'p180': "%.2f" % (Decimal(TCheckList.Combined[0]['totalBudget'])/10000/100),  # 课题负责人序号
        'p181': "%.2f" % (Decimal(TCheckList.Combined[0]['actualMoney'])/10000/100),  # 课题负责人序号
        'p182': "%.2f" % (Decimal(TCheckList.Combined[0]['actualDifferences'])/10000/100),  # 课题负责人序号
        'p183': "%.2f" % (Decimal(TCheckList.Combined[0]['spendingMoney'])/10000/100),  # 课题负责人序号
        'p184': "%.2f" % (Decimal(TCheckList.Combined[0]['spendingDifferences'])/10000/100),  # 课题负责人序号
        'p185': TCheckList.balance,  # 课题负责人序号
        'in4': TCheckList.conclusion,  # 课题负责人序号
        'c1': TExpenditureStatement.unit,
        'c2': str(TExpenditureStatement.fillFrom)[0:4],
        'c3': str(TExpenditureStatement.fillFrom)[5:7],
        'c4': str(TExpenditureStatement.fillFrom)[8:10],
        'c5': termination.subjectName,
        'c6': termination.contractNo,
        'c7': termination.startStopYear,
        'c8': "%.2f" % (TExpenditureStatement.planFundingCombined/10000/100),
        'c9': "%.2f" % (TExpenditureStatement.fiscalGrantFunding/10000/100),
        'c10': "%.2f" % (TExpenditureStatement.remainingFunding/10000/100),
        'c11': "%.2f" % (Decimal(TExpenditureStatement.fiscalGrant[0]['fiscalGrant']['plan'])/10000/100),
        'c12': "%.2f" % (Decimal(TExpenditureStatement.fiscalGrant[0]['fiscalGrant']['actual'])/10000/100),
        'c13': "%.2f" % (Decimal(TExpenditureStatement.equipmentFee[0]['equipmentFee']['spending'])/10000/100),
        'c14': "%.2f" % (Decimal(TExpenditureStatement.equipmentFee[0]['equipmentFee']['grant'])/10000/100),
        'c65': TExpenditureStatement.yearMonth[0]['yearMonth']['time'],
        'c15': "%.2f" % (Decimal(TExpenditureStatement.yearMonth[0]['yearMonth']['plan'])/10000/100),
        'c16': "%.2f" % (Decimal(TExpenditureStatement.yearMonth[0]['yearMonth']['actual'])/10000/100),
        'c17': "%.2f" % (Decimal(TExpenditureStatement.purchaseFee[0]['purchaseFee']['spending'])/10000/100),
        'c18': "%.2f" % (Decimal(TExpenditureStatement.purchaseFee[0]['purchaseFee']['grant'])/10000/100),
        'c19': "%.2f" % (Decimal(TExpenditureStatement.bankLoan[0]['bankLoan']['plan'])/10000/100),
        'c20': "%.2f" % (Decimal(TExpenditureStatement.bankLoan[0]['bankLoan']['actual'])/10000/100),
        'c21': "%.2f" % (Decimal(TExpenditureStatement.testFee[0]['testFee']['spending'])/10000/100),
        'c22': "%.2f" % (Decimal(TExpenditureStatement.testFee[0]['testFee']['grant'])/10000/100),
        'c23': "%.2f" % (Decimal(TExpenditureStatement.departmentProvide[0]['departmentProvide']['plan'])/10000/100),
        'c24': "%.2f" % (Decimal(TExpenditureStatement.departmentProvide[0]['departmentProvide']['actual'])/10000/100),
        'c25': "%.2f" % (Decimal(TExpenditureStatement.equipmentRentalFee[0]['equipmentRentalFee']['spending'])/10000/100),
        'c26': "%.2f" % (Decimal(TExpenditureStatement.equipmentRentalFee[0]['equipmentRentalFee']['grant'])/10000/100),
        'c27': "%.2f" % (Decimal(TExpenditureStatement.unitSelfRaised[0]['unitSelfRaised']['plan'])/10000/100),
        'c28': "%.2f" % (Decimal(TExpenditureStatement.unitSelfRaised[0]['unitSelfRaised']['actual'])/10000/100),
        'c29': "%.2f" % (Decimal(TExpenditureStatement.relatedOperatingExpenses[0]['relatedOperatingExpenses']['spending'])/10000/100),
        'c30': "%.2f" % (Decimal(TExpenditureStatement.relatedOperatingExpenses[0]['relatedOperatingExpenses']['grant'])/10000/100),
        'c31': "%.2f" % (Decimal(TExpenditureStatement.otherSources[0]['otherSources']['plan'])/10000/100),
        'c32': "%.2f" % (Decimal(TExpenditureStatement.otherSources[0]['otherSources']['actual'])/10000/100),
        'c33': "%.2f" % (Decimal(TExpenditureStatement.materialsCosts[0]['materialsCosts']['spending'])/10000/100),
        'c34': "%.2f" % (Decimal(TExpenditureStatement.materialsCosts[0]['materialsCosts']['grant'])/10000/100),
        'c35': "%.2f" % (Decimal(TExpenditureStatement.testCost[0]['testCost']['spending'])/10000/100),
        'c36': "%.2f" % (Decimal(TExpenditureStatement.testCost[0]['testCost']['grant'])/10000/100),
        'c37': "%.2f" % (Decimal(TExpenditureStatement.fuelCost[0]['fuelCost']['spending'])/10000/100),
        'c38': "%.2f" % (Decimal(TExpenditureStatement.fuelCost[0]['fuelCost']['grant'])/10000/100),
        'c39': "%.2f" % (Decimal(TExpenditureStatement.travelCost[0]['travelCost']['spending'])/10000/100),
        'c40': "%.2f" % (Decimal(TExpenditureStatement.travelCost[0]['travelCost']['grant'])/10000/100),
        'c41': "%.2f" % (Decimal(TExpenditureStatement.meetingCost[0]['meetingCost']['spending'])/10000/100),
        'c42': "%.2f" % (Decimal(TExpenditureStatement.meetingCost[0]['meetingCost']['grant'])/10000/100),
        'c43': "%.2f" % (Decimal(TExpenditureStatement.internationalCost[0]['internationalCost']['spending'])/10000/100),
        'c44': "%.2f" % (Decimal(TExpenditureStatement.internationalCost[0]['internationalCost']['grant'])/10000/100),
        'c45': "%.2f" % (Decimal(TExpenditureStatement.publishedCost[0]['publishedCost']['spending'])/10000/100),
        'c46': "%.2f" % (Decimal(TExpenditureStatement.publishedCost[0]['publishedCost']['grant'])/10000/100),
        'c47': "%.2f" % (Decimal(TExpenditureStatement.personnelCost[0]['personnelCost']['spending'])/10000/100),
        'c48': "%.2f" % (Decimal(TExpenditureStatement.personnelCost[0]['personnelCost']['grant'])/10000/100),
        'c49': "%.2f" % (Decimal(TExpenditureStatement.laborCost[0]['laborCost']['spending'])/10000/100),
        'c50': "%.2f" % (Decimal(TExpenditureStatement.laborCost[0]['laborCost']['grant'])/10000/100),
        'c51': "%.2f" % (Decimal(TExpenditureStatement.projectTeamPersonnel[0]['projectTeamPersonnel']['spending'])/10000/100),
        'c52': "%.2f" % (Decimal(TExpenditureStatement.projectTeamPersonnel[0]['projectTeamPersonnel']['grant'])/10000/100),
        'c53': "%.2f" % (Decimal(TExpenditureStatement.temporaryStaff[0]['temporaryStaff']['spending'])/10000/100),
        'c54': "%.2f" % (Decimal(TExpenditureStatement.temporaryStaff[0]['temporaryStaff']['grant'])/10000/100),
        'c55': "%.2f" % (Decimal(TExpenditureStatement.expertCost[0]['expertCost']['spending'])/10000/100),
        'c56': "%.2f" % (Decimal(TExpenditureStatement.expertCost[0]['expertCost']['grant'])/10000/100),
        'c57': "%.2f" % (Decimal(TExpenditureStatement.managementCost[0]['managementCost']['spending'])/10000/100),
        'c58': "%.2f" % (Decimal(TExpenditureStatement.managementCost[0]['managementCost']['grant'])/10000/100),
        'c59': "%.2f" % (Decimal(TExpenditureStatement.otherCost[0]['otherCost']['spending'])/10000/100),
        'c60': "%.2f" % (Decimal(TExpenditureStatement.otherCost[0]['otherCost']['grant'])/10000/100),
        'c61': "%.2f" % (Decimal(TExpenditureStatement.fundingCombined[0]['fundingCombined']['spending'])/10000/100),
        'c62': "%.2f" % (Decimal(TExpenditureStatement.fundingCombined[0]['fundingCombined']['grant'])/10000/100),
        'c63': "%.2f" % (Decimal(TExpenditureStatement.Combined[0]['Combined']['spending'])/10000/100),
        'c64': "%.2f" % (Decimal(TExpenditureStatement.Combined[0]['Combined']['grant'])/10000/100),
    }
    return data
