# -*- coding: utf-8 -*-


'''AST Pasring using Gumtree and Cgum'''
#
from MyUtils import read_file, write_file, eraseBletter
import csv, sys, os, json, copy, difflib, codecs, signal, time
from subprocess import Popen, PIPE, TimeoutExpired, run, call
csv.field_size_limit(sys.maxsize)

meta_path = '/mnt/storage/falconlk/ast/'
repo_path = '/mnt/storage/falconlk/gitrepos/repositories/'
beaf_path = '/mnt/storage/falconlk/gitrepos/before_after/'

def read_file_by_list(file_path):
    with codecs.open(file_path, "r", encoding='utf-8') as file:
        return file.readlines()

def stripFile(file):
    return read_file(file).strip()

def getFileDiffByLine(lines1, lines2):
    diff = ''

    # diffs = difflib.unified_diff(lines1, lines2, n=0)
    # diffText = ''.join(line for line in diffs)
    # print (diffText)

    for line in difflib.unified_diff(lines1, lines2, fromfile='file1', tofile='file2', lineterm='', n=0):
        diff += line.strip()+'\n'
    print(diff)
    return diff

def queryGit(target_repo, commit_hash):
    with Popen("cd %s && git log -2 %s | grep 'commit' | uniq" % (target_repo, commit_hash), shell=True, stdout=PIPE,
               preexec_fn=os.setsid) as process:
        try:
            commits = process.communicate(timeout=1000)[0]
        except TimeoutExpired:
            os.killpg(process.pid, signal.SIGINT)  # send signal to the process group
            commits = process.communicate()[0]
    commits = eraseBletter(commits)

def gumtree(src_path):
    dest_path = '/'.join(src_path.split('/')[:-1]) + '/' + src_path.split('/')[-1].split('.')[0] + '.json'

    # st = "/mnt/storage/falconlk/cgum/cgum parse %s > %s" % (src_path, dest_path)
    if os.path.exists(src_path):
        st = "/mnt/storage/falconlk/gumtree/dist/build/distributions/gumtree/bin/gumtree parse %s > %s" % (src_path, dest_path)
        my_env = os.environ.copy()
        my_env["PATH"] = "/home/falconlk/.linuxbrew/bin:/home/falconlk/.linuxbrew/sbin:/mnt/storage/falconlk/gumtree/dist/build/distributions/gumtree/bin:/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games:/usr/lib/jvm/java-8-oracle/bin:/usr/lib/jvm/java-8-oracle/db/bin:/usr/lib/jvm/java-8-oracle/jre/bin:/opt/dell/srvadmin/bin:/mnt/storage/falconlk/cgum" + my_env["PATH"]
        Popen(st, env=my_env, shell=True)
    else:
        write_file(meta_path + 'no_before_file_error.txt', src_path)
    return dest_path

def cgum(src_path, file_hash, success_count):
    dest_path = meta_path + str(success_count) + '_' + file_hash + '.html'
    if os.path.exists(src_path):
        st = "/mnt/storage/falconlk/cgum/cgum parse %s > %s" % (src_path, dest_path)
        my_env = os.environ.copy()
        my_env[
            "PATH"] = "/home/falconlk/.linuxbrew/bin:/home/falconlk/.linuxbrew/sbin:/mnt/storage/falconlk/gumtree/dist/build/distributions/gumtree/bin:/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games:/usr/lib/jvm/java-8-oracle/bin:/usr/lib/jvm/java-8-oracle/db/bin:/usr/lib/jvm/java-8-oracle/jre/bin:/opt/dell/srvadmin/bin:/mnt/storage/falconlk/cgum" + \
                      my_env["PATH"]
        Popen(st, env=my_env, shell=True)
    else:
        write_file(meta_path + 'no_before_file_forCgum.txt', src_path)
    return dest_path

def getEveryNodes(results, node, pos_1, pos_2):  # Position range 내의 모든 node 들 가져오기
    if int(node['pos']) >= int(pos_1) and int(node['pos']) <= int(pos_2):
        results.append(node)

    for child in node['children']:
        result = getEveryNodes(results, child, pos_1, pos_2)
        if result is False:
            break
    return

def getRepreNode(results, node, pos_1, pos_2):  # Position range 내의 대표 노드 1개 "results 에 넣기" (중복 position 무시)
    if int(node['pos']) >= int(pos_1) and int(node['pos']) <= int(pos_2):
        results.append(node)
        return
    for child in node['children']:
        result = getRepreNode(results, child, pos_1, pos_2)
        if result is False:
            break

def getTargetNode_Fail(node, pos_1, pos_2, mini=1000000000):  # Position range 내의 대표 노드 1개 "리턴" (중복되면 가장 안쪽의 노드 가져오기)
    if int(node['pos']) >= int(pos_1) and int(node['pos']) <= int(pos_2):
        if int(node['pos']) > int(mini) or len(node['children']) == 0:  # and node['children'] is not int(node['pos']):
            return None  # 끝낼 시점..

        for child in node['children']:
            result = getTargetNode(child, pos_1, pos_2,
                                   mini=node['pos'])  # Range 에 맞으면 일단 저장해놓고 그 숫자를 인자로 줘서 (Minimum 찾기)
            if result is None:
                return node

    for child in node['children']:
        result = getTargetNode(child, pos_1, pos_2, mini=node['pos'])
        if result is not None:
            return result  # result는 node 이거나 None 이거나..

    return None  # 다 돌고도 못찾은 경우..



