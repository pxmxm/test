def get_year(date):
    pass


def get_month(date):
    pass


def num_to_big(num):
    dict1 = {1: '壹', 2: '贰', 3: '叁', 4: '肆', 5: '伍', 6: '陆', 7: '柒', 8: '捌', 9: '玖', 0: '零'}
    dict2 = {2: '拾', 3: '佰', 4: '仟', 5: '万', 6: '拾', 7: '佰', 8: '仟', 1: '元', 9: '角', 10: '分', 11: '整'}
    money = ''  # 最终大写数字
    flag = False  # 去掉多余的十百千
    flag2 = False  # 增加零
    ifint = False  # 整
    count = 0
    count2 = 8
    # num = 11324
    strnum = num
    if type(strnum) != str:
        strnum = str(strnum)
    aa = strnum.split('.')
    bb = list(str(aa[:1])[2:-2])
    cc = list(str(aa[1:])[2:-2])
    # 此处控制：无小数时输出xxx元整
    # 若要求一位小数也带整，即xxx元整并且xxx元xx角整，则修改下方0为1
    if len(cc) <= 0:
        ifint = True
    else:
        ifint = False
    # 整数部分
    for i in reversed(bb):
        count = count + 1
        if int(i) == 0:
            if flag == True:
                if count != 5:
                    continue
                else:
                    money = dict2[count] + money
            else:
                if flag2 == False:
                    money = dict2[count] + money
                else:
                    if count != 5:
                        money = '零' + money
                    else:
                        money = dict2[count] + '零' + money
            flag = True
        else:
            flag = False
            flag2 = True
            money = dict1[int(i)] + dict2[count] + money
    # 小数部分
    for i in cc:
        count2 = count2 + 1
        money = money + dict1[int(i)] + dict2[count2]
    if (ifint == True):
        money = money + '整'
    return money


