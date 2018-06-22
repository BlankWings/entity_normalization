import dictionary
import jieba.posseg as pseg
import jieba.analyse
import linecache

#加载jieba分词自建的词典
jieba.load_userdict("jieba_dictionary/local.txt")
jieba.load_userdict("jieba_dictionary/suffix.txt")

#full_abb_file是全称简称对文件，用于测试准确率
#processed_word是根据jieba分词，自建词典和自定义规则生成的分词结果
#abb_storage是根据分词结果processed_word和自定义规则生成的简称侯选库
full_abb_file = "data/full_abb.txt"
processed_word_file = "data/processed_word.txt"
abb_storage_file = 'data/abb_storage.txt'

#主程序共有三个类，Process类，Ruler类和Test类
#Process类用于处理全称生成对应的分词结果，输入为全称（类型为字符串），输出为分词结果（类型为字典，词性或序号为键，对应分词为值）
class Process:
    #因为目的是生成简称，所以分词结果不能太长，需要对长度大于等于4的分词，进行切分后再分词
    #设置一个处理短分词的函数，city_value用于区分多个地名，rank用于排序
    def short_word(self,key,value,city_value,rank):
        word_dict = {}
        # 对于“中国”，“有限公司”，“股份”，“集团”，“银行”，“分行”，“支行”分别赋予对应键为“z”，“yy”，“gg”，“jj”，“yh”，“fh”，“zh”
        if  value == "z" or value == "yy"or value == "gg" or value == "jj" \
        or value == "yh" or value == "zh"or value == "fh" :
            word_dict[value] = key
        # 对省市地名的处理：第一个出现的省市，键为“nss”，后面出现的省市地名，键为递增的数字。
        elif value == "nss" and city_value == False:
            word_dict[value] = key
            city_value = True
        else:
            word_dict[rank] = key
            rank += 1
        return word_dict, rank, city_value
    #处理单个全称字符串
    def participle_single(self, full_name_single):
        process = Process()
        # 对输入进行处理
        full_name = str(full_name_single)
        full_name = full_name.strip()
        #processed_word_dict储存分词结果,键-1储存全称
        processed_word_dict = {}
        processed_word_dict[-1] = full_name
        # 使用jieba进行分词，得到原始的分词结果（结果类型为generator）
        full_name_pseg = pseg.cut(full_name)
        # rank用来对普通的分词以递增的顺序排序,city用来处理全称中多次出现地名。
        rank = 0
        city_value = False
        #这里的key为分词，value为对应词性
        for key, value in full_name_pseg:
            #判断分词key是不是监管机构名称，是监管机构赋予其键为"regulator"，赋予特定值特定的键，目的是在Ruler类中，通过特定的键使用特定的值（即分词）产生建成候选
            if key in dictionary.regulator_dictionary.keys():
                processed_word_dict["regulator"] = key
                continue
            #对于长度小于4的key或者是"有限公司"，直接调用short_word函数
            if len(key) < 4 or key == "有限公司":
                word_dict,rank,city_value = process.short_word(key,value,city_value,rank)
                for sub_key, sub_value in word_dict.items():
                    processed_word_dict[sub_key] = sub_value
            #对于长度大于4的词，要分成2个单位长度的词，再应用short_word函数
            elif len(key) >= 4:
                length = int(len(key)/2)
                for j in range(length):
                    new_key = pseg.cut(key[2*j:2*j+2])
                    for sub_key,sub_value in new_key:
                        word_dict,rank,city_value = process.short_word(sub_key, sub_value, city_value, rank)
                        for key1, value1 in word_dict.items():
                            processed_word_dict[key1] = value1
        #下面是对已经生成的分词字典进行处理。
        # 如果全称分词后有1+2+1的形式，改为2+2
        if 2 in processed_word_dict.keys():
            if len(processed_word_dict[0])==1 and len(processed_word_dict[1])==2 and len(processed_word_dict[2])==1:
                processed_word_dict[0] = processed_word_dict[0] +processed_word_dict[1][0]
                processed_word_dict[1] = processed_word_dict[1][1] +processed_word_dict[2]
        # 如果0和1都是1个字，合并
        if 1 in processed_word_dict.keys():
            if len(processed_word_dict[0])==1 and len(processed_word_dict[1])==1:
                processed_word_dict[0] = processed_word_dict[0] +processed_word_dict[1]
                processed_word_dict[1] = processed_word_dict[0]
        #print(processed_word_dict)
        return processed_word_dict

