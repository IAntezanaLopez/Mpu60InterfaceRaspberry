import datetime
import smbus
import time
import math
import csv
import os.path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from multiprocessing import Process
from matplotlib import style
from tkinter import Tk, Label, Button, Entry, StringVar, DISABLED, NORMAL, END, W, E, Text, NONE, Scrollbar, RIGHT, BOTTOM, X, Y
import tkinter.font

PWR_MGMT_1   = 0x6B
SMPLRT_DIV   = 0x19
CONFIG       = 0x1A
GYRO_CONFIG  = 0x1B
INT_ENABLE   = 0x38
ACCEL_XOUT_H = 0x3B
ACCEL_YOUT_H = 0x3D
ACCEL_ZOUT_H = 0x3F
GYRO_XOUT_H  = 0x43
GYRO_YOUT_H  = 0x45
GYRO_ZOUT_H  = 0x47
TEMP_OUT0    = 0x41

bus=smbus.SMBus(1)
Device_Address = 0x68

class DeviceProgram:
    def MPU_Init(self):
        bus.write_byte_data(Device_Address, SMPLRT_DIV,7)
        bus.write_byte_data(Device_Address, PWR_MGMT_1, 1)
        bus.write_byte_data(Device_Address, CONFIG, 0)
        bus.write_byte_data(Device_Address, GYRO_CONFIG, 24)
        bus.write_byte_data(Device_Address, INT_ENABLE, 1)

    def read_raw_data(self,addr):
        high = bus.read_byte_data(Device_Address, addr)
        low = bus.read_byte_data(Device_Address, addr+1)
        value = ((high << 8) | low)
        if(value > 32768):
            value = value - 65536
        return value

    def get_temp(self):
        raw_temp = self.read_raw_data(TEMP_OUT0)
        actual_temp = (raw_temp / 340.0) + 36.53
        return actual_temp

