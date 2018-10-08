# -*- coding: utf-8 -*-
from MyUtils import read_file, write_file, eraseBletter
import csv, sys, os, json, copy, difflib, codecs, signal, time
import clang
import clang.cindex
from subprocess import Popen, PIPE
csv.field_size_limit(sys.maxsize)

meta_path = '/mnt/storage/falconlk/ast/'
repo_path = '/mnt/storage/falconlk/gitrepos/repositories/'
beaf_path = '/mnt/storage/falconlk/gitrepos/before_after/'

def printNode(cursor, depth):
    if depth==0:
        str_depth=""
    else:
        str_depth = "+" + ("--"*depth)

    print '%s"%s" {%s} [line=%s, col=%s, offset=%s, type=%s, access=%s, spelling=%s]' % \
          (str_depth, cursor.displayname, str(cursor.kind).split('.')[1], cursor.location.line, cursor.location.column, cursor.location.offset,
            str(cursor.type.kind).split('.')[1], str(cursor.access_specifier).split('.')[1], cursor.spelling)

def deepCopy(node):  # deepcopy 가 함수가 제공되는게 없으면, json 노드를 json 텍스트로 만들고, 그걸 다시 객체로 생성해라..
    json_str = json.dumps(node)
    tree = json.loads(json_str)
    return tree

def buildLinePosDict(file):
    contents = read_file(file)
    char = len(contents)
    line_endpos_dict = {}
    pos = 0
    maxline = len(contents.splitlines())
    print maxline

    for i, line in enumerate(contents.split('\n'), 1):
        if maxline < i:
            break
        if line == '':
            pos += 1
        else:
            pos += len(line) + 1
        print i, pos
        line_endpos_dict[i] = pos

    print char
    print pos

    return line_endpos_dict

def buildNode(cursor):
    node = {}
    node['name'] = cursor.spelling
    node['display'] = cursor.displayname
    node['line'] = cursor.location.line
    node['column'] = cursor.location.column
    node['offset'] = cursor.location.offset
    node['kind'] = str(cursor.kind).split('.')[1]
    node['type'] = str(cursor.type.kind).split('.')[1]
    node['access'] = str(cursor.access_specifier).split('.')[1]
    node['z_children'] = []
    return node

def jsonFileLoad(path):
    with open(path) as f:
        return json.load(f)

def jsonLineLoad(path):
    with open(path) as f:
        return json.loads(f)

def nodeTraversePrint(cursor, depth = 0): # Node traverse for printing
    printNode(cursor, depth)
    for c in cursor.get_children():
        nodeTraversePrint(c, depth + 1)

def nodeTraverseBuild(cursor, depth=0):
    node = buildNode(cursor)
    for child_cursor in cursor.get_children():
        child = nodeTraverseBuild(child_cursor, depth + 1)
        node['z_children'].append(child)
    return node

#getting {hunk: lines} dict using diff
def getDiffNew(user_repo_='', commit_hash='', prev_hash='', file_name=''):
    # base_path = '/Users/Falcon/Desktop/'
    # user_repo_ = 'opencv_opencv'
    # commit_hash = '70fed019ae4f78582d0ab17a38688e8bce409f21'
    # prev_hash = 'c7db1c1cc81083eb5c5ccf3111486cfaa9aae202'
    # file_name = '3rdparty/libjasper/jpc_cs.c'

    each_repo_path = repo_path + user_repo_

    st = """cd %s && git diff %s:%s %s:%s | gawk 'match($0,"^@@ -([0-9]+),[0-9]+ [+]([0-9]+),[0-9]+ @@",a){left=a[1];right=a[2];next} /^(---|\+\+\+|[^-+ ])/{print;next}; {line=substr($0,2)}; /^-/{print "-" left++ ":" line;next}; /^[+]/{print "+" right++ ":" line;next}; {print "(" left++ "," right++ "):"line}' | grep -v '^+++' | grep -v '^---' | grep -v 'diff' | grep -v 'index'""" % (each_repo_path, prev_hash, file_name, commit_hash, file_name)
    print (st)
    p = Popen(st, shell=True, stdout=PIPE)
    commits = p.communicate()[0]

    lines = []
    # commits = eraseBletter(commits)
    for i in commits.split('\n'):
        if i.startswith('('):
            line_number = i.split(',')[0].split('(')[1]
            lines.append(line_number)
        if i.startswith('-'):
            line_number = i.split(':')[0].split('-')[1]
            lines.append(line_number)

    # lines = [1, 2, 3, 712, 713, 714, 1330, 1331]

    hunk_lines_dict = {}
    temp = []
    j = 0
    for i in range(len(lines)):
        temp.append(lines[i])
        if i == len(lines)-1:
            j += 1
            hunk_lines_dict[j] = str(temp[0]) + '..' + str(temp[-1])
            break
        if not ((int(lines[i+1]) - int(lines[i])) == 1):
            j += 1
            hunk_lines_dict[j] = str(temp[0]) + '..' + str(temp[-1])
            temp = []
    return hunk_lines_dict

