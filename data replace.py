import re
import openpyxl
import pandas as pd

# 本方法基于正则匹配来替换C和C++中的自定义函数名和变量名


# 全局变量
# 关键词的集合  对应的版本为C11和C++17 (不可变集)
keywords = frozenset({'__asm', '__builtin', '__cdecl', '__declspec', '__except', '__export', '__far16', '__far32',
                      '__fastcall', '__finally', '__import', '__inline', '__int16', '__int32', '__int64', '__int8',
                      '__leave', '__optlink', '__packed', '__pascal', '__stdcall', '__system', '__thread', '__try',
                      '__unaligned', '_asm', '_Builtin', '_Cdecl', '_declspec', '_except', '_Export', '_Far16',
                      '_Far32', '_Fastcall', '_finally', '_Import', '_inline', '_int16', '_int32', '_int64',
                      '_int8', '_leave', '_Optlink', '_Packed', '_Pascal', '_stdcall', '_System', '_try', 'alignas',
                      'alignof', 'and', 'and_eq', 'asm', 'auto', 'bitand', 'bitor', 'bool', 'break', 'case',
                      'catch', 'char', 'char16_t', 'char32_t', 'class', 'compl', 'const', 'const_cast', 'constexpr',
                      'continue', 'decltype', 'default', 'delete', 'do', 'double', 'dynamic_cast', 'else', 'enum',
                      'explicit', 'export', 'extern', 'false', 'final', 'float', 'for', 'friend', 'goto', 'if',
                      'inline', 'int', 'long', 'mutable', 'namespace', 'new', 'noexcept', 'not', 'not_eq', 'nullptr',
                      'operator', 'or', 'or_eq', 'override', 'private', 'protected', 'public', 'register',
                      'reinterpret_cast', 'return', 'short', 'signed', 'sizeof', 'static', 'static_assert',
                      'static_cast', 'struct', 'switch', 'template', 'this', 'thread_local', 'throw', 'true', 'try',
                      'typedef', 'typeid', 'typename', 'union', 'unsigned', 'using', 'virtual', 'void', 'volatile',
                      'wchar_t', 'while', 'xor', 'xor_eq', 'NULL'})
# 保存已知的非用户定义函数 (不可变集)
main_set = frozenset({'main'})
# 主函数当中的参数(不可变集)
main_args = frozenset({'argc', 'argv'})

# 输入的形式是以字符串为元素的列表
def clean_gadget(gadget):
    # 创建字典；将函数名映射到符号名+数字
    fun_symbols = {}
    # 创建字典；将变量名映射到符号名+数字
    var_symbols = {}

    # 函数数量计数
    fun_count = 1
    # 变量数量计数
    var_count = 1

    # 正则匹配找到多行的注释
    rx_comment = re.compile('\*/\s*$')
    # 正则匹配 找到用户自定义的那些函数名
    rx_fun = re.compile(r'\b([_A-Za-z]\w*)\b(?=\s*\()')
    # 正则匹配 找到用户自定义的那些变量名
    # rx_var = re.compile(r'\b([_A-Za-z]\w*)\b(?!\s*\()')
    rx_var = re.compile(r'\b([_A-Za-z]\w*)\b(?:(?=\s*\w+\()|(?!\s*\w+))(?!\s*\()')

    # 最终返回到界面
    cleaned_gadget = []

    for line in gadget:
        # 判断是不是标题行和注释行 如果不是，则进行处理
        if rx_comment.search(line) is None:
            # 移除所有字符串文字(保留引号)
            nostrlit_line = re.sub(r'".*?"', '""', line)
            # 移除所有字符文字
            nocharlit_line = re.sub(r"'.*?'", "''", nostrlit_line)
            # 用空字符串替换任何非ASCII字符
            ascii_line = re.sub(r'[^\x00-\x7f]', r'', nocharlit_line)

            # 按顺序返回字符串列表中的所有正则表达式匹配项；保留语义顺序
            user_fun = rx_fun.findall(ascii_line)
            user_var = rx_var.findall(ascii_line)

            # Could easily make a "clean gadget" type class to prevent duplicate functionality
            # of creating/comparing symbol names for functions and variables in much the same way.
            # The comparison frozenset, symbol dictionaries, and counters would be class scope.
            # So would only need to pass a string list and a string literal for symbol names to
            # another function.
            for fun_name in user_fun:
                if len({fun_name}.difference(main_set)) != 0 and len({fun_name}.difference(keywords)) != 0:
                    # DEBUG
                    # print('comparing ' + str(fun_name + ' to ' + str(main_set)))
                    # print(fun_name + ' diff len from main is ' + str(len({fun_name}.difference(main_set))))
                    # print('comparing ' + str(fun_name + ' to ' + str(keywords)))
                    # print(fun_name + ' diff len from keywords is ' + str(len({fun_name}.difference(keywords))))
                    ###
                    # 看函数名是否已经在已替换的字典里面了
                    if fun_name not in fun_symbols.keys():
                        fun_symbols[fun_name] = 'FUN' + str(fun_count)
                        fun_count += 1
                    # 确保只替换函数名(没有相同的变量名)
                    ascii_line = re.sub(r'\b(' + fun_name + r')\b(?=\s*\()', fun_symbols[fun_name], ascii_line)

            for var_name in user_var:
                # 下一行是fun_name和var_name之间的细微差别
                if len({var_name}.difference(keywords)) != 0 and len({var_name}.difference(main_args)) != 0:
                    # DEBUG
                    # print('comparing ' + str(var_name + ' to ' + str(keywords)))
                    # print(var_name + ' diff len from keywords is ' + str(len({var_name}.difference(keywords))))
                    # print('comparing ' + str(var_name + ' to ' + str(main_args)))
                    # print(var_name + ' diff len from main args is ' + str(len({var_name}.difference(main_args))))
                    ###
                    # 看变量名是否已经在已替换的字典里了
                    if var_name not in var_symbols.keys():
                        var_symbols[var_name] = 'VAR' + str(var_count)
                        var_count += 1
                    # 确保只替换变量名(没有相同的函数名)
                    ascii_line = re.sub(r'\b(' + var_name + r')\b(?:(?=\s*\w+\()|(?!\s*\w+))(?!\s*\()', \
                                        var_symbols[var_name], ascii_line)

            cleaned_gadget.append(ascii_line)
    # 返回替换后的列表
    return cleaned_gadget

if __name__ == '__main__':
    workbook = openpyxl.load_workbook('input.xlsx')
    sheet = workbook['工作表1']
    p_list = []
    for i in range(2, 38):
        cell_i_3 = sheet.cell(row=i,column=3).value
        p_list.append(cell_i_3)
    standard = clean_gadget(p_list)
    print(standard)
    # 将列表写进csv文件 标签为standardization(标准化)
    file = pd.DataFrame({'standardization': standard})
    file.to_csv("standardization.csv",index=False,sep=',')
