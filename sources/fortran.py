import re
import os
import fnmatch
import pydot 

class ModuleNode(pydot.Node):
    def __init__(self, name, filename = "", obj_dict = None, **attrs):
        self.filename = filename
        pydot.Node.__init__(self, name = name, obj_dict = obj_dict, **attrs)

class FortranProgram(object):
    def __init__(self):
        self.main_name = ""
        self.analyzed_modules = []
        self.nodes = []
        self.graph = None
        self.filenames = []
        
#   It eliminates fortran comments ! 
    def searh(self, line, exp): 

        line = re.split('!', line.strip(),re.ASCII)[0]
        if re.search(exp, line,flags=re.ASCII): 
            return line.strip()
        else:
            return ''

 #  It looks for an expresion in a file and returns a list with occurences
    def search_in_file(self, file, exp):
        try:
            file.seek(0)
        except:
            file = file.split('\n')
            pass
        lines = []

        for line in file:
            if ( not re.search("\s*end\s*module",  line, flags=re.MULTILINE) and 
                 not re.search("\s*end\s*program", line, flags=re.MULTILINE)       ):
              
                l = self.searh(line, exp) 
                if l and ( l not in lines): lines.append(l)
                  
            else:
                break

        return lines

  # It returns a list with lines  with USE statement use USE without USE and ONLY ketwords
    def get_uses(self, unitfile, excluded_modules):
        
        use_lines = self.search_in_file(unitfile, "^use\s+")
        for i in range(0,len(use_lines)):
            
            if "," in use_lines[i]:
                use_lines[i]=re.split(', only', use_lines[i], flags=re.ASCII)[0]
        uses_list = [re.sub("^use\s+", "", l, flags=re.ASCII) for l in use_lines]
        nmbrexc=0

        for i in range(0,len(uses_list)):
            i = i - nmbrexc
            if uses_list[i] in excluded_modules:
                del uses_list[i]
                nmbrexc = nmbrexc + 1
        return uses_list

  # It looks for the name after MODULE or PROGRAM in unitfile  
    def get_unit_name(self, unitfile):
        
        returned_module  = self.search_in_file(unitfile, "^.{0,3}module\s+")
        returned_program = self.search_in_file(unitfile, "^program\s+")

        if returned_module:
            return re.sub("^.*module\s+", "", returned_module[0], flags=re.ASCII)
        elif returned_program:
            return re.sub("^.*program\s+", "", returned_program[0], flags=re.ASCII)
        else:
            return None
  
    def create_tree(self, node1, D1):

        for i in D1:
            node2 = ModuleNode(name = i)
            edge = pydot.Edge(node1, node2)

            self.nodes.append(node2)
            self.graph.add_node(node2)
            self.graph.add_edge(edge)

            if D1[i]:
                filename = D1[i][0]
                D2 = D1[i][1]
                node2.filename = filename
                node2.set('shape' , "Mrecord")
                self.graph.get_node(i)[0].set('shape' , "Mrecord")
                self.create_tree(node2, D2)
            else:
                pass

  # If generates a dictionary with USE dependencies. 
  # KEY is the name of the used module  
  # VALUE is a tuple = (name of the file where it is located, dicctionary of its dependencies )    
    def create_uses_dictionary(self, unit_name, unit_filename, search_directory, excluded_modules): 
       
        D = {}
        with open(unit_filename) as unit_file:
            uses = self.get_uses(unit_file, excluded_modules)
        self.analyzed_modules.append(unit_name)

        for module in uses:
            use_filename = self.search_module_file(module, search_directory)
            D[module] = []

            if use_filename is not None:
                if module not in self.analyzed_modules:
                    self.filenames.append(use_filename)
                    Dn = self.create_uses_dictionary( module, use_filename, search_directory, excluded_modules )
                    D[module] = (use_filename, Dn)
                                              
            else:
                D[module] = ()
        return D

  # It look for "module" + module_name in file directory 
    def search_module_file(self, module_name, search_directory):
        
        for root, dirnames, filenames in os.walk(search_directory):
            for filename in fnmatch.filter(filenames, '*.f90'):
                file_name = os.path.join(root, filename)
             #   print( "file name =  ", filename)
                with open(file_name) as file:

              #     if (self.find_in_file( file, "^\s*module\s+" + module_name)):
                    if self.search_in_file( file, "module " + module_name):
                        print( "FOUND module  " + module_name, "  filename =", filename)
                        return file_name
                    else:
                        continue

def generate_diagrams(filename, dirname, excluded_modules):

    D = FortranProgram( )
    D.filenames.append( filename )
    with open(filename) as main_file:
       D.main_name = D.get_unit_name( main_file )

    D.uses_dictionary = D.create_uses_dictionary( D.main_name, filename, dirname, excluded_modules )

    D.graph = pydot.Dot(grap_name = "TOP-DOWN design", graph_type = "digraph", dpi = 300 )
    main_node = ModuleNode(name = D.main_name, filename = filename, shape = "Mrecord")

    D.nodes.append(main_node)
    D.graph.add_node(main_node)

    D.create_tree(main_node, D.uses_dictionary)
        
    D.G = pydot.Graph(margin=5.)
    D.graph.write_pdf('graphs\\uses_simplediagram.pdf')
    D.graph.write_dot('graphs\\uses_simplediagram.dot')
    print("**** End simple uses")