def delExceptTargets(node, hunk_start_pos, hunk_end_pos, line_endpos_dict):  #target_pos 들은 line의 시작점들
    i = 0
    j = 0
    num_children = len(node['z_children'])
    while j < num_children:  #0과 1이 남았는데, i 가 1이 되었는데, 1을 지웠으면 에러.
        j += 1
        print j
        flag = 0    #list 가 안줄었으면 flag 를 통해 i를 증가시켜야 함.

        if len(node['z_children']) > 0:   #i 에 더이상 남아있지 않을때?? index error
            child_node_start_pos = int(node['z_children'][i]['offset'])
            child_node_end_pos = int(line_endpos_dict[node['z_children'][i]['line']]) # 현재 노드가 있는 라인의 끝 포지션 = child_node_end_pos 로 할당하자.
            if hunk_start_pos > child_node_end_pos:
                del node['z_children'][i]
                flag = 1
            if hunk_end_pos < child_node_start_pos:
                del node['z_children'][i]
                flag = 1
            if flag == 0:
                i += 1

    for child in node['z_children']:
        result = delExceptTargets(child, hunk_start_pos, hunk_end_pos, line_endpos_dict)
        if result is not None:
            return result
    return None

def getTarget(node, line_start_pos, line_end_pos):
    # node_start_pos = int(node['pos'])
    # node_end_pos = int(node['pos']) + int(node['length'])

    for i in node['z_children']:
        if len(node['z_children']) > 1:
            return node

    for child in node['z_children']:
        result = getTarget(child, line_start_pos, line_end_pos)
        if result is not None:
            return result

# def clearPath(path):
#     for dir, sub_dirs, files in os.walk(path, topdown=False):
#         if not files:
#             print("no files at this level")
#             return
#         else:
#             for file in files:
#                 os.remove(file)
#
    # with Popen('cd %s && rm check.txt Index_2_revised.csv *.html' % path, shell=True, stdout=PIPE, preexec_fn=os.setsid) as process:
    #     try:
    #         commits = process.communicate()[0]
    #     except :
    #         commits = process.communicate()[0]

