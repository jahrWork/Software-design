import os.path
import os

import matplotlib.pyplot as plt
import matplotlib.widgets as widg
print (dir(widg))
from matplotlib.widgets import TextBox

import json
import PIL
from tkinter import filedialog as tkFileDialog
from tkinter import *

from fortran import  generate_diagrams as generate_diagrams_fortran
from python  import  generate_diagrams as generate_diagrams_python


class Interface(object):
    def __init__(self):
        #~ window=Tk()
        #~ w=Frame(window)
        
        
        
        #try:
        with open("configuration.ini", 'r') as fich:
            self.filedir = json.load(fich)
            print (self.filedir)
        #except:
        #    self.filedir = {'filename' : "main.f90",
        #                'dirname' : "./"}
        #.format(time.strftime("%d%m%y%H%M")
        self.diagrams_dicc = {'1.Use graph': "graphs{0}uses_simplediagram.jpg".format(os.sep), 
                              '2.Complete use graph': "graphs{0}uses_diagram.jpg".format(os.sep),
                              '3.Type graph' : "graphs{0}types_diagram.jpg".format(os.sep),
                              '4.Complete type graph': "graphs{0}types_completediagram.jpg".format(os.sep)}
        self.selected_diagram = '1.Use graph'

        #~ self.lstExcludes=['GlazingM']
        self.main_window = plt.figure(figsize=(16.,12.), dpi=70)
        self.graf_area = self.main_window.add_axes([0.25, 0.1, 0.73, 0.88])


        try: 
            with open("excludes.ini", 'r') as fich:
                self.lstExcludes = json.load(fich)
                print ("lstexcludes LOADED")
                print (self.lstExcludes)
                for Exc in self.lstExcludes:
                    self.listExcludes.insert(END,Exc)
                
        except:
            pass
            #self.lstExcludes=[]
            #print "lstexcludes EMPTY"

        def clearall(self):
            self.listExcludes.delete(0,END)
            self.lstExcludes=[]
            print (self.lstExcludes)
            with open('excludes.ini', mode='w') as fich:
                json.dump(self.lstExcludes, fich)
            print ("SAVED in excludes.ini")
        #~ exclusiones=Excludes()
        
        #~ excludetext_pos= plt.axes([0.05,0.1,0.2,0.3])
        #~ self.excludetext=TextBox(excludetext_pos,"Current Exclusions", initial='\n'.join(self.lstExcludes))
        #~ self.excludetext.on_submit(clearall)

        butfile_pos = plt.axes([0., 0., 0.25, 0.06])
        self.butfile = widg.Button(butfile_pos, 'Select folder...')
        self.butfile.on_clicked(self.__selectdir_click)

        butdir_pos = plt.axes([0.25, 0., 0.25, 0.06])
        self.butdir = widg.Button(butdir_pos, 'Select main file...')
        self.butdir.on_clicked(self.__selectfile_click)

        butupdt_pos = plt.axes([0.5, 0., 0.25, 0.06])
        self.butupdt = widg.Button(butupdt_pos, 'Refresh graphs...')
        self.butupdt.on_clicked(self.__update_click)

        butexc_pos=plt.axes([0.75,0.,0.25,0.06])
        self.butexc=widg.Button(butexc_pos, 'USES excluded')
        self.butexc.on_clicked(self.__excludes)
        
        grafselect_pos = plt.axes([0.01, 0.6, 0.2, 0.2])
        diagram_list = [name for name in sorted(self.diagrams_dicc)]
        self.grafselect = widg.RadioButtons(grafselect_pos, diagram_list)
        self.grafselect.on_clicked(self.__grafselect_click)
        
        plt.show()
        #~ canvas = FigureCanvasTkAgg(self.main_window, window)
        #~ plt.show()
        #~ canvas.draw()
        #~ w.pack()
        
        
        #~ self.butfile=Button(window,text="Select folder...",height=2,width=20,command=self.__selectdir_click).place(x=200,y=20)
        
        #~ self.butdir=Button(window,text="Select main file...",height=2,width=20,command=self.__selectfile_click).place(x=220,y=20)
        
        #~ self.butupdt=Button(window,text="Refresh graphs...",height=2,width=20,command=self.__update_click).place(x=240,y=20)
        
        
        #~ self.canvas = FigureCanvasTkAgg(self.main_window,window)
        #~ self.canvas.show()
        #~ self.canvas.get_tk_widget().pack(side='top', fill='both', expand=1)
        #~ w.pack()

        #~ window.mainloop()
        
    def __excludes(self,event):
        os.startfile('excludes.ini')
        
    def __selectfile_click(self, event):
        with open('configuration.ini', mode='r') as fich:
            try:
                filename = tkFileDialog.askopenfilename(
                            title = "Select file to analyze",
                            filetypes=[("FORTRAN files", ".f90"),
                                       ("PYTHON files", ".py"),
                                       ("All files",".*")],
                                       initialdir = self.filedir['dirname'])#json.load(fich)["dirname"])
            except:
                filename = tkFileDialog.askopenfilename(
                            title = "Select file to analyze",
                            filetypes=[("FORTRAN files", ".f90"),
                                       ("PYTHON files", ".py"),
                                       ("All files",".*")])
        try:
            filename = os.path.relpath(filename)
        except:
            pass
            
        if filename:
            self.filedir['filename'] = filename

            with open('configuration.ini', mode='w') as fich:
                json.dump(self.filedir, fich, indent = 2)

    def __selectdir_click(self, event):
        with open('configuration.ini', mode='r') as fich:
            try:
                dirname = tkFileDialog.askdirectory(
                                    initialdir = self.filedir['dirname'],#json.load(fich)["dirname"],
                                    title = "Seleccione el directorio de busqueda")
            except:
                dirname = tkFileDialog.askdirectory(
                                    title = "Seleccione el directorio de busqueda")
        try:
            filename = os.path.relpath(dirname)
        except:
            pass
            
        if dirname:
            self.filedir['dirname'] = dirname

            with open('configuration.ini', mode='w') as fich:
                json.dump(self.filedir, fich, indent = 2)

    def __grafselect_click(self, label):
        self.selected_diagram = label
        self.update_diagram()

    def __update_click(self, event):
        
        try: 
            with open("excludes.ini", 'r') as fich:
                self.lstExcludes = json.load(fich)
                print ("lstexcludes LOADED")
                print (self.lstExcludes)
                
        except:
            self.lstExcludes=[]
            print ("lstexcludes EMPTY")
        
        if self.filedir['filename'].lower().endswith(".f90"):
            generate_diagrams_fortran(self.filedir['filename'], self.filedir['dirname'],self.lstExcludes)
        elif self.filedir['filename'].lower().endswith(".py"):
            generate_diagrams_python(self.filedir['filename'], self.filedir['dirname'],self.lstExcludes)
        self.update_diagram()

    def update_diagram(self):
        img = plt.imread(self.diagrams_dicc[self.selected_diagram])
        self.graf_area.cla()
        self.graf_area.imshow(img,interpolation="bilinear")#,origin='lower'

        plt.show()
    
