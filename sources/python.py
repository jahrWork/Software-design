import re
import os 
import time
import pydot
import setuptools
from collections import namedtuple as Namedtuple 


class ModuleNode(pydot.Node):
    def __init__(self, name, filename="", obj_dict=None, **attrs):
        self.filename = filename
        pydot.Node.__init__(self, name=name, obj_dict=obj_dict, **attrs)
        return
        pass
    pass


class ProgramPython(object):
 
    def _filename2module(self, filename: str):
        module = filename
        module = re.sub("[.]{1,1}py$", '', module)
        module = module.replace(os.sep, '.')
        module = module.replace('\\', '.')
        return module 

    def _find_existing_packages(self, paths):
        findings = list()
        if isinstance(paths, str):  
            paths = [paths]
            pass
        for path in paths:
            findings += setuptools.find_packages(path)
            pass
        findings = list(set(findings))
        [print("PACKAGE: |{0}|".format(p)) for p in findings]
        return findings
        pass

    def _find_existing_modules(self, paths, excludes):
        newdict = dict()
        files, modules = self._find_existing_files(paths, excludes)
        print("{:->10}".format(""))
        for file, module in zip(files, modules):
            print("SCAN: |{}|".format(file))
            f = open(file, 'r', encoding="utf8")
            code = f.read()
            f.close()
            token = self._scan_code(code)
            newdict[module] = (file, token)
            print("FUNCTIONS: |{0}|".format(', '.join(token.functions)))
            print("CLASSES:   |{0}|".format(', '.join(token.classes)))
            print("IMPORTS:   |{0}|".format(', '.join(token.apis)))
            print("{:->10}".format(""))
        return newdict
        pass

    def _find_existing_files(self, paths, excludes):

        def _subfindall(files, excludes):
            subfiles = list()
            # file ends with 'py' extension
            matching_pattern = r"[.]{1,1}py$"
            # file does not contain 'OLD' word nor underscore.
            not_matching_pattern = r"(OLD|_[\w_ +\-]+[.]{1,1}py$)"
            for file in files:
                cond_excludes = not any([file.startswith(exclude) for exclude in excludes])
                cond_true = bool(re.search(matching_pattern, file))
                cond_false = bool(re.search(not_matching_pattern, file))
                if cond_excludes and cond_true and not cond_false:
                    subfiles.append(file)
                    pass
                pass
            return subfiles

        findings = list()
        modules = list()

        parsedfindings = list()
        parsedmodules = list()

        if isinstance(paths, str):
            paths = [paths]
            pass
        if isinstance(excludes, str):
            excludes = [excludes]
            pass

        for path in paths:
            files = setuptools.findall(path)
            files = _subfindall(files, excludes)
            submodules = [file.replace(path, '') for file in files]
            submodules = [submodule[1:] if submodule.startswith(os.sep) else submodule for submodule in submodules]
            submodules = [self._filename2module(submodule) for submodule in submodules]

            findings += files
            modules += submodules
            pass

        [print("MODULE NAME |{0}| ON |{1}| ".format(m, f)) for m, f in zip(modules, findings)]
        return findings, modules

    def _scan_code(self, code: str):

        def _parse_code(code: str):
            fullcoments = ['"""', "'''"]
            reg_comment = r'#.*'
            #reg_group = r'(?s)""".*"""'

            for c in fullcoments:
                while True:
                    indent = len(c)
                    i = code.find(c)
                    if i < 0:
                        break
                    else:
                        prefix = code[:i]
                        j = code.find('"""', i + indent)
                        if j < 0:
                            print("Warning: Error in code")
                            break
                        sufix = code[j + indent:]
                        code = prefix + sufix
                        pass
                    pass
                pass

            code = re.sub(reg_comment, '', code)
            return code
        
        def _token_pattern():
            reg_def = (r'(async\s+)?'
                       r'(?P<DEF_TYPE>(def|class))\s+'
                       r'(?P<DEF_NAME>\w+)\s*'
                       r'(\((?P<DEF_ARGS>.*)\))?'
                       r'.*:')

            reg_import = (r'(from\s+(?P<FROMS>[\w.]+)\s+)?'
                          r'import\s+'
                          r'(?P<IMPORTS>([\w.]+'
                          r'(\s+as\s+[\w.]+)?'
                          r'(\s*,\s*|(?=(\n)\s*))'
                          r')+)')


            tokens = [('DEF', reg_def), ('IMPORT', reg_import)]
            fmt = "?P<{0}>{1}"
            reg_list = [fmt.format(name, regex) for name, regex in tokens]
            reg = '(' + ')|('.join(reg_list) + ')'
            reg = r"(?P<INDENT>(?<=\n)[ \t\r]*)" + reg
            return reg
            pass

        def _tokenize(code: str, pattern: str):
            token_scan_name = "Token"
            token_scan_fields = ['type', 'name', 'args', 'indent']
            token_scan = Namedtuple(token_scan_name, token_scan_fields)

            def _tokenize_defs(mo):
                kind = mo.group("DEF_TYPE")
                if kind.lower() == "class":
                    kind = "CLASS"
                else:
                    kind = "FUNC"
                name = mo.group("DEF_NAME")
                indent = mo.group("INDENT")
                indentation = 0 if indent is None else len(indent)
                arguments = mo.group("DEF_ARGS")
                args = list()
                if arguments is None:
                    args = ["Object"]
                else:
                    arguments = arguments.split(',')
                    for arg in arguments:
                        arg = arg.split('=', 1)[0]
                        arg = arg.split(':', 1)[0]
                        arg = arg.strip(' ')
                        args.append(arg)
                yield token_scan(kind, name, args, indentation)
                return
                pass

            def _tokenize_imports(mo):
                kind = "IMPORT"
                indent = mo.group("INDENT")
                indentation = 0 if indent is None else len(indent)
                imports = mo.group("IMPORTS")
                imports = re.sub(r"\s+as.*", '', imports)
                imports = re.sub(r'\s+', '', imports)
                imports = imports.split(',')

                froms = mo.group("FROMS")
                if froms is None:
                    froms = ''
                    pass
                else:
                    imports = [(froms + '.' + imp).replace('..', '.') for imp in imports]
                yield token_scan(kind, froms, imports, indentation)
                return
                pass

            for mo in re.finditer(pattern, code):
                kind = mo.lastgroup
                if kind == 'DEF':
                    for item in _tokenize_defs(mo):
                        yield item
                elif kind == 'IMPORT':
                    for item in _tokenize_imports(mo):
                        yield item
            return
            pass

        def _code_content(code: str):
            token_name = "Content"
            token_fields = ["functions", "classes", "apis"]
            token_content = Namedtuple(token_name, token_fields)

            functions = dict()
            classes = dict()
            apis_list = list()

            pattern = _token_pattern()

            for token in _tokenize(code, pattern):
                if token.type == "FUNC" and not token.name.startswith('_'):
                    functions[token.name] = token.args
                elif token.type == "CLASS" and not token.name.startswith('_'):
                    args = token.args
                    classes[token.name] = args
                elif token.type == "IMPORT":
                    module = token.name
                    imports = token.args
                    apis_list += imports
                    pass
            apis_list = list(set(apis_list))
            return token_content(functions, classes, apis_list)

        code = _parse_code(code)
        return _code_content(code)
        pass

    def _packages_deps(self):
        newdict = dict()
        for package in self._packages:
            deps = list()
            for module in self._modules:
                if package in module:
                    deps.append(module)
                    pass
                pass
            newdict[package] = (package, [], [], deps)
            pass
        return newdict

    def areCommon(self, left: str, right: str, delim: str = '.'):
        left_arr = left.split(delim)
        right_arr = right.split(delim)
        i, j = len(left_arr), len(right_arr)
        k = min([i, j])
        for l in range(k, 0, -1):
            if left_arr[-l: i] == right_arr[0: l]:
                return l
            pass
        else:
            return 0
        pass

    def _find_file_dependancies(self, module):
        out = list()

        name = module
        links = list()
        nodetype = dict()
        imported = dict()

        nodetype[module] = "Mrecord"
        imported[module] = self._modules[module][1][0:2]

        apis = self._modules[module][1].apis
        print("MODULE is: ", module)
        for api in apis:
            api = api[1:] if api.startswith('.') else api
            if api in self._modules:
                print("API in modules: ", api)
                links.append((module, api))
                nodetype[api] = "Mrecord"
                imported[api] = self._modules[api][1][0:2]
                out += self._find_file_dependancies(api)
                pass
            elif api in self._packages:
                print("API in packages: ", api)
                links.append((module, api))
                nodetype[api] = "Rectangle"
                imported[api] = None
                print(self._packages[api][1])
                for subapi in self._packages[api][1].apis:
                    out += self._find_file_dependancies(subapi)
                    pass
                pass
            elif any([self.areCommon(m, api) for m in self._modules]):
                lmax = -1
                modulemax = ""
                for m in self._modules:
                    if self.areCommon(m, api):
                        l = self.areCommon(m, api)
                        prefix = '.'.join(m.split('.')[-l:])
                        intersection = '.'.join(api.split('.')[0:l])
                        sufix = '.'.join(api.split('.')[l:])

                        if sufix == '':
                            print("API is a module on a package: ", api)
                            links.append((module, m))
                            nodetype[m] = "Mrecord"
                            imported[m] = self._modules[m][1][0:2]
                            out += self._find_file_dependancies(m)
                            break
                            pass
                        elif l > lmax:
                            lmax = l
                            modulemax = m
                        pass
                    pass
                else:
                    print("API is a definition on a module: ", api)
                    basemodule = modulemax
                    importation = api.replace(basemodule + '.', '')
                    links.append((module, basemodule))

                    funcs, classes, _ = self._modules[basemodule][1]
                    old_f, old_c = imported.get(basemodule, ([], []))
                    if importation in funcs:
                        old_f.append(importation)
                        pass
                    elif importation in classes:
                        old_c.append(importation)
                        pass
                    else:
                        print("ERRROR: ", self._modules[basemodule])
                        print(list(self._modules.keys()))
                        pass
                    imported[basemodule] = (old_f, old_c)
                    nodetype[basemodule] = "Mrecord"
                    #out += self._find_file_dependancies(basemodule)
                    pass
                pass
            elif any([self.areCommon(p, api) for p in self._packages]):
                lmax = -1
                packagemax = ""
                for p in self._packages:
                    if self.areCommon(p, api):
                        l = self.areCommon(p, api)
                        prefix = '.'.join(p.split('.')[-l:])
                        intersection = '.'.join(api.split('.')[0:l])
                        sufix = '.'.join(api.split('.')[l:])

                        if sufix == '':
                            print("API is a subpackage on a package: ", api)
                            links.append((module, p))
                            nodetype[p] = "Mrecord"
                            imported[p] = ([], [])
                            for submodule in self._packages[p][3]:
                                out += self._find_file_dependancies(submodule)
                                pass
                            break
                            pass
                        elif l > lmax:
                            lmax = l
                            packagemax = p

                        pass
                    pass
                else:
                    print("PCK ERRR: ", packagemax)
                    pass
                pass
            else:
                print("API is external: ", api)
                links.append((module, api))
                nodetype[api] = "ellipse"
                imported[api] = ([], [])
            pass

        nodetype[module] = "Mrecord"
        imported[module] = self._modules[module][1][0:2]

        out += [(name, links, nodetype, imported)]
        print("")
        return out
        
        pass
    
    def _get_dot(self):
        nodes = list()
        links = list()
        types = dict()
        labels = dict()
        deps = self._deps

        for dep in deps:
            thisname = dep[0]
            thislinks = dep[1]
            thistypes = dep[2]
            thisimports = dep[3]

            if '.' in thisname:
                print(thisname.split('.'))
                nodes += thisname.split('.')
                pass
            else:
                print(thisname)
                nodes.append(thisname)
                pass
            pass

            for link in thislinks:
                fr = [link[0]] if not '.' in link[0] else link[0].split('.')
                to = [link[1]] if not '.' in link[1] else link[1].split('.')
                l = fr + to
                for i in range(0, len(l) - 1):
                    print(l[i], "->", l[i+1])
                    links.append((l[i], l[i+1]))
                    nodes.append(l[i+1])
                    pass
                pass

            for name, tp in thistypes.items():
                if '.' in name:
                    split = name.split('.')
                    for i in range(0, len(split) - 1):
                        types[split[i]] = tp
                        links += [(split[i], split[i + 1])]
                        pass
                    types[split[-1]] = tp
                    pass
                else:
                    types[name] = tp
                    pass
                types[name.split('.')[-1]] = tp
                pass

            for key0, val in thisimports.items():
                
                if '.' in key0:
                    key = key0.split('.')[-1]
                    pass
                else:
                    key = key0
                    pass
                print(key0, key, val[0], val[1])
                labels[key] = self._create_label(key, val[0], val[1])
                pass
            pass
        
        self.nodes = list(set(nodes))
        self.links = list(set(links))
        self.types = types
        self.labels = labels
        pass

    def __init__(self, main_file_name, program_directory, lstExcludes):
        bad_sep = '/' if os.sep == '\\' else '\\'

        main_file_name = main_file_name.replace(bad_sep, os.sep)
        
        self.main_name = main_file_name.split(os.sep)[-1].split('.')[0]
        self.root = os.sep.join(main_file_name.split(os.sep)[:-1])
        self.main_file_name = main_file_name

        search_dirs = list()
        if isinstance(program_directory, list):
            for progdir in program_directory:
                search_dirs.append(progdir.replace(bad_sep, os.sep))
                pass
            pass
        elif isinstance(program_directory, str):
            search_dirs.append(program_directory.replace(bad_sep, os.sep))
            pass
        
        exclude_dirs = list()
        if isinstance(lstExcludes, list):
            for exclude in lstExcludes:
                if exclude.startswith("./") or exclude.startswith(".\\"):
                    exclude_dirs.append(self.root + os.sep + exclude[2:])
                    pass
                else:
                    exclude_dirs.append(exclude)
                    pass
                pass
        elif isinstance(lstExcludes, str):
            if lstExcludes.startswith("./") or lstExcludes.startswith(".\\"):
                exclude_dirs.append(self.root + os.sep + lstExcludes[2:])
                pass
            else:
                exclude_dirs.append(lstExcludes)
                pass
            pass
        
        self.excludes = exclude_dirs
        self._packages = self._find_existing_packages(search_dirs)
        self._modules = self._find_existing_modules(search_dirs, self.excludes)
        self._packages = self._packages_deps()
        self._deps = self._find_file_dependancies(self.main_name)
        
        self._get_dot()

        [print(n) for n in self.links]
        
        print(self.excludes)
        pass

    def _generate_diagram(self, out: str, includeLabels: bool) -> None:
        if includeLabels:
            title = "Diagrama import"
        else:
            title = "Diagrama import simple"
        grafico = pydot.Dot(name=title, graph_type="digraph", dpi = 300)
        print("")
        for node in self.nodes:
            print("NODE: |{0}|".format(node))
            pydotnode = pydot.Node(name=node, shape=self.types[node])
            if node in self.labels and includeLabels:
                pydotnode.set_label(self.labels[node])
                pass
            grafico.add_node(pydotnode)
            pass
        print("")
        for fr, to in self.links:
            fmt_link = "{0} <-> {1}"
            print("LINK: {0}".format(", ".join([fmt_link.format(fr, to)])))
            node_fr = grafico.get_node(fr)[0]
            node_to = grafico.get_node(to)[0]
            edge = pydot.Edge(node_fr, node_to)
            grafico.add_edge(edge)

        #grafico = self._labels(grafico, self.plain, includeLabels)
        time_str = time.strftime("%d%m%y%H%M")
        grafico.write_dot('{}.{}'.format(out, "dot", time_str))
        grafico.write_jpg('{}.{}'.format(out, "jpg", time_str))
        grafico.write_png('{}.{}'.format(out, "png", time_str))
        grafico.write_pdf('{}.{}'.format(out, "pdf", time_str))
        return

    def generate_uses_simplediagram(self):
        out = "graphs" + os.sep + "uses_simplediagram"
        self._generate_diagram(out, False)
        pass

    def generate_uses_diagram(self):
        out = "graphs" + os.sep + "uses_diagram"
        self._generate_diagram(out, True)
        pass

    def _create_label(self, name, funcs, classes):
        # \l == new line

        # 0 -> module name, 1 -> APIs
        nl_fmt_name = "{{" + "{0}|{{" + "{1}" + "}}}}"

        # 0 -> type, 1 -> items
        nl_fmt_table = "{{" + "{0}" + "}}|{{" + "{1}" + "}}"

        # 0 -> aditional \l
        nl_fmt_funcs = "func\l{0}"

        # 0 -> aditional \l
        nl_fmt_class = "class\l{0}"

        col1 = ""
        col2 = ""
        if funcs is not None and len(funcs) > 0:
            funcs_col2 = ", ".join(funcs)
            if len(funcs_col2) > 20:
                        funcs_col2 = re.sub("(?<=.{20}),", ",\l", funcs_col2)
            n_lfs = "\l" * funcs_col2.count('\l')
            col1 += nl_fmt_funcs.format(n_lfs)
            col2 += funcs_col2
        if classes is not None and len(classes) > 0:
            if col1 != "":
                col1 += "|"
                col2 += "|"
            class_col2 = ", ".join(classes)
            if len(class_col2) > 20:
                        class_col2 = re.sub("(.{20},\s)", "\\n", class_col2)
            n_lfs = "\l" * class_col2.count('\n')
            col1 += nl_fmt_class.format(n_lfs)
            col2 += class_col2

        if col1 != "":
            table = nl_fmt_table.format(col1, col2)
            node_label = nl_fmt_name.format(name, table)
        else:
            node_label = name

        return node_label
    pass

def generate_diagrams(filename, dirname,lstExcludes):
    programa = ProgramPython(filename, dirname,lstExcludes)
    programa.generate_uses_diagram()
    programa.generate_uses_simplediagram()