def getTargetNode(node, pos_1, pos_2):  # Position range 내의 대표 노드 1개 "리턴" (중복되면 가장 안쪽의 노드 가져오기)
    start = int(node['pos'])
    end = int(node['pos']) + int(node['length'])

    # s <= p1 <= e : step into
    if start <= pos_1 and pos_1 <= end:
        for child in node['children']:
            result = getTargetNode(child, pos_1, pos_2)
            if result is not None:
                return result

    # e < p1 : return None
    if end < pos_1:
        return None

    # s > p2 : return None
    # s >= p1 : return node [자식을 봐야한다..]
    if start >= pos_1:
        mini = node['pos']
        xnode = node
        while (len(xnode['children']) > 0 and xnode['children'][0]['pos'] == mini):
            xnode = xnode['children'][0]
        return xnode

def checkNodeRange(node, pos_1, pos_2):
    start = int(node['pos'])
    end = int(node['pos']) + int(node['length'])

    # s <= p1 <= e : step into
    if start <= pos_1 and pos_1 <= end:
        for child in node['children']:
            result = checkNodeRange(child, pos_1, pos_2)
            if result is not None:
                return result

    # e < p1 : return None
    if end < pos_1:
        return None

    # s > p2 : return None
    # s >= p1 : return node [자식을 봐야한다..]
    if start >= pos_1:
        mini = node['pos']
        xnode = node
        while (len(xnode['children']) > 0 and xnode['children'][0]['pos'] == mini):
            xnode = xnode['children'][0]
        return xnode

def deepCopy(node):  # deepcopy 가 함수가 제공되는게 없으면, json 노드를 json 텍스트로 만들고, 그걸 다시 객체로 생성해라..
    json_str = json.dumps(node)
    tree = json.loads(json_str)
    return tree

def deepCopyLib(node):
    tree = copy.deepcopy(node)
    return tree

def printNode(node):
    print()
    print(node['type'])
    print(node['typeLabel'])
    print(node['pos'])
    print(node['length'])
    print(node.__len__())
    print()

def travelNodes(node):
    for child in node['children']:
        print()
        print(child['type'])
        print(child['typeLabel'])
        print(child['pos'])
        print(child['length'])
        print(child.__len__())
        print()

        result = travelNodes(child)
        if result is False:
            print('End point..')

def jsonFileLoad(path):
    with open(path) as f:
        return json.load(f)

def jsonLineLoad(path):
    with open(path) as f:
        return json.loads(f)

def sortNodes(node):
    pass

def charCounter(st):
    count = 0
    for _ in read_file(st): count += 1
    return count


#getting {hunk: lines} dict using diff
def getDiffNew(user_repo_='', commit_hash='', prev_hash='', file_name=''):
    # base_path = '/Users/Falcon/Desktop/'
    # user_repo_ = 'opencv_opencv'
    # commit_hash = '70fed019ae4f78582d0ab17a38688e8bce409f21'
    # prev_hash = 'c7db1c1cc81083eb5c5ccf3111486cfaa9aae202'
    # file_name = '3rdparty/libjasper/jpc_cs.c'

    each_repo_path = repo_path + user_repo_
    st = """cd %s && git diff %s:%s %s:%s | gawk 'match($0,"^@@ -([0-9]+),[0-9]+ [+]([0-9]+),[0-9]+ @@",a){left=a[1];right=a[2];next} /^(---|\+\+\+|[^-+ ])/{print;next}; {line=substr($0,2)}; /^-/{print "-" left++ ":" line;next}; /^[+]/{print "+" right++ ":" line;next}; {print "(" left++ "," right++ "):"line}' | grep -v '^+++' | grep -v '^---' | grep -v 'diff' | grep -v 'index'""" % (each_repo_path, prev_hash, file_name, commit_hash, file_name)
    with Popen(st, shell=True, stdout=PIPE, preexec_fn=os.setsid) as process:
        try:
            commits = process.communicate(timeout=100)[0]
        except TimeoutExpired:
            os.killpg(process.pid, signal.SIGINT)  # send signal to the process group
            commits = process.communicate()[0]

    lines = []
    commits = eraseBletter(commits)
    for i in commits.split('\\n'):
        if i.startswith('('):
            line_number = i.split(',')[0].split('(')[1]
            lines.append(line_number)
        if i.startswith('-'):
            line_number = i.split(':')[0].split('-')[1]
            lines.append(line_number)

    for i in commits.split('\\n'):
        print(i)
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

