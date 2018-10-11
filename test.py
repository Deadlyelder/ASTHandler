# -*- coding: utf-8 -*-
import clang.cindex
import json
from MyUtils import read_file, write_file

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

def nodeTraverseBuild(cursor, depth=0):
    node = buildNode(cursor)
    for child_cursor in cursor.get_children():
        child = nodeTraverseBuild(child_cursor, depth + 1)
        node['z_children'].append(child)
    return node

def printNode(cursor, depth):
    if depth==0:
        str_depth=""
    else:
        str_depth = "+" + ("--"*depth)

    print '%s"%s" {%s} [line=%s, col=%s, offset=%s, type=%s, access=%s, spelling=%s]' % \
          (str_depth, cursor.displayname, str(cursor.kind).split('.')[1], cursor.location.line, cursor.location.column, cursor.location.offset,
            str(cursor.type.kind).split('.')[1], str(cursor.access_specifier).split('.')[1], cursor.spelling)

def nodeTraversePrint(cursor, depth = 0): # Node traverse for printing
    printNode(cursor, depth)
    for c in cursor.get_children():
        nodeTraversePrint(c, depth + 1)

def jsonFileLoad(path):
    with open(path) as f:
        return json.load(f)
    
# Modified from https://eli.thegreenplace.net/2011/07/03/parsing-c-in-python-with-clang/
def find_typerefs(node, typename):
    """ Find all references to the type named 'typename'
    """
    if node.kind.is_reference():
        ref_node = clang.cindex.Cursor_ref(node)
        if ref_node.spelling == typename:
            print 'Found %s [line=%s, col=%s]' % (
                typename, node.location.line, node.location.column)

    # Recurse for children of this node,
    # skipping all nodes not beginning with "a"
    for c in node.get_children():
        if c.spelling.endswith ("/stdio.h"):
            print "Skipping stdio.h"
            return 1
 
# Another possible function; this one works by excluding the nodes from specific fice while visiting the AST. The idea is to first test in the visit to skip the file as early as it is being hit and avoid its subnodes all together
def func_visitor(self, node, parent, userdata):
    
    if node.location.file.endswith("/stdio.h"):
        print "Skip stdio.h"
        return 1
    
    if node.kind == clang.cindex.CursorKind.FUNCTION_DECL: #https://clang.llvm.org/doxygen/classclang_1_1FunctionDecl.html
        self.func_defn.append(clang.cindex.Cursor_displayname(node))
        self.func_defn_line_no.append(node.location.line)
        self.func_defn_col_no.append(node.location.column)
# https://github.com/libigl/libigl/blob/master/python/scripts/parser.py

    print 'Found %s [line=%s, col=%s]' % (
        clang.cindex.Cursor_displayname(node),
        node.location.line,
        node.location.column)

    # Continue visiting recursively
    return 2

tu = index.parse(self.filename)
clang.cindex.Cursor_visit(
    tu.cursor,
    clang.cindex.Cursor_visit_callback(self.func_visitor),
    None)

# End of my function


if __name__ == "__main__":
    before_file_path = '.before.c'
    clang.cindex.Config.set_library_file('/usr/lib/x86_64-linux-gnu/libclang-6.0.so')
    index = clang.cindex.Index.create()
    line_endpos_dict = buildLinePosDict(before_file_path)
    translation_unit = index.parse(before_file_path)

    node = nodeTraverseBuild(translation_unit.cursor)
    nodeTraversePrint(translation_unit.cursor)

    json_path = '.before.json'
    write_file(json_path, json.dumps(node, sort_keys=True, indent=4))

    tree_before = jsonFileLoad(json_path)