if __name__ == "__main__":
    clang.cindex.Config.set_library_file('/usr/lib/x86_64-linux-gnu/libclang-6.0.so')
    index = clang.cindex.Index.create()

    if not os.path.isdir(meta_path):
        os.mkdir(meta_path, 0755)

    # clearPath(meta_path)
    success_count = 0

    # Index_2 에서 file_hash, commit_hash, user_repo, file_name 정보 얻어서 진행
    index_1 = beaf_path + 'Index_1.csv'
    index_2 = beaf_path + 'Index_2.csv'

    f = open(meta_path + 'Index_2_revised.csv', 'a')
    wr = csv.writer(f)

    ifile = open(index_2, 'rt')
    read = csv.reader(ifile)
    for row in read:    # File hash 1개 (file hash 1개) 별로 loop 돌기 때문에, before 와 after 전부 처리해주어야 함.
        print('=======================================')
        file_hash = str(row[0]).strip()
        print('File hash: ', file_hash)
        commit_hash = str(row[1]).strip()
        print('Commit hash: ', commit_hash)
        user_repo = str(row[2]).strip()
        user_repo_ = user_repo.split('/')[0] + "_" + user_repo.split('/')[1]
        print('User / Repo: ', user_repo)
        file_name = str(row[3]).strip()
        print('File name: ', file_name)
        file_hash_string = str(row[4]).strip()
        print('File hash string: ', file_hash_string)
        print()

        sub_before_path = user_repo_ + '/' + commit_hash + '/' + file_hash + '/' + 'before.%s' % (file_name.split('/')[-1].split('.')[-1])
        sub_after_path = user_repo_ + '/' + commit_hash + '/' + file_hash + '/' + 'after.%s' % (file_name.split('/')[-1].split('.')[-1])

        before_file_path = beaf_path + 'results/' + sub_before_path
        after_file_path = beaf_path + 'results/' + sub_after_path
        print(before_file_path)
        print(after_file_path)
        print()

        # Index 2 revising with file existence status
        if not os.path.exists(before_file_path) and not os.path.exists(after_file_path):
            write_file(meta_path + 'check.txt', 'X.X')
            wr.writerow([file_hash, commit_hash, user_repo, file_name, file_hash_string, 'X.X'])
        elif os.path.exists(before_file_path) and not os.path.exists(after_file_path):
            write_file(meta_path + 'check.txt', 'O.X')
            wr.writerow([file_hash, commit_hash, user_repo, file_name, file_hash_string, 'O.X'])
        elif not os.path.exists(before_file_path) and os.path.exists(after_file_path):
            write_file(meta_path + 'check.txt', 'X.O')
            wr.writerow([file_hash, commit_hash, user_repo, file_name, file_hash_string, 'X.O'])
        elif os.path.exists(before_file_path) and os.path.exists(after_file_path):
            write_file(meta_path + 'check.txt', 'O.O')
            wr.writerow([file_hash, commit_hash, user_repo, file_name, file_hash_string, 'O.O'])

        #####TODO: CPP (srcML) 추가 전까지는 제외
        if file_name.split('/')[-1].split('.')[1] == 'cpp':
            continue

        # git diff 를 쓰기로 바꿨기 때문에, previous hash 도 필요하다. Index 1 도 사용.
        index1 = open(index_1, "rt")
        index_1_read = csv.reader(index1)
        prev_hash = ''
        for r in index_1_read:
            if str(r[1]) == commit_hash:
                prev_hash = str(r[5])
                break
        if not commit_hash or not prev_hash or not file_name:
            write_file(meta_path + 'Failed.txt', file_hash + '\n' + commit_hash + '\n' + user_repo + '\n' + file_name + '\n=============================')
            print("Failed to get previous hash for ...Commit: %s /// File: %s" % (commit_hash, file_hash))
            continue


        success_count += 1

        # {hunk: lines} dict 생성 (한 파일 당, 분산된 여러 hunk 가 있을 수 있음.)
        hunk_num = 0
        hunk_lines_dict = {}

        # diff 정보 가져오기
        # hunk_lines_dict
        # h[1]:63..74 // 63, 64, 65, ... , 74
        # h[2]:78..89 //
        hunk_lines_dict = getDiffNew(user_repo_, commit_hash, prev_hash, file_name)
        if hunk_lines_dict is None:
            print("Failed to get the diff for ...Commit: %s /// File: %s" % (commit_hash, file_hash))
            continue

        # 2개의 파일을 받아서 [변경된 라인 번호] + [각 라인 별 Position range] 얻기
        before = read_file(before_file_path)
        after = read_file(after_file_path)

        # {line: position} dict 생성 (한 라인 당, position)
        f_pos_1 = 0
        f_pos_2 = 0
        f_init_line_num = 0
        line_positions_dict = {}
        for i in before.split('\n'):
            f_init_line_num += 1
            f_pos_2 = f_pos_1 + i.__len__()

            # line_positions_dict
            # l[0]:0..12
            # l[1]:13..21
            line_positions_dict[f_init_line_num] = str(f_pos_1) + ".." + str(f_pos_2)
            f_pos_1 += i.__len__() + 1  # \n char + 1

        # {hunk: position} dict 생성 (한 hunk 단위로 position 을 모아서..)
        hunk_positions_dict = {}
        for key, value in hunk_lines_dict.items():
            start_l = value.split('..')[0]
            end_l = value.split('..')[1]
            start_p = line_positions_dict[int(start_l)].split('..')[0]
            end_p = line_positions_dict[int(end_l)].split('..')[1]

            # hunk_positions_dict
            # hp[0]:401..627
            hunk_positions_dict[key] = start_p + '..' + end_p


        line_endpos_dict = buildLinePosDict(before_file_path)


        if before_file_path.split('.')[-1] == 'cpp':    # C++ 의 경우 clang++ 로 파싱해야함.
            translation_unit = index.parse(before_file_path, ['-x', 'c++', '-std=c++11', '-D__CODE_GENERATOR__'])
        elif before_file_path.split('.')[-1] == 'c':
            translation_unit = index.parse(before_file_path)
        elif before_file_path.split('.')[-1] == 'h':    #TODO: .h 파일의 경우 처리를 따로 해야함.
            pass
        else:   #cc file
            translation_unit = index.parse(before_file_path, ['-x', 'c++', '-std=c++11', '-D__CODE_GENERATOR__'])

        node = nodeTraverseBuild(translation_unit.cursor)
        json_path = '/'.join(before_file_path.split('/')[:-1]) + '/' + before_file_path.split('/')[-1].split('.')[0] + '.json'
        write_file(json_path, json.dumps(node, sort_keys=True, indent=4))

        # json load
        print json_path
        tree_before = jsonFileLoad(json_path)

        # getting target nodes
        rep_nodes = []
        for key, value in hunk_positions_dict.items():
            dpnode = deepCopy(tree_before)  # node deepcopy
            start_p = value.split('..')[0]
            end_p = value.split('..')[1]
            delExceptTargets(dpnode, int(start_p), int(end_p), line_endpos_dict)
            rep_nodes.append(getTarget(dpnode, int(start_p), int(end_p)))

        if not len(rep_nodes):
            print("Failed to find any node...")
        else:
            for i in rep_nodes:
                print('\n--- Node briefing ---')
                print('Spelling: ', i['spelling'])
                print('Displayname: ', i['displayname'])
                print('Line: ', i['line'])
                print('Column: ', i['column'])
                print('Offset: ', i['offset'])
                print('Kind: ', i['kind'])
                print('Type: ', i['type'])
                print('Specifier: ', i['access'])
        print('break point')