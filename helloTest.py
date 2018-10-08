# -*- coding: utf-8 -*-
from MyUtils import read_file, write_file, eraseBletter
import csv, sys, os, json, copy, difflib, codecs, signal
from subprocess import Popen, PIPE, TimeoutExpired, run, call
csv.field_size_limit(sys.maxsize)

meta_path = '/mnt/storage/falconlk/'

def read_file_by_list(file_path):
    with codecs.open(file_path, "r", encoding='utf-8') as file:
        return file.readlines()

def getFileDiffByLine(lines1, lines2):
    diff = ''

    # diffs = difflib.unified_diff(lines1, lines2, n=0)
    # diffText = ''.join(line for line in diffs)
    # print (diffText)

    for line in difflib.unified_diff(lines1, lines2, fromfile='file1', tofile='file2', lineterm='', n=0):
        diff += line.strip()+'\n'
    print(diff)
    return diff

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

def deepCopy(node):  # deepcopy 가 함수가 제공되는게 없으면, json 노드를 json 텍스트로 만들고, 그걸 다시 객체로 생성해라..
    json_str = json.dumps(node)
    tree = json.loads(json_str)
    return tree

def jsonFileLoad(path):
    with open(path) as f:
        return json.load(f)

def getBeforeStartAndIncludeEnd(node, line_start_pos, line_end_pos):  #target_pos 들은 line의 시작점들
    # 종료조건 1: target 라인의 첫번째 position 이 0으로 시작되면 어차피 root 를 다 통틀어야 한다.
    # 종료조건 2: target 라인의 첫번째 position 보다 현재 노드의 position 이 커야 하며,
    # 동시에 target 라인의 마지막 position 보다 현재 노드의 position 이 작아야 한다.

    node_start_pos = int(node['pos'])
    node_end_pos = int(node['pos']) + int(node['length'])

    # 종료조건 1
    if line_start_pos == 0:
        return node

    # 현재 node 가 target range (lines) 에 속하는 순간 (직후면 좋음).
    if line_start_pos <= node_start_pos: # Candidate
        if line_end_pos <= node_end_pos:
            # 타겟 라인 포지션 123..152 은 현 노드 포지션 124..152 에 포함 //
            # 하지만 라인 포지션 123..152 와 현 노드 포지션 124..148 의 가능성은??
            # 다 돌고나서도 못찾았다.. 그럼 루트를 넘겨야 하나?

            # 종료조건 2
            return node
        else:
            for child in node['children']:
                if node_end_pos < line_start_pos:  # 현 노드의 end position 이 라인 포지션의 범위 안에도 못들었으면 그냥 올라가서 다른 자식 탐색
                    return None
                result = getBeforeStartAndIncludeEnd(child, line_start_pos, line_end_pos)
                if result is not None:
                    return result

    else:   # 아무런 조건에 해당되지 않는다면 그냥 밑으로 들어가서 탐색.
        for child in node['children']:
            if node_end_pos < line_start_pos:   # 현 노드의 end position 이 라인 포지션의 범위 안에도 못들었으면 그냥 올라가서 다른 자식 탐색
                return None
            result = getBeforeStartAndIncludeEnd(child, line_start_pos, line_end_pos)
            if result is not None:
                return result

    return None # 찾지 못했을 경우.


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


def test():
    before_file_path = '/mnt/storage/falconlk/hello.c'
    # before_file_path = '/Users/Falcon/Desktop/Vulnerability/gumtree/test/before.c'
    after_file_path = '/mnt/storage/falconlk/hello_.c'
    # after_file_path = '/Users/Falcon/Desktop/Vulnerability/gumtree/test/after.c'
    # 2개의 파일을 받아서 [변경된 라인 번호] + [각 라인 별 Position range] 얻기

    lines_1 = read_file_by_list(before_file_path)
    lines_2 = read_file_by_list(after_file_path)

    # diff 정보 가져오기
    diff = getFileDiffByLine(lines_1, lines_2)
    if diff == '':
        sys.exit()

    # hunk lines dict 생성 (한 파일 당, 분산된 여러 hunk 가 있을 수 있음.)
    hunk_num = 0
    hunk_lines_dict = {}
    for diff_line in diff.split('\n'):
        if diff_line.startswith('@@'):
            hunk_num += 1
            start_line = int((diff_line.split(' ')[1].split(',')[0])[1:])  # start line per each hunk

            if ',' in diff_line.split(' ')[1]:
                plus_line = int(diff_line.split(' ')[1].split(',')[1]) -1   # plus line per each hunk

            else:
                plus_line = 0  # plus line per each hunk

            end_line = int(start_line) + int(plus_line)  # end line per each hunk
            print("Start line: ", start_line, "/// Plus line: ", plus_line, "/// End line: ", end_line)

            # hunk_lines_dict
            # h[1]:63..74 // 63, 64, 65, ... , 74
            # h[2]:78..89 //
            hunk_lines_dict[hunk_num] = str(start_line) + ".." + str(
                int(start_line) + int(plus_line))  # 각 파일별로 변경된 라인들의 list 가 도출

    # line position dict 생성 (한 라인 당, position)
    f_pos_1 = 0
    f_pos_2 = 0
    f_init_line_num = 0
    line_positions_dict = {}
    for i in lines_1:
        f_init_line_num += 1
        if lines_1[len(lines_1) - 1] == i:
            f_pos_2 = f_pos_1 + len(i)      # 마지막 라인은 -1 을 하면 안 됨.
        else:
            f_pos_2 = f_pos_1 + len(i) - 1  # \n char 가 맨 마지막에 붙어있으니 때자..

        # line_positions_dict
        # l[0]:0..12
        # l[1]:13..21
        line_positions_dict[f_init_line_num] = str(f_pos_1) + ".." + str(f_pos_2)
        f_pos_1 += len(i) # \n char 를 고려해서 + 1을 해야 하나, 마지막에 붙어있으니 + -

    # hunk position dict 생성 (한 hunk 단위로 position 을 모아서..)
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
            print (i['pos'], i['typeLabel'], i['type'])



if __name__ == "__main__":
    test()



