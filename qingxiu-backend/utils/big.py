def numToBig(num):
    dict1 = {1: '壹', 2: '贰', 3: '叁', 4: '肆', 5: '伍', 6: '陆', 7: '柒', 8: '捌', 9: '玖', 0: '零'}
    dict2 = {2: '拾', 3: '佰', 4: '仟', 5: '万', 6: '拾', 7: '佰', 8: '仟', 1: '元', 9: '角', 10: '分', 11: '整'}
    money = ''  # 最终大写数字
    flag = False  # 去掉多余的十百千
    flag2 = False  # 增加零
    ifint = False  # 整
    count = 0
    count2 = 8
    # num = 11324
    strnum = str(num)
    aa = strnum.split('.')
    bb = list(str(aa[:1])[2:-2])
    cc = list(str(aa[1:])[2:-2])
    # 此处控制：无小数时输出xxx元整
    # 若要求一位小数也带整，即xxx元整并且xxx元xx角整，则修改下方0为1
    if strnum != '0' and strnum != '0.00':
        if len(cc) <= 1:
            ifint = True
        else:
            ifint = False
        # 整数部分
        for i in reversed(bb):
            count = count + 1
            if (int(i) == 0):
                if (flag == True):
                    if (count != 5):
                        continue
                    else:
                        money = dict2[count] + money
                else:
                    if (flag2 == False):
                        money = dict2[count] + money
                    else:
                        if (count != 5):
                            money = '零' + money
                        else:
                            money = dict2[count] + '零' + money
                flag = True
            else:
                flag = False
                flag2 = True
                money = dict1[int(i)] + dict2[count] + money
        # 小数部分
        if len(cc) == 1 and cc[0] == '0':
            if ifint == True:
                money = money + '整'
        elif len(cc) == 2 and cc[0] == '0' and cc[1] == '0':
            money = money + '整'
        else:
            for i in cc:
                count2 = count2 + 1
                money = money + dict1[int(i)] + dict2[count2]
            if (ifint == True):
                money = money + '整'
        return money
    else:
        return '零元'
from decimal import Decimal


