# -*- coding: utf-8 -*-
import re
import os
import fnmatch
from tkinter import filedialog as tkFileDialog
import sys
import time

import pydot 

class ModuleNode(pydot.Node):
    def __init__(self, name, filename = "", obj_dict = None, **attrs):
        self.filename = filename
        pydot.Node.__init__(self, name = name, obj_dict = obj_dict, **attrs)

class FortranProgram(object):
    def __init__(self, main_file_name, program_directory,lstExcludes):
        self.lstExcludes=lstExcludes
        self.main_file_name = main_file_name
        self.main_name = ""
        self.program_directory = program_directory  
        self.modules_searched = []
        self.nodes = []
        self.grafico = None
        self.graficotypes = None 
        self.filenames = []
        self.filetypes = {}
        self.tipos_ficheros = {} 
        self.__get_project_dependencies()
        self.create_legend()
        

    def __find_regexp(self, line, regexp): #Entra una linea y un patrón, elimina comentarios y devuelve la linea si existe coincidencia
        """Busca una expresion regular en una cadena.

        Recibe una cadena y una expresion regular, elimina comentarios
        y devuelve la cadena en caso de que esta contenga la expresion regular en minusculas.


        """
        strippeduncommented_line = re.split('!', line.strip(),re.ASCII)[0]#lower
        if re.search(regexp, strippeduncommented_line,flags=re.ASCII): #Manda la linea para ver si existe patrón
            return strippeduncommented_line.strip()
        else:
            return ''

    def __find_in_file(self, datafile, regexp):#Entra un archivo y un patrón, busca en el archivo eliminando comentarios líneas con el patrón y devuelve un lista con las líneas SALVO las repetidas.
                                               #Para una vez encuentra un END\s*MODULE o END\s*PROGRAM
        
        """Busca una expresion regular en un fichero.

        Recibe un fichero y una expresion regular y devuelve una lista
        con todas las lineas en las que hay una ocurrencia de esa expresion.

         """
        try:
            datafile.seek(0)
        except:
            datafile = datafile.split('\n')
            pass
        lines = []
        for line in datafile:
            #~ print("!!!!", line)
            if not re.search("\s*end\s*module",line,flags=re.MULTILINE) and not re.search("\s*end\s*program",line,flags=re.MULTILINE):
                
                line = self.__find_regexp(line, regexp)
                if line and line not in lines:
                    lines.append(line)
            else:
                #print( "end line: " + line)
                break
        return lines

    def __get_uses(self, unitfile):#Entra un archivo, devuelve una lista con las líneas del archivo con la palabra USE al principio de línea, quitando la susodicha palabra USE y las comas seguidas de ONLY
        uselines = self.__find_in_file(unitfile, "^use\s+")
        for idd in range(0,len(uselines)):
            
            if "," in uselines[idd]:
                uselines[idd]=re.split(', only', uselines[idd],flags=re.ASCII)[0]
        useslist = [re.sub("^use\s+", "", useline,flags=re.ASCII) for useline in uselines]
        nmbrexc=0
        for idd in range(0,len(useslist)):
            idd=idd - nmbrexc
            if useslist[idd] in self.lstExcludes:
                del useslist[idd]
                nmbrexc=nmbrexc+1
        return useslist

    def __get_unit_name(self, unitfile):#Entra un archivo, devuelve una cadena con el nombre que viene detrás de la palabra MODULE o PROGRAM, las cuales tienen que estar al principio de una linea del archivo
        returned_module = self.__find_in_file(unitfile, "^.{0,3}module\s+")#^.
        returned_program = self.__find_in_file(unitfile, "^program\s+")#^.

        if returned_module:
            return re.sub("^.*module\s+", "", returned_module[0],flags=re.ASCII)
        elif returned_program:
            return re.sub("^.*program\s+", "", returned_program[0],flags=re.ASCII)
        else:
            return None

    def __get_types(self, searchfile):#Entra un archivo, busca todas las lineas con la palabra TYPE al principio y devuelve la lista de líneas quitando la palabra TYPE.
        """Devuelve los nombres de los types del fichero searchfile."""
        typelines = self.__find_in_file(searchfile, "^type\s*(,\s*[\w(\w)]\s*)?[::]*\s*\w")#*\s*\s*\w
        #typelines.extend(self.__find_in_file(searchfile, "^type\s*[::]*\s*\w"))
        j=0
        for i in range(len(typelines)):
            i=i-j
            if " is " in typelines[i]:
                typelines.pop(i)
                j=j+1
        print( "!!!!!!TYPELINES!", typelines)
        typeliness= [re.sub("^type\s*,\s*[a-zA-Z]*\([a-zA-Z]*\)\s*[::]*\s*", "", typeline,flags=re.ASCII) for typeline in typelines]
        print( typeliness)
        return [re.sub("^type\s*[::]*\s*", "", typeline,flags=re.ASCII) for typeline in typeliness]

    def __get_subroutines(self, searchfile):#Entra un archivo, busca las líneas con la palabra SUBROUTINE al pricipio y devuelve la lista de líneas quitando la palabra SUBROUTINE
        """Devuelve los nombres de las subrutinas del fichero searchfile."""
        subroutine_lines = self.__find_in_file(searchfile, "^subroutine\s+\w")
        unstripped_names = [re.sub("^subroutine\s+", "", subroutine_line,re.ASCII)
                                      for subroutine_line in subroutine_lines]
        return [subroutinename.split("(")[0].strip()
                                for subroutinename in unstripped_names]

    def __get_funcs(self, searchfile):#Entra un archivo, busca las líneas con la palabra FUNCTION al principio de cada línea y devuelve la lista  de líneas quitando la palabra FUNCTION
        """Devuelve los nombres de las funciones del fichero searchfile."""
        function_lines = self.__find_in_file(searchfile, "^(\s*\w\s*)*function\s+\w")
        unstripped_names = [re.sub("^.*function\s+", "", function_line,re.ASCII)
                                      for function_line in function_lines]
        return [functionname.split("(")[0].strip()
                                for functionname in unstripped_names]

    def __find_modulefile(self, modulename, search_directory):#Busca en el directorio archivos con alguna línea coincidente con "MODULE" + modulename(minusculas), devuelve el archivo encontrado
        """Busca el fichero que contiene el module modulename."""
        print( "^module\s+" + modulename)
        for root, dirnames, filenames in os.walk(search_directory):
            for filename in fnmatch.filter(filenames, '*.f90'):
                searchedfilename = os.path.join(root, filename)
                with open(searchedfilename) as searchedfile:
                    #print( "------>>>SEARCHEDFILE", searchedfile)
                    if (self.__find_in_file(
                              searchedfile, "^\s*module\s+" + modulename)):
                        #print( "----------->>>lines", self.__find_in_file(
                        #      searchedfile, "^\s*module\s+" + modulename))
                        return searchedfilename
                    else:
                        continue

    def __get_filedependencies(self, unit_name,                  #A partir de un archivo te genera un diccionario con las dependecias USE, cuya clave es el nombre del USE, y cuya variable  
                               unit_filename, search_directory): #son el fichero donde se encuentra el use y las dependencias de este use en forma de otro diccionario homólogo.
                                                                 #Esta dependencia se omitirá si ya ha sido construida anteriormente.
        
        """Obtiene todas las dependencias del fichero unit_filename.

        Devuelve un diccionario en el que la clave es el nombre de la unidad,
        y el valor es una tupla con el nombre del fichero que la contiene y
        un diccionario de sus dependencias.

        """
        dependencies = {}
        with open(unit_filename) as unit_file:
            uses = self.__get_uses(unit_file)
        print( unit_name," usa: ", uses)
        self.modules_searched.append(unit_name)

        for use_name in uses:
            use_filename = self.__find_modulefile(use_name, search_directory)
            dependencies[use_name] = []
            print( "USE_FILENAME", use_filename)

            if use_filename is not None:
                if use_name not in self.modules_searched:
                    self.filenames.append(use_filename)
                    filedependencies = self.__get_filedependencies(
                                          use_name, use_filename,
                                          search_directory)
                    dependencies[use_name] = (use_filename,
                                              filedependencies)
            else:
                dependencies[use_name] = ()
        print( "DEPENDENCIES", dependencies)
        print( "MODULES_SEARCHED", self.modules_searched)
        return dependencies

    def __get_project_dependencies(self):#A partir del fichero principal obtiene las dependencias con el get_filedependencies
        """Obtiene todas las dependencias del fichero principal."""
        self.filenames.append(self.main_file_name)
        with open(self.main_file_name) as main_file:
            self.main_name = self.__get_unit_name(main_file)
        print( self.main_name)
        self.dependencies = self.__get_filedependencies(self.main_name,
                                self.main_file_name, self.program_directory)
        #~return dependencies

    def __create_usesnodelabel(self, unit_name, unit_filename):#Entra un fichero y busca todos las filas SUBROUTINE, TYPE y FUNCTION para hacer la etiqueta del nodo MODULE, devuelve un string en lenguaje DOT
        """Crea la label del nodo con toda la informacion del module."""
        with open(unit_filename) as unit_file:
            types = re.sub("(.{10},\s)", "\\1\s\\l", #!!!!!!!!!NUMERO DE CARACTERES EN LA ETIQUETA HASTA CAMBIAR DE LÍNEA (ÚTIL PARA HACER ESQUEMAS MAS ESTRECHOS)
                           ", ".join(self.__get_types(unit_file)),re.ASCII)
            newlinestypes=len(re.findall("\\\\s\\\\l",types,re.ASCII))
            if types:
                types=types+"\l"
                types=re.sub(",\s\\\\s",",",types,re.ASCII)
            
            subroutines = re.sub("(.{20},\s)", "\\1\s\\l",
                            ", ".join(self.__get_subroutines(unit_file)),re.ASCII)
            newlinessubroutines=len(re.findall("\\\\s\\\\l",subroutines,re.ASCII))
            if subroutines:
                subroutines=subroutines+"\l"
                subroutines=re.sub(",\s\\\\s",",",subroutines,re.ASCII)
            
            functions = re.sub("(.{20},\s)", "\\1\s\\l",
                               ", ".join(self.__get_funcs(unit_file)),re.ASCII)
            newlinesfunctions=len(re.findall("\\\\s\\\\l",functions,re.ASCII))
            if functions:
                functions=functions+"\l"
                functions=re.sub(",\s\\\\s",",",functions,re.ASCII)
            
        print( "FILE" , unit_file)
        print( "types:", types, "\n", "subroutines:", subroutines, "\n", "functions:", functions)
        
        node_label = ("{" + unit_name + "|{{types\l" + " \l"*newlinestypes + "|" + "subroutines\l" 
                    + " \l"*newlinessubroutines + "|"+ "functions\l" + " \l"*newlinesfunctions 
                    + "}" + "|" + "{" + types + "|" + subroutines + "|" + functions
                    + "}}}")
        return node_label

    def __create_usesnodetree(self, unit_node, dependencies_dictionary):
        """Agrega el nodo al grafico de uses y todas sus dependencias."""
        for use_name in dependencies_dictionary:
            #Se crea un nodo por cada use y se añade al grafico y a la lista de
            #nodes. Tambien se crea el Edge entre los nodos y se añade
            use_node = ModuleNode(name = use_name)
            self.nodes.append(use_node)
            self.grafico.add_node(use_node)
            edge = pydot.Edge(unit_node, use_node)
            self.grafico.add_edge(edge)
            if dependencies_dictionary[use_name]:
                print( "!!", dependencies_dictionary[use_name])
                use_filename = dependencies_dictionary[use_name][0]
                use_dependencies = dependencies_dictionary[use_name][1]
                use_node.filename = use_filename
                use_node.set('shape' , "Mrecord")
                self.grafico.get_node(use_name)[0].set('shape' , "Mrecord")
                self.__create_usesnodetree(use_node, use_dependencies)
            else:
                pass

    def generate_uses_simplediagram(self):
        """Genera el grafico de uses del main_file."""
        self.grafico = pydot.Dot(grap_name = "Diagrama de uses",
                                 graph_type = "digraph",
                                 dpi = 300 )
        main_node = ModuleNode(name = self.main_name,
                                filename = self.main_file_name,
                                shape = "Mrecord")
        self.nodes.append(main_node)
        self.grafico.add_node(main_node)
        self.__create_usesnodetree(main_node, self.dependencies)
        print( self.dependencies)
        
        self.G=pydot.Graph(margin=5.)
        self.legend=pydot.Subgraph(graph_name='Legend', shape = 'Mrecord', rank='sink', label='Legend')
        self.grafico.add_subgraph(self.legend)
        self.grafico.write_svg('graphs\\uses_simplediagram.svg')#.format(time.strftime("%d%m%y%H%M")))
        self.grafico.write_jpg('graphs\\uses_simplediagram.jpg'.format(time.strftime("%d%m%y%H%M")))
        self.grafico.write_pdf('graphs\\uses_simplediagram.pdf'.format(time.strftime("%d%m%y%H%M")))
        self.grafico.write_dot('graphs\\uses_simplediagram.dot'.format(time.strftime("%d%m%y%H%M")))

    def generate_uses_diagram(self):
        """Genera el grafico de uses del main_file.

        Incluye la informacion acerca de las subrutinas, types y funciones
        que contiene cada module.

        """
        self.generate_uses_simplediagram()
        for node in self.nodes:
            node_name = node.get_name()
            node_filename = node.filename
            if node_filename:
                node_label = self.__create_usesnodelabel(node_name, node_filename)
                self.grafico.get_node(node_name)[0].set_label(node_label)


        self.grafico.write_png('graphs\\uses_diagram.png'.format(time.strftime("%d%m%y%H%M")))
        self.grafico.write_jpg('graphs\\uses_diagram.jpg'.format(time.strftime("%d%m%y%H%M")))
        self.grafico.write_pdf('graphs\\uses_diagram.pdf'.format(time.strftime("%d%m%y%H%M")))
        self.grafico.write_dot('graphs\\uses_diagram.dot'.format(time.strftime("%d%m%y%H%M")))

    def __get_filetypes(self):#Crea diccionario FILETYPES cuya clave es un archivo y las variables son los distintos tipos que contiene
        filetypes = {}
        for filename in self.filenames:
            with open(filename) as openedfile:
                types = self.__get_types(openedfile)
                filetypes[filename] = types

            for tipo in types:
                self.tipos_ficheros[tipo] = filename
            print( "!!!!!!!!!!!!!!!",self.tipos_ficheros)
        return filetypes

    def generate_typesdiagram(self):
        self.graficotypes = pydot.Dot(grap_name = "Diagrama de types",
                                      graph_type = "digraph")
                                      #dpi = 300 )
        filetypes = self.__get_filetypes()
        fileclusters = []
        for filename in filetypes:
            with open(filename) as searchfile:
                unitname = self.__get_unit_name(searchfile)
            print( unitname)
            fileclusters.append(pydot.Cluster(unitname, label = unitname))
            self.graficotypes.add_subgraph(fileclusters[-1])
            for tipo in filetypes[filename]:
                fileclusters[-1].add_node(pydot.Node(tipo))

        for filename in filetypes:
            for tipo in filetypes[filename]:
                with open(filename) as searchfile:
                    typecode = self.get_type_code(tipo, searchfile)
                    print( "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", typecode)
                    print( re.sub("\\\l","\n",typecode,re.ASCII))
                used_types = self.get_used_types(re.sub("\\\l","\n",typecode,flags=re.ASCII))
                for used_type in used_types:
                    self.graficotypes.add_edge(pydot.Edge(tipo, used_type))
        self.graficotypes.write_png('graphs\\types_diagram.png'.format(time.strftime("%d%m%y%H%M")))
        self.graficotypes.write_jpg('graphs\\types_diagram.jpg'.format(time.strftime("%d%m%y%H%M")))
        self.graficotypes.write_pdf('graphs\\types_diagram.pdf'.format(time.strftime("%d%m%y%H%M")))
        self.graficotypes.write_dot('graphs\\types_diagram.dot'.format(time.strftime("%d%m%y%H%M")))

    def get_used_types(self, code):#A partir del codigo de los tipos saca la lista de los tipos usados
        codefile = code
        #~ print ("!!codefile",codefile,"!!")
        type_lines = self.__find_in_file(codefile, ".*type\s*\(")
        if self.__find_in_file(codefile, "^.*type\s*,\s*extends\s*\("):
            type_extends = self.__find_in_file(codefile, "^.*type\s*,\s*extends\s*\(")
            for type_extend in type_extends:
                type_lines.append(re.sub("^.*type\s*,\s*extends\s*\(", "",type_extend,flags=re.ASCII))
        #else:
            #pass
        #~ print( "!!type_lines: ", type_lines)
        unstripped_names = [re.sub(".*type\s*\(", "", type_line,re.ASCII) for type_line in type_lines]
        return [subroutinename.split(")")[0].strip()
                                for subroutinename in unstripped_names]


    def get_type_code(self, typename, searchfile): #Buscar en un archivo el codigo que define los tipos
        typecode = ""
        into_typecode = False
        searchfile.seek(0)
        for line in searchfile:
            if self.__find_regexp(line,
                                        "^type\s*(,\s*[a-zA-Z]+\([a-zA-Z]+\)\s*)*[::]*\s*" + typename):#lower
                into_typecode = True
                #typecode = typecode + self.__find_regexp(line,
                #                        "^type\s*(,\s*[a-zA-Z]+\([a-zA-Z]+\)\s*)*[::]*\s*" + typename)+ " \l "
                continue
            elif into_typecode:
                if self.__find_regexp(line,
                                        "^end\s*type"):
                    into_typecode = False
                    break
                else:
                    line=re.split('!', line.strip(),re.ASCII)[0]#lower
                    line=re.sub('=>', '\=\>',line.strip(),re.ASCII)#lower
                    #~ line=re.sub('->', '\-\>',line.strip())#lower
                    typecode = typecode + line + " \l "
            else:
                continue
        #typecode=typecode 
        return typecode

    def generate_typescomplete_diagram(self):
        self.generate_typesdiagram()
        for subgraph in self.graficotypes.get_subgraphs():
            for node in subgraph.get_nodes():

                typename = node.get_name()
                print( "!!!!!!!!!!!!!!!!!!!!!!!!", typename, node)
                with open(self.tipos_ficheros[typename]) as fich:
                    codigo = self.get_type_code(typename, fich)
                node.set('shape', "Mrecord")
                label = ('{' + typename + '|' + codigo
                        + '}')
                print( label)
                node.set_label(label)
        self.graficotypes.write_png('graphs\\types_completediagram.png'.format(time.strftime("%d%m%y%H%M")))
        self.graficotypes.write_jpg('graphs\\types_completediagram.jpg'.format(time.strftime("%d%m%y%H%M")))
        self.graficotypes.write_pdf('graphs\\types_completediagram.pdf'.format(time.strftime("%d%m%y%H%M")))
        #~ self.graficotypes.write_dot('graphs\\types_completediagram.dot')

    def update_dependencies(self, new_file = None, new_dir = None):
        if new_file is not None:
            self.main_file_name = new_file
        if new_dir is not None:
            self.program_directory = new_dir

        self.__get_project_dependencies()
        
    def create_legend(self):
        legend=pydot.Subgraph(graph_name='Legend')
        legend.set('shape' , "Mrecord")
        #self.grafico.get_node(use_name)[0].set('shape' , "Mrecord")
        

    def generate_diagrams(self):
        self.generate_uses_diagram()
        self.generate_typescomplete_diagram()
    
    
    #def set_attributes(self):
        #G.obj_dict['attributes']['labeljust']
        

def generate_diagrams(filename, dirname,lstExcludes):
    programa = FortranProgram(filename, dirname,lstExcludes)
    programa.generate_uses_diagram()
    programa.generate_typescomplete_diagram()

if __name__ == '__main__':
    filename = tkFileDialog.askopenfilename(
                            title = "Seleccione el fichero a analizar",
                            filetypes=[("Ficheros fortran", ".f90"),
                                       ("Todos los ficheros",".*")])
    dirname = tkFileDialog.askdirectory(
                              title = "Seleccione el directorio de busqueda")
    programa_ejemplo = FortranProgram(filename, dirname)
    #~ print( programa_ejemplo.get_filedependencies("prueba", programa_ejemplo.main_file_name,
                                    #~ programa_ejemplo.program_directory))
    programa_ejemplo.generate_uses_diagram()
    #~ programa_ejemplo.generate_typesdiagram()
    programa_ejemplo.generate_typescomplete_diagram()
    #~ programa_ejemplo.generate_uses_diagram('ejemplo.png')
    #sys.exit()