class Excludes():
    def __init__(self):
        ventana=Tk()
        #~ if  'normal' != ventana.state():
        ventana.geometry("400x350+0+0")
        ventana.title("USES excluded")
        lblExcludes=Label(ventana, text="USES excluded").place(x=20,y=100)
        
        self.listExcludes=Listbox(ventana,width=50)
        self.listExcludes.place(x=20,y=120)
        lblExc=Label(ventana,text="USE ").place(x=20,y=20)
        self.entrada=StringVar()
        self.txtExclude=Entry(ventana,textvariable=self.entrada).place(x=50,y=20)
        
        btnExclude=Button(ventana,text="Exclude",height=2,width=20,command=self.addEx).place(x=200,y=20)
        btnClearAll=Button(ventana,text="Clear list", height=2,width=20, command=self.clearall).place(x=200,y=60)
            
        #~ lstExcludes=[]
            
        try: 
            with open("excludes.ini", 'r') as fich:
                self.lstExcludes = json.load(fich)
                print ("lstexcludes LOADED")
                print (self.lstExcludes)
                for Exc in self.lstExcludes:
                    self.listExcludes.insert(END,Exc)
                
        except:
            self.lstExcludes=[]
            print ("lstexcludes EMPTY")
            
    
        ventana.mainloop()
        #~ interfaz = Interface()
        
    def addEx(self):
        #~ print self.entrada
        print (self.entrada.get())
        self.listExcludes.insert(END,self.entrada.get())
        #~ self.listExcludes.update_idletasks()
        print (self.listExcludes)
        self.lstExcludes=self.listExcludes.get(0, END)
        print (self.lstExcludes)    
        print (self.listExcludes.get(0, END))
        #~ data=json.dumps(self.lstEx
        
        #~ os.system("pause")
        with open('excludes.ini', mode='w') as fich:
            json.dump(self.lstExcludes, fich)
            print ("SAVED in excludes.ini")
    
    def clearall(self):
        self.listExcludes.delete(0,END)
        self.lstExcludes=[]
        print (self.lstExcludes)
        with open('excludes.ini', mode='w') as fich:
            json.dump(self.lstExcludes, fich)
            print ("SAVED in excludes.ini")
        
            
if __name__ == '__main__':
    #~ exclude=Excludes()
    interfaz = Interface()
    interfaz.update_diagram()
    plt.show()

