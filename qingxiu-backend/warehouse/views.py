from itertools import combinations

from django.shortcuts import render

# Create your views here.
def combine(temp_list, n):
    ''' 根据n获得列表中的所有可能组合（n个元素为一组）'''
    temp_list2 = []
    for c in combinations(temp_list, n):
        temp_list2.append(c)
    return temp_list2

list1 = ['a', 'b', 'c', 'd']
end_list = []
for i in range(len(list1)):
    end_list.extend(combine(list1, i))
print(end_list)
print(len(end_list))