class InclinometerProgram(DeviceProgram):
    def __init__(self, master):
        self.master = master
        master.title('Inclinometer')
        self.callId = self.fixedh = None
        self.recstatus = self.check = False
        self.timestr=time.strftime('%Y%m%d-%H%M%S')
        self.idx=self.idy=self.idz=0
        self.mean=np.zeros(shape=(99,12))
        self.message1 = 'Altura fija [m]'
        self.label1_text = StringVar()
        self.label1_text.set(self.message1)
        self.label1 = Label(master, textvariable=self.label1_text)
        self.font = tkinter.font.Font(size=7)
        vcmd = master.register(self.validate)
        self.entry = Entry(master, validate='key', validatecommand=(vcmd, '%P'))
        self.start_button = Button(master,height=3,width=20,text='Start',command=self.start_program)
        self.stop_button=Button(master,height=3,width=20,text='Pause',command=self.pause_program,state=DISABLED)
        self.rec_button=Button(master,height=3,width=20,text='rec',command=self.rec,state=DISABLED)
        self.quit_button = Button(master,height=3,width=20,text='quit',command=self.quit_program)
        self.message2 = 'ver.: 1.110'
        self.message3 = 'Lecturas'
        self.message4 = 'Promedios'
        self.label2_text = StringVar()
        self.label2_text.set(self.message2)
        self.label2 = Label(master, textvariable=self.label2_text)
        self.label3_text = StringVar()
        self.label3_text.set(self.message3)
        self.label3 = Label(master, textvariable=self.label3_text)
        self.label4_text = StringVar()
        self.label4_text.set(self.message4)
        self.label4 = Label(master, textvariable=self.label4_text)
        self.text1=Text(master,width=146,height=10,wrap=NONE,font=self.font)
        #self.hbar1 = Scrollbar(master, orient = 'horizontal')
        #self.hbar1.pack(side = BOTTOM, fill = X)
        #self.vbar1 = Scrollbar(self.text1,command=self.text1.yview)
        #self.vbar1.pack(side = 'right', fill = 'y')
        self.text2=Text(master,width=146,height=10,wrap=NONE,font=self.font)
        self.label1.grid(row=0, column=0, columnspan=4, sticky=W)
        self.entry.grid(row=1, column=0, columnspan=4, sticky=W+E)
        self.start_button.grid(row=2, column=0)
        self.stop_button.grid(row=2, column=1)
        self.rec_button.grid(row=2, column=2)
        self.quit_button.grid(row=2, column=3)
        self.label2.grid(row=3, column=0, columnspan=4, sticky=W+E)
        self.label3.grid(row=4, column=0, columnspan=4, sticky=W)
        self.text1.grid(row=5, column=0, columnspan=4, sticky=W)
        self.label4.grid(row=6, column=0, columnspan=4, sticky=W)
        self.text2.grid(row=7, column=0, columnspan=4, sticky=W)

    def validate(self, new_text):
        if not new_text:
            self.fixedh = None
            return True
        try:
            fixedh = float(new_text)
            if 0 <= fixedh <= 1000:
                self.fixedh = fixedh
                return True
            else:
                return False
        except ValueError:
            return False

    def start_program(self):
        self.start_button.configure(state=DISABLED)
        self.stop_button.configure(state=NORMAL)
        self.rec_button.configure(state=NORMAL)
        if self.fixedh is None and self.recstatus == False:
            self.message2 = 'Corriendo'
        if self.fixedh is not None and self.recstatus == False:
            self.message2 = 'Corriendo con h=%7.4f [m]'%(self.fixedh)
        if self.fixedh is None and self.recstatus == True:
            self.message2 = 'Grabando'
        if self.fixedh is not None and self.recstatus == True:
            self.message2 = 'Grabando con h=%7.4f [m]'%(self.fixedh)
        self.label2_text.set(self.message2)
        self.check = True

    def pause_program(self):
        self.start_button.configure(state=NORMAL)
        self.stop_button.configure(state=DISABLED)
        self.rec_button.configure(state=DISABLED)
        self.message2 = 'Pausa'
        self.label2_text.set(self.message2)
        self.check = False

    def rec(self):
        self.recstatus = not self.recstatus
        if self.recstatus == True and self.fixedh is None:
            self.message2 = 'Grabando'
            self.rec_button.configure(fg='red')
        if self.recstatus == False and self.fixedh is None:
            self.message2 = 'Corriendo'
            self.rec_button.configure(fg='black')
        if self.recstatus == True and self.fixedh is not None:
            self.message2 = 'Grabando con h=%7.4f [m]'%(self.fixedh)
            self.rec_button.configure(fg='red')
        if self.recstatus == False and self.fixedh is not None:
            self.message2 = 'Corriendo con h=%7.4f [m]'%(self.fixedh)
            self.rec_button.configure(fg='black')
        self.label2_text.set(self.message2)

    def quit_program(self):
        if self.callId is not None:
            root.after_cancel(self.callId)
        print('saliendo')
        time.sleep(1)
        if os.path.isfile('%s-mean.csv'%self.timestr):
            plt.savefig('%s-figure.png'%self.timestr,papertype='a4',orientation='landscape',dpi=300)
            self.fig.clf()
            plt.close('all')
        self.master.destroy()

    def rec_program(self,dt,td,z,A,G,X,temp):
        pr=self.mean
        idy=self.idy
        if self.recstatus==True:
            self.idz+=1
            self.text2.insert('end','Grabando: date=%s temp=%6.4f td=%6.4f h=%6.4f Ax=%6.4f Ay=%6.4f Az=%6.4f Gx=%6.4f Gy=%6.4f Gz=%6.4f x=%6.4f y=%6.4f z=%6.4f\n'%(dt,temp,td,z,A[0],A[1],A[2],G[0],G[1],G[2],X[0],X[1],X[2]))
            self.text2.see('end')
            with open('%s-mean.csv'%self.timestr,'a') as csvfile:
                headers=['indice','date','temp','td','h','Ax','Ay','Az','Gx','Gy','Gz','x','y','z']
                writer=csv.DictWriter(csvfile, delimiter=';', lineterminator='\n',fieldnames=headers)
                if csvfile.tell()==0:
                    writer.writeheader()
                writer.writerow({'indice':self.idz,'date':dt,'temp':'%8.4f'%temp,'td':'%8.4f'%td,'h':'%8.4f'%z,'Ax':'%8.4f'%A[0],'Ay':'%8.4f'%A[1],'Az':'%8.4f'%A[2],'Gx':'%8.4f'%G[0],'Gy':'%8.4f'%G[1],'Gz':'%8.4f'%G[2],'x':'%8.4f'%X[0],'y':'%8.4f'%X[1],'z':'%8.4f'%X[2]})
            pr[idy][0]+=temp
            pr[idy][1]+=td
            pr[idy][2]+=z
            for i in range (0,3):
                pr[idy][i+3]+=A[i]
                pr[idy][i+6]+=G[i]
                pr[idy][i+9]+=X[i]
        if(self.recstatus==False and self.idz>0):
            for i in range (0,12):
                pr[idy][i]=pr[idy][i]/self.idz
            self.text2.insert('end','PROMEDIO                                             temp=%6.4f td=%6.4f h=%6.4f Ax=%6.4f Ay=%6.4f Az=%6.4f Gx=%6.4f Gy=%6.4f Gz=%6.4f x=%6.4f y=%6.4f z=%6.4f\n'%(pr[idy][0],pr[idy][1],pr[idy][2],pr[idy][3],pr[idy][4],pr[idy][5],pr[idy][6],pr[idy][7],pr[idy][8],pr[idy][9],pr[idy][10],pr[idy][11]))
            self.text2.see('end')
            with open('%s-mean.csv'%self.timestr,'a') as csvfile:
                headers=['indice','date','temp','td','h','Ax','Ay','Az','Gx','Gy','Gz','x','y','z']
                writer=csv.DictWriter(csvfile, delimiter=';', lineterminator='\n',fieldnames=headers)
                writer.writerow({'indice':'Pr','temp':'%8.4f'%pr[idy][0],'td':'%8.4f'%pr[idy][1],'h':'%8.4f'%pr[idy][2],'Ax':'%8.4f'%pr[idy][3],'Ay':'%8.4f'%pr[idy][4],'Az':'%8.4f'%pr[idy][5],'Gx':'%8.4f'%pr[idy][6],'Gy':'%8.4f'%pr[idy][7],'Gz':'%8.4f'%pr[idy][8],'x':'%8.4f'%pr[idy][9],'y':'%8.4f'%pr[idy][10],'z':'%8.4f'%pr[idy][11]})
            self.idz=0
            self.idy+=1
        self.mean=pr

    def plot_program(self):
        if (self.idz==2 and self.idy==0):
            self.fig,self.mp=plt.subplots(nrows=1,ncols=2)
        with open('%s-mean.csv'%self.timestr,'r') as csvfile:
            plots = np.genfromtxt(csvfile,delimiter=';',skip_header=1)
        h=plots[:,4]
        z=plots[:,13]
        x=plots[:,11]
        y=plots[:,12]
        self.mp[0].clear()
        self.mp[1].clear()
        self.fig.suptitle('Low cost -inclinometer')
        self.mp[0].set(xlabel='Y axis, m',ylabel='Deep, m')
        self.mp[1].set(xlabel='X axis, m',ylabel='Deep, m')
        self.mp[0].plot(x,z,'o',color='k')
        self.mp[1].plot(y,z,'o',color='k')
        for i in range (self.idy):
            self.mp[0].plot(self.mean[i][9],self.mean[i][11],'ro')
            self.mp[1].plot(self.mean[i][10],self.mean[i][11],'ro')
        plt.pause(0.1)

    def calculate(self,td,z,A,G,X):
        if self.idx==0:
            self.ft=time.time()
        if self.fixedh is not None:
            z=self.fixedh
        td=time.time()-self.ft
        temp   = DeviceProgram().get_temp()
        acc_x  = DeviceProgram().read_raw_data(ACCEL_XOUT_H)
        acc_z  = DeviceProgram().read_raw_data(ACCEL_YOUT_H)
        acc_y  = DeviceProgram().read_raw_data(ACCEL_ZOUT_H)
        gyro_x = DeviceProgram().read_raw_data(GYRO_XOUT_H)
        gyro_y = DeviceProgram().read_raw_data(GYRO_YOUT_H)
        gyro_z = DeviceProgram().read_raw_data(GYRO_ZOUT_H)
        A=[((math.atan2(((acc_x/16384.0)),math.sqrt(math.pow(((acc_y/16384.0)), 2)+math.pow(((acc_z/16384.0)), 2))))*(180/math.pi))-0.25,((math.atan2(((acc_y/16384.0)),math.sqrt(math.pow(((acc_x/16384.0)), 2)+math.pow(((acc_z/16384.0)), 2))))*(180/math.pi))-6.5,((math.atan2(((acc_z/16384.0)),math.sqrt(math.pow(((acc_x/16384.0)), 2)+math.pow(((acc_y/16384.0)), 2))))*(180/math.pi))+6.5]
        G=[gyro_x/131.0,gyro_y/131.0,gyro_z/131.0]
        if self.idy>=1:
            idy=self.idy
            za=self.mean[self.idy-1][2]
            Aa=[self.mean[self.idy-1][3],self.mean[self.idy-1][4],self.mean[self.idy-1][5]]
            Xa=[self.mean[self.idy-1][9],self.mean[self.idy-1][10],self.mean[self.idy-1][11]]
            X=[Xa[0]+(((math.sin(A[0]/180*math.pi))*(z-za)/2)+((math.sin(Aa[0]/180*math.pi))*(z-za)/2)),Xa[1]+(((math.sin(A[1]/180*math.pi))*(z-za)/2)+((math.sin(Aa[1]/180*math.pi))*(z-za)/2)),Xa[2]+(((math.sin(A[2]/180*math.pi))*(z-za)/2)+((math.sin(Aa[2]/180*math.pi))*(z-za)/2))]
        return td,z,A,G,X,temp

    def background_program(self):
        if self.check==True:
            if self.idx==0:
                DeviceProgram().MPU_Init()
                print('Starting Device')
            A=G=X=np.zeros(3)
            td=z=0
            dt=datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
            td,z,A,G,X,temp=self.calculate(td,z,A,G,X)
            self.text1.insert('end','date=%s temp=%6.4f td=%6.4f h=%6.4f Ax=%6.4f Ay=%6.4f Az=%6.4f Gx=%6.4f Gy=%6.4f Gz=%6.4f x=%6.4f y=%6.4f z=%6.4f\n'%(dt,temp,td,z,A[0],A[1],A[2],G[0],G[1],G[2],X[0],X[1],X[2]))
            self.text1.see('end')
            with open('%s-data.csv'%self.timestr,'a') as csvfile:
                headers=['date','temp','time','h','Ax','Ay','Az','Gx','Gy','Gz','x','y','z']
                writer=csv.DictWriter(csvfile, delimiter=';', lineterminator='\n',fieldnames=headers)
                if csvfile.tell()==0:
                    writer.writeheader()
                writer.writerow({'date':dt,'temp':'%8.4f'%temp,'time':'%8.4f'%td,'h':'%8.4f'%z,'Ax':'%8.4f'%A[0],'Ay':'%8.4f'%A[1],'Az':'%8.4f'%A[2],'Gx':'%8.4f'%G[0],'Gy':'%8.4f'%G[1],'Gz':'%8.4f'%G[2],'x':'%8.4f'%X[0],'y':'%8.4f'%X[1],'z':'%8.4f'%X[2]})
            self.rec_program(dt,td,z,A,G,X,temp)
            if self.idz>=2:
                self.plot_program()
                if (self.idz==2 and self.idy==0):
                    plt.show(block=False)
            self.idx+=1
        self.callId=root.after(500,self.background_program)

root = Tk()
my_gui = InclinometerProgram(root)
my_gui.background_program()
root.mainloop()