def delExceptTargets(node, line_start_pos, line_end_pos):  #target_pos 들은 line의 시작점들
    # node_start_pos = int(node['pos'])
    # node_end_pos = int(node['pos']) + int(node['length'])

    i = 0
    j = 0
    num_children = len(node['children'])
    while j < num_children:  #0과 1이 남았는데, i 가 1이 되었는데, 1을 지웠으면 에러
        j += 1
        flag = 0    #list 가 안줄었으면 flag 를 통해 i를 증가시켜야 함.
        child_node_start_pos = int(node['children'][i]['pos'])
        child_node_end_pos = int(node['children'][i]['pos']) + int(node['children'][i]['length'])
        if line_start_pos > child_node_end_pos:
            del node['children'][i]
            flag = 1
        if line_end_pos < child_node_start_pos:
            del node['children'][i]
            flag = 1
        if flag == 0:
            i += 1

    # for child in node['children']:
    #     child_node_start_pos = int(child['pos'])
    #     child_node_end_pos = int(child['pos']) + int(child['length'])

    for child in node['children']:
        result = delExceptTargets(child, line_start_pos, line_end_pos)
        if result is not None:
            return result
    return None

def getTarget(node, line_start_pos, line_end_pos):
    # node_start_pos = int(node['pos'])
    # node_end_pos = int(node['pos']) + int(node['length'])

    for i in node['children']:
        if len(node['children']) > 1:
            return node

    for child in node['children']:
        result = getTarget(child, line_start_pos, line_end_pos)
        if result is not None:
            return result

def getBeforeStartAndIncludeEnd(node, line_start_pos, line_end_pos):  #target_pos 들은 line의 시작점들
    node_start_pos = int(node['pos'])
    node_end_pos = int(node['pos']) + int(node['length'])

    # 종료조건 1: target 라인의 첫번째 position 이 0으로 시작되면 어차피 root 를 다 통틀어야 한다.
    # 종료조건 2: target 라인의 첫번째 position 보다 현재 노드의 position 이 커야 하며,
    # 동시에 target 라인의 마지막 position 보다 현재 노드의 position 이 작아야 한다.

    # if line_start_pos > node_start_pos:
    #     return None
    # if line_end_pos > node_end_pos:
    #     return None

    # 종료조건 1
    if line_start_pos == 0:
        return node

    # 현재 node 가 target range (lines) 에 속하는 순간 (직후면 좋음).
    if line_start_pos <= node_start_pos: # Candidate
        if line_end_pos <= node_end_pos:
            # 종료조건 2
            return node
        else:
            for child in node['children']:
                result = getBeforeStartAndIncludeEnd(child, line_start_pos, line_end_pos)
                if result is not None:
                    return result

    else:   # 아무런 조건에 해당되지 않는다면 그냥 밑으로 들어가서 탐색.
        for child in node['children']:
            result = getBeforeStartAndIncludeEnd(child, line_start_pos, line_end_pos)
            if result is not None:
                return result

    return None # 찾지 못했을 경우.

def clearPath(path):
    with Popen('cd %s && rm check.txt Index_2_revised.csv *.html' % path, shell=True, stdout=PIPE, preexec_fn=os.setsid) as process:
        try:
            commits = process.communicate(timeout=100)[0]
        except TimeoutExpired:
            os.killpg(process.pid, signal.SIGINT)  # send signal to the process group
            commits = process.communicate()[0]

if __name__ == "__main__":
    clearPath(meta_path)
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

        # gumtree 를 사용하여 parsed json file 을 얻어냄
        before_json_file_path = gumtree(before_file_path)
        time.sleep(5)

        ############ logging for examples
        cgum(before_file_path, file_hash, success_count)
        time.sleep(5)

        # json load
        tree_before = jsonFileLoad(before_json_file_path)

        # getting target nodes
        rep_nodes = []
        for key, value in hunk_positions_dict.items():
            dpnode = deepCopy(tree_before)  # node deepcopy
            start_p = value.split('..')[0]
            end_p = value.split('..')[1]
            delExceptTargets(dpnode['root'], int(start_p), int(end_p))
            rep_nodes.append(getTarget(dpnode['root'], int(start_p), int(end_p)))



        if not len(rep_nodes):
            print("Failed to find any node...")
        else:
            for i in rep_nodes:
                ############ logging for examples
                print('\n--- Node briefing ---')
                print('Position: ', i['pos'])
                print('TypeLable: ', i['typeLabel'])
                print('Type: ', i['type'])
                print('Length: ', i['length'])

        print('break point')


        # print('==========================================')
        # for key, value in hunk_lines_dict.iteritems():
        #     f_pos_1 = line_dict[i].split('..')[0]
        #     f_pos_2 = line_dict[i].split('..')[1]
        #     target_node = getTargetNode(node['root'], int(f_pos_1), int(f_pos_2))
        #
        #     clone_node = deepCopy(target_node)  # File 내에 여러 라인이 산발적으로 바뀌었을때..
        #     clone_node = deleteNodes(clone_node, 90)  # TODO: 끝 pos 에서 트리 끊어주기.
        #

        # hunk 들의 start, end position 가져오기




    # f.close()

