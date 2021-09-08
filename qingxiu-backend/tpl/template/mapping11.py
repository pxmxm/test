from decimal import Decimal


def get_data(subject, subject_info, enterprise, expected_results, funding_budget, intellectual_property,
             subject_personnel_info, subject_other_info, unit_commitment, subject_unit_info):
    # print(type(subject_unit_info.unitInfo), subject_unit_info.unitInfo)
    # print(type(subject_unit_info.jointUnitInfo), subject_unit_info.jointUnitInfo)

    def get_p137():
        return funding_budget.directCostsCombined + funding_budget.indirectCostCombined

    def get_p138():
        return funding_budget.indirectScienceFunding + funding_budget.directScienceFunding

    def get_p139():
        return funding_budget.directRestFunding + funding_budget.indirectRestFunding

    def get_year(val):
        if val:
            return str(val)[2:4]
        return ''

    def get_month(val):
        if val:
            return str(val)[5:7]
        return ''

    def get_day(val):
        if val:
            return str(val)[8:10]
        return ''

    def get_person(val):
        tmp = list()
        index = 1
        for i in val:
            index += 1
            tmp.append({
                'c1': index,
                'c2': i['name'],
                'c3': i['gender'],
                'c4': i['idNumber'],
                'c5': i['age'],
                'c6': i['recordSchooling'],
                'c7': i['title'],
                'c8': i['workUnit'],
                'c9': i['professional'],
                'c10': i['divisionSubject'],
                'c11': '',
            })
        # while index < 12:
        #     index += 1
        #     tmp.append({
        #         'c1': '',
        #         'c2': '',
        #         'c3': '',
        #         'c4': '',
        #         'c5': '',
        #         'c6': '',
        #         'c7': '',
        #         'c8': '',
        #         'c9': '',
        #         'c10': '',
        #         'c11': '',
        #     })
        return tmp

    def get_other(val):
        tmp = list()
        for i in val:
            if i['funding'] is None or i['funding'] == '':
                tmp.append({
                    'c1': i['contractNo'],
                    'c2': i['subjectName'],
                    'c3': i['subjectSource'],
                    'c4': '',
                    'c5': i['agreedCompletionTime'],
                    'c6': i['completion'],
                })
            else:
                tmp.append({
                    'c1': i['contractNo'],
                    'c2': i['subjectName'],
                    'c3': i['subjectSource'],
                    'c4': "%.2f" % (Decimal(i['funding'])/10000/100),
                    'c5': i['agreedCompletionTime'],
                    'c6': i['completion'],
                })
        return tmp

    project = subject.project
    data = {
        'p1': project.category.batch.annualPlan,  # 申报编号
        'p2': project.category.planCategory,  # 计划类别
        'p3': subject.project.projectName,  # 项目名称
        'p4': subject.subjectName,  # 课题名称
        'p5': subject.unitName,  # 申报单位
        'p6': subject.head,  # 课题负责人
        'p7': subject.phone,  # 联系电话
        'p8': subject.mobile,  # 手机
        'p9': subject.email,  # 电子邮箱
        'p10': subject.startStopYear[2:4],  # 起止年限年
        'p11': subject.startStopYear[5:7],  # 起止年限月
        'p12': subject.startStopYear[10:12],  # 起止年限年
        'p13': subject.startStopYear[13:],  # 起止年限月
        'p14': get_year(subject.declareTime),  # 申报日期年
        'p15': get_month(subject.declareTime),  # 申报日期月
        'p16': get_day(subject.declareTime),  # 申报日期日
        'p17': subject.subjectName,  # 课题名称
        'p18': subject_info.IAR,  # 产学研联合
        'p19': subject_info.innovationType,  # 创新类型
        'p20': subject_info.formCooperation,  # 合作形式
        'p21': subject_info.phase,  # 所处阶段
        'p22': subject_info.overallGoal,  # 课题总体目标
        'p23': subject_info.assessmentIndicators,  # 课题考核指标
        'p24': subject_unit_info.unitInfo,  # 单位名称
        'p25': subject_unit_info.jointUnitInfo,  # 统一社会信用代码或组织机构代码
        'p26': subject_unit_info.unitInfo[0]['legalRepresentative'],  # 法人代表姓名
        'p27': subject_unit_info.unitInfo[0]['registeredAddress'],  # 单位地址
        'p28': subject_unit_info.unitInfo[0]['zipCode'],  # 邮编
        'p29': subject_unit_info.unitInfo[0]['contact'],  # 单位联系人
        'p30': subject_unit_info.unitInfo[0]['phone'],  # 联系电话
        'p31': subject_unit_info.unitInfo[0]['mobile'],  # 手机
        'p32': subject_unit_info.unitInfo[0]['fax'],  # 传真
        'p33': subject_unit_info.unitInfo[0]['email'],  # 电子邮箱
        'p34': subject_unit_info.unitInfo[0]['industry'],  # 单位类别
        'p35': subject_unit_info.unitInfo[0]['projectMembers'],  # 项目人员情况成员总数
        'p36': subject_unit_info.unitInfo[0]['technicalPersonnel'],  # 项目人员情况技术人员
        'p37': subject_unit_info.unitInfo[0]['seniorTitle'],  # 项目人员情况高级职称
        'p38': subject_unit_info.unitInfo[0]['intermediateTitle'],  # 项目人员情况中级职称
        'p39': subject_unit_info.unitInfo[0]['accountName'],  # 单位开户名称
        'p40': subject_unit_info.unitInfo[0]['bank'],  # 开户银行
        'p41': subject_unit_info.unitInfo[0]['bankAccount'],  # 银行账号
        'p42': expected_results.inventionPatent,  # 发明专利
        'p43': expected_results.newIndustrialProducts,  # 工业新产品
        'p44': expected_results.demonstrationBase,  # 创新/示范基地
        'p45': expected_results.utilityModelPatent,  # 实用新型专利
        'p46': expected_results.newAgriculturalVariety,  # 农业新品种
        'p47': expected_results.cs,  # 申请登记计算机软件
        'p48': expected_results.scientificTechnologicalAchievementsTransformed,  # 个数
        'p49': expected_results.importedTechnology,  # 引进技术
        'p50': expected_results.researchPlatform,  # 研发平台
        'p51': "%.2f" % (expected_results.technicalTrading / 10000 / 100),  # 技术交易额
        'p52': expected_results.applicationTechnology,  # 集成应用技术
        'p53': expected_results.pilotStudies,  # 示范点
        'p54': expected_results.internationalStandard,  # 国际标准
        'p55': expected_results.newTechnology,  # 新技术（工艺、方法、模式）
        'p56': expected_results.postdoctoralTraining,  # 培养博士后
        'p57': expected_results.nationalStandard,  # 国家标准
        'p58': expected_results.newMaterial,  # 新材料
        'p59': expected_results.trainingDoctors,  # 培养博士
        'p60': expected_results.industryStandard,  # 行业标准
        'p61': expected_results.newDevice,  # 新装置
        'p62': expected_results.trainingMaster,  # 培养硕士
        'p63': expected_results.localStandards,  # 地方标准
        'p64': expected_results.productionLine,  # 生产线
        'p65': expected_results.generalJournal,  # 一般期刊
        'p66': expected_results.enterpriseStandard,  # 企业标准
        'p67': expected_results.pilotLine,  # 中试线
        'p68': expected_results.coreJournals,  # 核心期刊
        'p69': expected_results.trainingCourses,  # 举办培训班
        'p70': expected_results.TS,  # 科技信息服务平台
        'p71': expected_results.highLevelJournal,  # 高水平期刊
        'p72': expected_results.trainingNumber,  # 参加培训人数
        'p73': expected_results.monographs,  # 专著
        'p74': expected_results.academicReport,  # 学术报告
        'p75': "%.2f" % (expected_results.newProduction / 10000 / 100),  # 新增产值
        'p76': "%.2f" % (expected_results.newTax / 10000 / 100),  # 新增税收
        'p77': "%.2f" % (expected_results.export / 10000 / 100),  # 出口创汇
        'p78': "%.2f" % (funding_budget.combined / 10000 / 100),  # 合计
        'p79': "%.2f" % (funding_budget.scienceFunding / 10000 / 100),  # 申请科技经费
        'p80': "%.2f" % (funding_budget.unitSelfRaised / 10000 / 100),  # 单位自筹
        'p81': "%.2f" % (funding_budget.stateFunding / 10000 / 100),  # '（国家）部门提供经费
        'p82': "%.2f" % (funding_budget.departmentFunding / 10000 / 100),  # '（自治区）部门提供经费
        'p83': "%.2f" % (funding_budget.municipalFunding / 10000 / 100),  # '(市级)部门提供经费
        'p84': "%.2f" % (funding_budget.otherFunding / 10000 / 100),  # 其他经费
        'p85': "%.2f" % (funding_budget.directCostsCombined / 10000 / 100),  # 直接费用合计
        'p86': "%.2f" % (funding_budget.directScienceFunding / 10000 / 100),  # 直接费用申请科技经费
        'p87': "%.2f" % (funding_budget.directRestFunding / 10000 / 100),  # 直接费用其余经费
        'p88': funding_budget.directUseInstructions or '',  # 直接费用用途说明
        'p89': "%.2f" % (funding_budget.equipmentCostsCombined / 10000 / 100),  # 设备费合计
        'p90': "%.2f" % (funding_budget.equipmentScienceFunding / 10000 / 100),  # 设备费申请科技经费
        'p91': "%.2f" % (funding_budget.equipmentRestFunding / 10000 / 100),  # 设备费其余经费
        'p92': funding_budget.equipmentUseInstructions or '',  # 设备费用途说明
        'p93': "%.2f" % (funding_budget.materialsCostsCombined / 10000 / 100),  # 材料费合计
        'p94': "%.2f" % (funding_budget.materialsScienceFunding / 10000 / 100),  # 材料费申请科技经费
        'p95': "%.2f" % (funding_budget.materialsRestFunding / 10000 / 100),  # 材料费其余经费
        'p96': funding_budget.materialsUseInstructions or '',  # 材料费用途说明
        'p97': "%.2f" % (funding_budget.testCostsCombined / 10000 / 100),  # 测试化验加工费合计
        'p98': "%.2f" % (funding_budget.testScienceFunding / 10000 / 100),  # 测试化验加工费申请科技经费
        'p99': "%.2f" % (funding_budget.testRestFunding / 10000 / 100),  # 测试化验加工费其余经费
        'p100': funding_budget.testUseInstructions or '',  # 测试化验加工费用途说明
        'p101': "%.2f" % (funding_budget.fuelCostCombined / 10000 / 100),  # 燃料动力费合计
        'p102': "%.2f" % (funding_budget.fuelScienceFunding / 10000 / 100),  # 燃料动力费申请科技经费
        'p103': "%.2f" % (funding_budget.fuelRestFunding / 10000 / 100),  # 燃料动力费其余经费
        'p104': funding_budget.fuelUseInstructions or '',  # 燃料动力费用途说明
        'p105': "%.2f" % (funding_budget.travelCostCombined / 10000 / 100),  # 差旅费合计
        'p106': "%.2f" % (funding_budget.travelScienceFunding / 10000 / 100),  # 差旅费申请科技经费
        'p107': "%.2f" % (funding_budget.travelRestFunding / 10000 / 100),  # 差旅费其余经费
        'p108': funding_budget.travelUseInstructions or '',  # 差旅费用途说明
        'p109': "%.2f" % (funding_budget.meetingCostCombined / 10000 / 100),  # 会议费合计
        'p110': "%.2f" % (funding_budget.meetingScienceFunding / 10000 / 100),  # 出口会议费申请科技经费创汇
        'p111': "%.2f" % (funding_budget.meetingRestFunding / 10000 / 100),  # 会议费其余经费
        'p112': funding_budget.meetingUseInstructions or '',  # 会议费用途说明
        'p113': "%.2f" % (funding_budget.internationalCostCombined / 10000 / 100),  # 国际合作与交流费合计
        'p114': "%.2f" % (funding_budget.internationalScienceFunding / 10000 / 100),  # 国际合作与交流费申请科技经费
        'p115': "%.2f" % (funding_budget.internationalRestFunding / 10000 / 100),  # 国际合作与交流费其余经费
        'p116': funding_budget.internationalUseInstructions or '',  # 国际合作与交流费用途说明
        'p117': "%.2f" % (funding_budget.publishedCostCombined / 10000 / 100),  # 出版/文献/信息传播/知识产权事务费合计
        'p118': "%.2f" % (funding_budget.publishedScienceFunding / 10000 / 100),  # 出版/文献/信息传播/知识产权事务费申请科技经费
        'p119': "%.2f" % (funding_budget.publishedRestFunding / 10000 / 100),  # 出版/文献/信息传播/知识产权事务费其余经费
        'p120': funding_budget.publishedUseInstructions or '',  # 出版/文献/信息传播/知识产权事务费用途说明
        'p121': "%.2f" % (funding_budget.laborCostCombined / 10000 / 100),  # 劳务费合计
        'p122': "%.2f" % (funding_budget.laborScienceFunding / 10000 / 100),  # 劳务费申请科技经费
        'p123': "%.2f" % (funding_budget.laborRestFunding / 10000 / 100),  # 劳务费其余经费
        'p124': funding_budget.laborUseInstructions or '',  # 劳务费用途说明
        'p125': "%.2f" % (funding_budget.expertCostCombined / 10000 / 100),  # 专家咨询费合计
        'p126': "%.2f" % (funding_budget.expertScienceFunding / 10000 / 100),  # 专家咨询费申请科技经费
        'p127': "%.2f" % (funding_budget.expertRestFunding / 10000 / 100),  # 专家咨询费其余经费
        'p128': funding_budget.expertUseInstructions or '',  # 专家咨询费用途说明
        'p129': "%.2f" % (funding_budget.otherCostCombined / 10000 / 100),  # 其他费用合计
        'p130': "%.2f" % (funding_budget.otherScienceFunding / 10000 / 100),  # 其他费用申请科技经费
        'p131': "%.2f" % (funding_budget.otherRestFunding / 10000 / 100),  # 其他费用其余经费
        'p132': funding_budget.otherUseInstruction or '',  # 其他费用用途说明
        'p133': "%.2f" % (funding_budget.indirectCostCombined / 10000 / 100),  # 间接费用合计
        'p134': "%.2f" % (funding_budget.indirectScienceFunding / 10000 / 100),  # 间接费用申请科技经费
        'p135': "%.2f" % (funding_budget.indirectRestFunding / 10000 / 100),  # 间接费用其余经费
        'p136': funding_budget.indirectUseInstruction or '',  # 间接费用用途说明
        'p137': "%.2f" % (get_p137() / 10000 / 100),  # 合计合计
        'p138': "%.2f" % (get_p138() / 10000 / 100),  # 合计申请科技经费
        'p139': "%.2f" % (get_p139() / 10000 / 100),  # 合计其余经费
        'p140': funding_budget.useInstructions or '',  # 合计用途说明
        'p141': intellectual_property.totalNumberPatentApplications,  # 申报单位专利申请总数
        'p142': intellectual_property.totalNumberPatentLicenses,  # 申报单位专利授权总数
        'p143': intellectual_property.inventionApplication,  # 申报单位发明申请
        'p144': intellectual_property.inventionAuthorization,  # 申报单位发明授权
        'p145': intellectual_property.applicationUtilityModel,  # 申报单位实用新型申请
        'p146': intellectual_property.authorizationUtilityModel,  # 申报单位实用新型授权
        'p147': intellectual_property.softwareCopyright,  # 申报单位软件版权
        'p148': intellectual_property.totalNumberPatentApplications3,  # 其中近三年专利申请总数
        'p149': intellectual_property.totalNumberPatentLicenses3,  # 其中近三年专利授权总数
        'p150': intellectual_property.inventionApplication3,  # 其中近三年发明申请
        'p151': intellectual_property.inventionAuthorization3,  # 其中近三年发明授权
        'p152': intellectual_property.applicationUtilityModel3,  # 其中近三年实用新型申请
        'p153': intellectual_property.authorizationUtilityModel3,  # 其中近三年实用新型授权
        'p154': intellectual_property.softwareCopyright3,  # 其中近三年软件版权
        'p155': intellectual_property.totalNumberPatentApplications2,  # 专利申请总数申请
        'p156': intellectual_property.totalNumberPatentLicenses2,  # 专利授权总数
        'p157': intellectual_property.inventionApplication2,  # 其中近三年软件版权
        'p158': intellectual_property.inventionAuthorization2,  # 其中近三年软件版权
        'p159': intellectual_property.applicationUtilityModel2,  # 其中近三年软件版权
        'p160': intellectual_property.authorizationUtilityModel2,  # 其中近三年软件版权
        'p161': intellectual_property.softwareCopyright2,  # 软件版权
        'p162': intellectual_property.instructions,  # 其他知识产权现状说明
        'p163': str(subject_personnel_info.id),  # 课题负责人序号
        'p164': subject_personnel_info.name,  # 课题负责人姓名
        'p165': subject_personnel_info.gender,  # 课题负责人性别
        'p166': subject_personnel_info.idNumber,  # 课题负责人身份证号码
        'p167': subject_personnel_info.age,  # 课题负责人年龄
        'p168': subject_personnel_info.recordSchooling,  # 课题负责人学历
        'p169': subject_personnel_info.title,  # 课题负责人职称
        'p170': subject_personnel_info.workUnit,  # 课题负责人工作单位
        'p171': subject_personnel_info.professional or '',  # 课题负责人从事专业
        'p172': subject_personnel_info.divisionSubject or '',  # 课题负责人课题分工
        'p173': '',  # 课题负责人签字
        'p174': get_person(subject_personnel_info.researchDevelopmentPersonnel or []),  # 主要研究开发人员
        'p175': get_other(subject_other_info.otherMatters or []),  # 课题负责人近五年内承担各级科技计划项目（课题）完成情况
        'p176': subject_other_info.financialFundsOtherSupport,  # 本申报课题已获得的财政经费等支持情况
        'p177': unit_commitment.commitment,  # 本申报课题已获得的财政经费等支持情况
    }
    return data