class Ruler:
    # 函数regulator_ruler生成监管机构的简称
    def regulator_ruler(self, processed_word_dict):
        # result用于根据规则生成建成候选，abb_storage用于储存简称候选，rank用于对候选简称排序
        dict = processed_word_dict
        abb_storage = {}
        rank = 0
        if 'nss' not in dict.keys():
            abb_storage[rank] = dictionary.regulator_dictionary[dict["regulator"]]
        elif 'nss' in dict.keys():
            abb_storage[rank] = dict['nss'] + dictionary.place_regulator_dictionary[dict["regulator"]]
        return abb_storage
    #函数bank_ruler用来对银行生成简称候选。
    def bank_ruler(self,processed_word_dict):
        # result用于根据规则生成建成候选，abb_storage用于储存简称候选，rank用于对候选简称排序
        dict = processed_word_dict
        abb_storage = {}
        rank = 0
        # 候选一：去掉“股份有限公司“,对应abb_storage[0]
        result = ""
        for key, value in dict.items():
            if key != 'gg' and key != 'yy':
                result += value
                abb_storage[rank] = result
        # 候选二：去掉“地名”和“股份有限公司“,对应abb_storage[1]
        result = ""
        rank += 1
        for key, value in dict.items():
            if key != 'gg' and key != 'yy' and key != 'nss' and key != 'z':
                result +=  value
                abb_storage[rank] = result
        #候选三：地名或0加银行,这种候选简称主要是为了识别上市银行的简称
        for key, value in dict.items():
            if key == 0 or key == "nss":
                rank += 1
                result = dict[key] + "银行"   #这种属于重新赋值了，不需要result = “”
                abb_storage[rank] = result
        # 查询建立的词典中有没有abb_storage[0]，如果有，提取已经写好的简称放入简称库中。
        if abb_storage[0] in dictionary.bank_full_abb_dictionary.keys():
            rank += 1
            abb_storage[rank] = dictionary.bank_full_abb_dictionary[abb_storage[0]]
        #将“农村商业”替换为“农商”，生成一个候选简称
        if "农村商业" in abb_storage[0]:
            rank += 1
            abb_storage[rank] = abb_storage[0].replace("农村商业", '农商')
        if "农村商业" in abb_storage[1]:
            rank += 1
            abb_storage[rank] = abb_storage[1].replace("农村商业", '农商')
        # 筛选掉是“银行”的简称
        abb_storage = {key: value for key, value in abb_storage.items() if value != "银行"}
        return abb_storage
    #函数company_ruler生成普通公司的简称集
    def company_ruler(self,processed_word_dict):
        # result用于根据规则生成建成候选，abb_storage用于储存简称候选，rank用于对候选简称排序
        dict = processed_word_dict
        abb_storage = {}
        rank = 0
        # 下面是建立候选简称的规则
        for key, value in dict.items():
            # 规则一nss/zh加0,1,2还有对应的简称加0,1,2，nss/zh加0,1的第一个字
            if key == 'nss' or key == 'z' :
                if 0 in dict.keys():
                    result = value + dict[0]
                    abb_storage[rank] = result
                    rank += 1
                    for full, abb in dictionary.province_city_abb_dictionary.items():
                        if value == full:
                            result = abb + dict[0]
                            abb_storage[rank] = result
                            rank += 1
                            break
                if 1 in dict.keys():
                    result = value + dict[1]
                    abb_storage[rank] = result
                    rank += 1
                    #nss/zh加0,1的第一个字
                    result = value + dict[0][0] + dict[1][0]
                    abb_storage[rank] = result
                    rank += 1
                    for full, abb in dictionary.province_city_abb_dictionary.items():
                        if value == full:
                            result = abb + dict[1]
                            abb_storage[rank] = result
                            rank += 1
                            break
                if 2 in dict.keys():
                    result = value + dict[2]
                    abb_storage[rank] = result
                    rank += 1
                    for full, abb in dictionary.province_city_abb_dictionary.items():
                        if value == full:
                            result = abb + dict[0]
                            abb_storage[rank] = result
                            rank += 1
            # 规则二0,1,0+1,0+2,1+2，0+1+2，0+3,1+3,2+3,0+1和2的第一个字
            if key == 0:
                result = dict[0]
                abb_storage[rank] = result
                rank += 1
            if key == 1:
                result = dict[0] + dict[1]
                abb_storage[rank] = result
                rank += 1
                result = dict[1]
                abb_storage[rank] = result
                rank += 1
            if key == 2:
                result = dict[0] + dict[2]
                abb_storage[rank] = result
                rank += 1
                result = dict[1] + dict[2]
                abb_storage[rank] = result
                rank += 1
                result = dict[0] + dict[1] + dict[2]
                abb_storage[rank] = result
                rank += 1
                result = dict[0] + dict[1][0] + dict[2][0]
                abb_storage[rank] = result
                rank += 1
            if key == 3:
                result = dict[0] + dict[3]
                abb_storage[rank] = result
                rank += 1
                result = dict[1] + dict[3]
                abb_storage[rank] = result
                rank += 1
                result = dict[2] + dict[3]
                abb_storage[rank] = result
                rank += 1
            # 规则三0+jj/1+jj/2+jj和0+gg/1+gg/2+gg和0+kk/1+kk/2+kk
            if key == 'jj':
                if 0 in dict.keys():
                    result = dict[0] + value
                    abb_storage[rank] = result
                    rank += 1
                if 1 in dict.keys():
                    result = dict[1] + value
                    abb_storage[rank] = result
                    rank += 1
                if 2 in dict.keys():
                    result = dict[2] + value
                    abb_storage[rank] = result
                    rank += 1
            if key == 'gg':
                if 0 in dict.keys():
                    result = dict[0] + value
                    abb_storage[rank] = result
                    rank += 1
                if 1 in dict.keys():
                    result = dict[1] + value
                    abb_storage[rank] = result
                    rank += 1
                if 2 in dict.keys():
                    result = dict[2] + value
                    abb_storage[rank] = result
                    rank += 1
            if key == 'kk':
                if 0 in dict.keys():
                    result = dict[0] + value
                    abb_storage[rank] = result
                    rank += 1
                if 1 in dict.keys():
                    result = dict[1] + value
                    abb_storage[rank] = result
                    rank += 1
                if 2 in dict.keys():
                    result = dict[2] + value
                    abb_storage[rank] = result
                    rank += 1
        return abb_storage
    #单个全称的简称候选
    def ruler_single(self,processed_word_dict,abb_storage_file=abb_storage_file):
        # result用于根据规则生成建成候选，abb_storage用于储存简称候选
        dict = processed_word_dict
        abb_storage = {}
        ruler = Ruler()
        #先检查是不是监管机构
        if "regulator" in dict.keys():
            abb_storage = ruler.regulator_ruler(dict)
        # 对于银行的情况，分为有分行支行的和没有分行支行的。
        elif 'yh' in dict.keys() :
            #没有分行或支行
            if 'zh' not in dict.keys() and 'fh' not in dict.keys():
                abb_storage = ruler.bank_ruler(dict)
            #存在分行或者支行，将全称划分为前后两段，前段是对应总行名字(类型是字典，因为要使用函数bank_rule生成简称)，
            #后段是分行名字(类型是字符串，直接放在生成的总行简称后即可)
            if 'zh' in dict.keys() or 'fh' in dict.keys():
                #将全称分为两个部分
                dict_bank_main = {}
                bank_branch = ''
                swicth = False
                for key,value in dict.items():
                    if swicth == False:
                        dict_bank_main[key] = value
                    if key == 'yh' or key =='gg' or key == 'yy':
                        swicth = True
                    if swicth == True and key != 'yh' or key !='gg' or key != 'yy':
                        bank_branch += value
                #对dict_bank_main使用使用函数bank_rule生成简称，直接加上后缀即可
                abb_storage = ruler.bank_ruler(dict_bank_main)
                abb_storage = {value + bank_branch for value in abb_storage.values()}
        #下面是对普通公司生成简称候选
        else:
            abb_storage = ruler.company_ruler(dict)
        # 最后对生成的简称进一步处理
        # 对于简称长度大于4产生长度等于4，长度等于3的两个简称候选。字典在迭代的时候不能改变大小。所以引入新字典。
        # -1键储存全称
        new_abb_storage = {}
        new_abb_storage[-1] = processed_word_dict[-1]
        rank = 0
        for value in abb_storage.values():
            new_abb_storage[rank] = value
            rank += 1
            if len(value) > 4:
                new_abb_storage[rank] = value[0:4]
                rank += 1
                new_abb_storage[rank] = value[0:3]
                rank += 1
        return new_abb_storage