def get_data(params):
    data = {
        'p1': params['合同编号'],  # 合同编号
        'p2': params['计划类别'],  # 计划类别
        'p3': params['项目名称'],  # 项目名称
        'p4': params['承担单位'],  # 承担单位（乙方）
        'p5': params['乙方'],  # 乙方
        'p6': params['本项目'],  # 本项目
        'p7': get_year(params['项目实施开始日期']),  # 项目实施开始年份
        'p8': get_month(params['项目实施开始日期']),  # 项目实施开始月份
        'p9': get_year(params['项目实施结束日期']),  # 项目实施结束年份
        'p10': get_month(params['项目实施结束日期']),  # 项目实施结束月份
        'p11': params['总体目标'],  # 总体目标
        'p12': params['主要研究开发内容'],  # 主要研究开发内容, 包括拟研究解决的问题、技术关键及创新内容
        'p13': params['考核指标'],  # 考核指标
        'p14': params['项目进度'],  # 项目进度
        'p15': params['乙方分工'],  # 乙方分工
        'p16': params['主要研究开发人员'],  # 主要研究、开发人员及责任分工
        'p17': num_to_big(params['甲方计划无偿资助乙方科技经费']),  # 甲方计划无偿资助乙方科技经费
        'p18': num_to_big(params['本合同生效后拨付乙方首款']),  # 本合同生效后拨付乙方首款
        'p19': params['乙方先行垫付该项目经费余款'],  # 乙方先行垫付该项目经费余款
        'p20': params['待项目验收通过后再拨付该项目经费余款'],  # 待项目验收通过后再拨付该项目经费余款
        'p21': params['合计单位自筹经费'],  # 合计单位自筹经费
        'p22': params['合计科技经费'],  # 合计科技经费
        'p23': params['合计开支内容'],  # 合计开支内容
        'p24': params['合计备注'],  # 合计备注
        'p25': params['直接费用单位自筹经费'],  # 直接费用单位自筹经费
        'p26': params['直接费用科技经费'],  # 直接费用科技经费
        'p27': params['直接费用开支内容'],  # 直接费用开支内容
        'p28': params['直接费用备注'],  # 直接费用备注
        'p29': params['设备费单位自筹经费'],  # 设备费单位自筹经费
        'p30': params['设备费科技经费'],  # 设备费科技经费
        'p31': params['设备费开支内容'],  # 设备费开支内容
        'p32': params['设备费备注'],  # 设备费备注
        'p33': params['材料费单位自筹经费'],  # 材料费单位自筹经费
        'p34': params['材料费科技经费'],  # 材料费科技经费
        'p35': params['材料费开支内容'],  # 材料费开支内容
        'p36': params['材料费备注'],  # 材料费备注
        'p37': params['测试化验加工费单位自筹经费'],  # 测试化验加工费单位自筹经费
        'p38': params['测试化验加工费科技经费'],  # 测试化验加工费科技经费
        'p39': params['测试化验加工费开支内容'],  # 测试化验加工费开支内容
        'p40': params['测试化验加工费备注'],  # 测试化验加工费备注
        'p41': params['燃料动力费单位自筹经费'],  # 燃料动力费单位自筹经费
        'p42': params['燃料动力费科技经费'],  # 燃料动力费科技经费
        'p43': params['燃料动力费开支内容'],  # 燃料动力费开支内容
        'p44': params['燃料动力费备注'],  # 燃料动力费备注
        'p45': params['差旅费单位自筹经费'],  # 差旅费单位自筹经费
        'p46': params['差旅费科技经费'],  # 差旅费科技经费
        'p47': params['差旅费开支内容'],  # 差旅费开支内容
        'p48': params['会议费单位自筹经费'],  # 会议费单位自筹经费
        'p49': params['会议费科技经费'],  # 会议费科技经费
        'p50': params['会议费开支内容'],  # 会议费开支内容
        'p51': params['国际合作与交流费单位自筹经费'],  # 国际合作与交流费单位自筹经费
        'p52': params['国际合作与交流费科技经费'],  # 国际合作与交流费科技经费
        'p53': params['国际合作与交流费开支内容'],  # 国际合作与交流费开支内容
        'p54': params['出版/文献/信息传播/知识产权事务费单位自筹经费'],  # 出版/文献/信息传播/知识产权事务费单位自筹经费
        'p55': params['出版/文献/信息传播/知识产权事务费科技经费'],  # 出版/文献/信息传播/知识产权事务费科技经费
        'p56': params['出版/文献/信息传播/知识产权事务费开支内容'],  # 出版/文献/信息传播/知识产权事务费开支内容
        'p57': params['出版/文献/信息传播/知识产权事务费备注'],  # 出版/文献/信息传播/知识产权事务费备注
        'p58': params['劳务费单位自筹经费'],  # 劳务费单位自筹经费
        'p59': params['劳务费科技经费'],  # 劳务费科技经费
        'p60': params['劳务费开支内容'],  # 劳务费开支内容
        'p61': params['专家咨询费单位自筹经费'],  # 专家咨询费单位自筹经费
        'p62': params['专家咨询费科技经费'],  # 专家咨询费科技经费
        'p63': params['专家咨询费开支内容'],  # 专家咨询费开支内容
        'p64': params['其他费用单位自筹经费'],  # 其他费用单位自筹经费
        'p65': params['其他费用科技经费'],  # 其他费用科技经费
        'p66': params['其他费用开支内容'],  # 其他费用开支内容
        'p67': params['其他费用备注'],  # 其他费用备注
        'p68': params['间接费用单位自筹经费'],  # 间接费用单位自筹经费
        'p69': params['间接费用科技经费'],  # 间接费用科技经费
        'p70': params['间接费用开支内容'],  # 间接费用开支内容
        'p71': params['乙方负责落实项目总投资'],  # 乙方负责落实项目总投资
        'p72': params['除甲方提供科技经费之外的其余经费'],  # 除甲方提供科技经费之外的其余经费
    }
    return data