class Test:
    # 目前定义以下几个函数
    # 函数test_all()是用来测试整体准确率的输入的文件是全称加简称对。
    # 函数test_full()是用来输入全称，输出预测的简称
    # 函数test_full_abb_single()，输入全称和简称，看其是否匹配
    # 函数test_abb()是用来匹配全称的，输入简称，输出匹配到的全称（这里可能涉及到两个全称有相同简称的问题，目前还没有遇到）
    def test_all(self, full_abb, abb_storge_flie = abb_storage_file, process_word_flie = processed_word_file):
        #统计参数如下：
        sum = 0
        right_num = 0
        right_list = []
        wrong_num = 0
        wrong_list = []
        #生成简称候选集
        full_abb_file = open(full_abb, 'r', encoding="utf-8")
        file_processed_word = open(processed_word_file, 'w', encoding='utf-8')
        file_abb_storage = open(abb_storage_file, 'w', encoding='utf-8')
        process = Process()
        ruler = Ruler()
        #读取每一行数据，前面是全称，后面是简称。对全程进行分词和规则处理，生成简称候选集，将简称与简称候选集进行比较。
        for i in range(1, len(full_abb_file.readlines()) + 1):
            sum += 1
            #提取简称
            tag_abb_name = linecache.getline(full_abb, lineno=i).split(" ")[1]
            tag_abb_name = tag_abb_name.strip()
            #提取全称并生成候选简称集
            full_name = linecache.getline(full_abb, lineno=i).split(" ")[0]
            processed_word = process.participle_single(full_name)
            project_abb_name_storage = ruler.ruler_single(processed_word)
            #将processed_word和project_abb_name_storage写入相应文件
            file_processed_word.writelines(str(processed_word) + '\n')
            file_abb_storage.writelines(str(project_abb_name_storage) + '\n')
            for value in project_abb_name_storage.values():
                if tag_abb_name == value:
                    right_num += 1
                    right_list.append(i)
                    break
                else:
                    wrong_num += 1
                    wrong_list.append(i)
        accuracy = right_num / sum
        #print(right_list)
        #print(wrong_list)
        print('总数为： ' + str(sum))
        print('预测正确的数目为： ' + str(right_num))
        print("正确率为" + str(accuracy))
    # 函数test_full()是用来输入全称，输出预测的简称
    def test_full(self):
        process = Process()
        ruler = Ruler()
        # 输入全称生成简称候选
        full_name_single = input("请输入企业全称: ")
        processed_word = process.participle_single(full_name_single)
        abb_storage = ruler.ruler_single(processed_word)
        print(abb_storage)
        return abb_storage
    # 函数test_full_abb_single()，输入全称和简称，看其是否匹配
    def test_full_abb_single(self):
        process = Process()
        ruler = Ruler()
        #输入全称生成简称候选
        full_name_single = input("请输入企业全称: ")
        processed_word = process.participle_single(full_name_single)
        abb_storage = ruler.ruler_single(processed_word)
        abb_name_single = input("请输入企业简称: ")
        result = False
        for value in abb_storage.values():
            if abb_name_single == value:
                result = True
                break
        if result == True:
            print("您输入的全称简称对是匹配的。")
        else:
            print("您输入的全称简称对是不匹配的。")
        return result
    # 函数test_abb()是用来匹配全称的，输入简称，输出匹配到的全称（这里可能涉及到两个全称有相同简称的问题,目前还没有遇到）
    def test_abb(self):
        tag_abb_name = input("请输入简称: ")
        #注意，简称库应该是生成好。
        tag_full_name = []
        result = False
        with open(abb_storage_file, 'r', encoding="utf-8") as f:
            for line in f.readlines():
                line = eval(line)
                for value in line.values():
                    if tag_abb_name == value:
                        result =True
                        tag_full_name.append(line[-1])
                        break
            if result ==True:
                print("您输入的简称在已有的全称库中，有匹配到的全称： ")
                print(tag_full_name)
            else:
                print("您输入的简称在已有的全称库中，没有匹配到的全称。")

if __name__ == '__main__': 
    test = Test()
    #test.test_all(full_abb_file)
    #test.test_full()
    #test.test_full_abb_single()
    test.test_abb()


