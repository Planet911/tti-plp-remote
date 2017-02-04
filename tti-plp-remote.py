#!/usr/bin/python3

import os, threading, socket, queue, datetime, time

#Do Tk imports like this..
import tkinter as tk
from tkinter import ttk 
#..and prefix the widgets with either tk or ttk
#f1 = tk.Frame(..., bg=..., fg=...)
#f2 = ttk.Frame(..., style=...)
#Then its obvious which widget you are using, at the expense of just a tiny bit more typing

#default_psu_ip = '192.168.1.100'
default_psu_ip ='192.168.128.30'
sample_interval_secs = 2.5

max_volt_setting = 30.0
max_milliamp_setting = 3000



'''
           |-------< commQueueRx <------|
           |                            |
 GUI Thread|-------> commQueueTx >------| Timer Thread <----> ttiPsu object <===== ETHERNET =====> TTi PSU
           |                            |
           |-------> stopFlag --------->|

'''




'''
  _______ _____ __  __ ______ _____        _______ _    _ _____  ______          _____  
 |__   __|_   _|  \/  |  ____|  __ \      |__   __| |  | |  __ \|  ____|   /\   |  __ \ 
    | |    | | | \  / | |__  | |__) |        | |  | |__| | |__) | |__     /  \  | |  | |
    | |    | | | |\/| |  __| |  _  /         | |  |  __  |  _  /|  __|   / /\ \ | |  | |
    | |   _| |_| |  | | |____| | \ \         | |  | |  | | | \ \| |____ / ____ \| |__| |
    |_|  |_____|_|  |_|______|_|  \_\        |_|  |_|  |_|_|  \_\______/_/    \_\_____/ 
                                                                                                                                                                                                                     
'''                                                                                                                                    



class ttiPsu(object):

    def __init__(self, ip, channel=1):
        self.ip = ip
        self.port = 9221 #default port for socket control
        #channel=1 for single PSU and right hand of Dual PSU
        self.channel = channel
        self.ident_string = ''
        self.sock_timeout_secs = 4
        self.packet_end = bytes('\r\n','ascii')
        print('Using port', self.port)

    def send(self, cmd):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(self.sock_timeout_secs)
            s.connect((self.ip, self.port))
            s.sendall(bytes(cmd,'ascii'))

    def recv_end(self, the_socket):
        total_data=[]
        data=''
        while True:
            data=the_socket.recv(1024)
            if self.packet_end in data:
                total_data.append(data[:data.find(self.packet_end)])
                break
            total_data.append(data)
            if len(total_data)>1:
                #check if end_of_data was split
                last_pair=total_data[-2]+total_data[-1]
                if self.packet_end in last_pair:
                    total_data[-2]=last_pair[:last_pair.find(self.packet_end)]
                    total_data.pop()
                    break
        return b''.join(total_data)

    def send_receive_string(self, cmd):
        #print('Cmd', repr(cmd))
        self.mysocket.sendall(bytes(cmd,'ascii'))
        data = self.recv_end(self.mysocket)
        #print('Received', repr(data))
        return data.decode('ascii')
    '''
    def send_receive_string(self, cmd):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(self.sock_timeout_secs)
            s.connect((self.ip, self.port))
            s.sendall(bytes(cmd,'ascii'))
            data = s.recv(1024)
        #print('Received', repr(data))
        return data.decode('ascii')
    '''

    def send_receive_float(self, cmd):
        r = self.send_receive_string(cmd)
        #Eg. '-0.007V\r\n'  '31.500\r\n'  'V2 3.140\r\n'
        r=r.rstrip('\r\nVA') #Strip these trailing chars
        l=r.rsplit() #Split to array of strings
        if len(l) > 0:
            return float(l[-1]) #Convert number in last string to float
        return 0.0

    def send_receive_integer(self, cmd):
        r = self.send_receive_string(cmd)
        return int(r)

    def send_receive_boolean(self, cmd):
        if self.send_receive_integer(cmd) > 0:
            return True
        return False

    def getIdent(self):
        self.ident_string = self.send_receive_string('*IDN?')
        return self.ident_string.strip()

    def getConfig(self):
        cmd = 'CONFIG?'
        v = self.send_receive_integer(cmd)
        return v

    def getAmpRange(self):
        #Supported on PL series
        #Not supported on MX series
        r=0
        try:
            cmd = 'IRANGE{}?'.format(self.channel)
            r = self.send_receive_integer(cmd)
        except:
            pass
        #The response is 1 for Low (500/800mA) range,
        # 2 for High range (3A or 6A parallel)
        # or 0 for no response / not supported
        return r

    def setAmpRangeLow(self):
        #Supported on PL series
        #Not supported on MX series
        cmd = 'IRANGE{} 1'.format(self.channel)
        self.send(cmd)

    def setAmpRangeHigh(self):
        #Supported on PL series
        #Not supported on MX series
        cmd = 'IRANGE{} 2'.format(self.channel)
        self.send(cmd)

    def getOutputIsEnabled(self):
        cmd = 'OP{}?'.format(self.channel)
        v = self.send_receive_boolean(cmd)
        return v

    def getOutputVolts(self):
        cmd = 'V{}O?'.format(self.channel)
        v = self.send_receive_float(cmd)
        return v

    def getOutputAmps(self):
        cmd = 'I{}O?'.format(self.channel)
        v = self.send_receive_float(cmd)
        return v

    def getTargetVolts(self):
        cmd = 'V{}?'.format(self.channel)
        v = self.send_receive_float(cmd)
        return v

    def getTargetAmps(self):
        cmd = 'I{}?'.format(self.channel)
        v = self.send_receive_float(cmd)
        return v

    def getOverVolts(self):
        cmd = 'OVP{}?'.format(self.channel)
        v = self.send_receive_float(cmd)
        return v

    def getOverAmps(self):
        cmd = 'OCP{}?'.format(self.channel)
        v = self.send_receive_float(cmd)
        return v

    def setOutputEnable(self, ON):
        cmd=''
        if ON == True:
            cmd = 'OP{} 1'.format(self.channel)
        else:
            cmd = 'OP{} 0'.format(self.channel)
        self.send(cmd)

    def setTargetVolts(self, volts):
        cmd = 'V{0} {1:2.3f}'.format(self.channel, volts)
        self.send(cmd)

    def setTargetAmps(self, amps):
        cmd = 'I{0} {1:1.3f}'.format(self.channel, amps)
        self.send(cmd)

    def setLocal(self):
        cmd = 'LOCAL'
        self.send(cmd)

    def GetData(self):
        # Gather data from PSU
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            self.mysocket = s
            self.mysocket.settimeout(self.sock_timeout_secs)
            self.mysocket.connect((self.ip, self.port))

            dtime = datetime.datetime.now()
            identity = self.getIdent()
            out_volts = self.getOutputVolts()
            out_amps = self.getOutputAmps()
            target_volts = self.getTargetVolts()
            target_amps = self.getTargetAmps()
            is_enabled = self.getOutputIsEnabled()
            amp_range = self.getAmpRange()
            dataset = DataToGui(True, dtime, identity,
                                    out_volts, out_amps,
                                    target_volts, target_amps,
                                    is_enabled, amp_range)
            return dataset


'''
#Example usage:
tti = ttiPsu('192.168.128.30', channel=2)
print(tti.getIdent())
print('Output: {0:2.2f} V'.format(tti.getOutputVolts()))
print('Output: {0:2.2f} A'.format(tti.getOutputAmps()))
print('OverV: {0:2.2f} V'.format(tti.getOverVolts()))
print('OverI: {0:2.2f} A'.format(tti.getOverAmps()))
print('Config: {}'.format(tti.getConfig()))
print('isEnabled: {}'.format(tti.getOutputIsEnabled()))
print('AmpRange: {}'.format(tti.getAmpRange()))
print('TargetV: {0:2.2f} V'.format(tti.getTargetVolts()))
print('TargetI: {0:2.2f} A'.format(tti.getTargetAmps()))

tti.setTargetVolts(3.14)
tti.setTargetAmps(1.234)
tti.setOutputEnable(True)
tti.setAmpRangeHigh()
tti.setLocal()
'''




class TimerThread(threading.Thread):
    def __init__(self, event, ip, channel):
        threading.Thread.__init__(self)
        self.stopped = event
        self.tti = ttiPsu(ip, channel)
        self.ticktime = 0.2
        self.max_ticks = sample_interval_secs / self.ticktime
        self.tick = self.max_ticks #Do sample soon after connect

    def run(self):
        while not self.stopped.wait(self.ticktime) and root != None:
            self.tick = self.tick+1
            #print(self.tick)
            if not commQueueTx.empty():
                cmd = commQueueTx.get()
                commQueueTx.task_done()
                #print(cmd.command)
                try:
                    if cmd.command == 'OUTPUT OFF':
                        self.tti.setOutputEnable(False)
                    elif cmd.command == 'OUTPUT ON':
                        self.tti.setOutputEnable(True)
                    elif cmd.command == 'SET VOLTS':
                        self.tti.setTargetVolts(cmd.parameter)
                    elif cmd.command == 'SET AMPS':
                        self.tti.setTargetAmps(cmd.parameter)
                    self.tick = self.max_ticks-2 #Do sample soon after a command
                except:
                    print('Failed to send command')
            elif self.tick >= self.max_ticks:
                self.tick = 0
                dataset = None
                try:
                    dataset = self.tti.GetData()
                except socket.timeout:
                    print("Socket connection failure")
                    dataset = DataToGui.error()
                    pass
                commQueueRx.put( dataset ) #send through Queue to gui
                if root != None:
                    root.event_generate('<<PsuGuiDisplayUpdate>>', when='tail') #Tell gui to update
        try:
            #Clean up when thread is closing
            print('Cleanup timer thread')
            if root != None:
                dataset = DataToGui.error()
                commQueueRx.put(dataset)
                root.event_generate('<<PsuGuiDisplayUpdate>>', when='tail')
                self.tti.setLocal() 
        except:
            pass


'''
  _______ _    _ _____  ______          _____   _____         ______ ______          __  __ ______  _____ _____         _____ ______          _____         _____ _____ _____ _   _  _____ 
 |__   __| |  | |  __ \|  ____|   /\   |  __ \ / ____|  /\   |  ____|  ____|        |  \/  |  ____|/ ____/ ____|  /\   / ____|  ____|        |  __ \ /\    / ____/ ____|_   _| \ | |/ ____|
    | |  | |__| | |__) | |__     /  \  | |  | | (___   /  \  | |__  | |__           | \  / | |__  | (___| (___   /  \ | |  __| |__           | |__) /  \  | (___| (___   | | |  \| | |  __ 
    | |  |  __  |  _  /|  __|   / /\ \ | |  | |\___ \ / /\ \ |  __| |  __|          | |\/| |  __|  \___ \\___ \ / /\ \| | |_ |  __|          |  ___/ /\ \  \___ \\___ \  | | | . ` | | |_ |
    | |  | |  | | | \ \| |____ / ____ \| |__| |____) / ____ \| |    | |____         | |  | | |____ ____) |___) / ____ \ |__| | |____         | |  / ____ \ ____) |___) |_| |_| |\  | |__| |
    |_|  |_|  |_|_|  \_\______/_/    \_\_____/|_____/_/    \_\_|    |______|        |_|  |_|______|_____/_____/_/    \_\_____|______|        |_| /_/    \_\_____/_____/|_____|_| \_|\_____|
                                                                                                                                                                                           
'''

commQueueRx = queue.Queue()
commQueueTx = queue.Queue()
stopFlag = threading.Event()
tti_timer_thread = None

class DataToGui(object):
    def __init__(self, valid, dtime, identity, out_volts, out_amps, target_volts, target_amps, is_enabled, amp_range):
        self.valid = valid
        self.dtime = dtime
        self.identity = identity
        self.out_volts = out_volts
        self.out_amps = out_amps
        self.target_volts = target_volts
        self.target_amps = target_amps
        self.is_enabled = is_enabled
        self.amp_range = amp_range
        
    @classmethod
    def error(cls):
        return cls(False, datetime.datetime.now(), None, None, None, None, None, None, None)

class CmdToTTi(object):
    def __init__(self, command, parameter):
        self.command = command
        self.parameter = parameter


'''
   _____ _    _ _____       _______ _    _ _____  ______          _____  
  / ____| |  | |_   _|     |__   __| |  | |  __ \|  ____|   /\   |  __ \ 
 | |  __| |  | | | |          | |  | |__| | |__) | |__     /  \  | |  | |
 | | |_ | |  | | | |          | |  |  __  |  _  /|  __|   / /\ \ | |  | |
 | |__| | |__| |_| |_         | |  | |  | | | \ \| |____ / ____ \| |__| |
  \_____|\____/|_____|        |_|  |_|  |_|_|  \_\______/_/    \_\_____/ 
                                                                         
'''


class FrameIpAddr(ttk.LabelFrame):

    def __init__(self, master):
        super().__init__(master, text='IP Address', borderwidth=10, padding = 10) 

        #Tk variable for comms enable checkbox
        self.chkvar = tk.BooleanVar()
        self.chkvar.set(False)
        self.chkvar.trace('w', self.chkvar_callback)

        self.ipaddr = tk.StringVar()
        self.ipaddr.set(default_psu_ip)

        self.rb_var = tk.IntVar()
        
        #Create styles
        self.style = ttk.Style()
        self.style.configure('base.TLabel')
        
        #Create widgets
        self.label_1 = ttk.Label(self, text='PSU IPv4 Address:', style='base.TLabel', padding=(0,0,10,0)) # padding=(left, top, right, bottom)

        #Validate IPv4 entry
        vaddr = (self.register(self.entryValidateIPv4),'%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        self.entry_1 = ttk.Entry(self, textvariable=self.ipaddr, validate='key', validatecommand=vaddr)
        
        self.chk = ttk.Checkbutton(self, text='Connect', variable = self.chkvar, padding=(10,0,0,0)) # padding=(left, top, right, bottom)
        
        self.label_2 = ttk.Label(self, text='PSU Channel:', style='base.TLabel', padding=(0,0,50,0)) # padding=(left, top, right, bottom)
        self.rb1 = ttk.Radiobutton(self, text='1 (Single or Master)', variable=self.rb_var, value=1)
        self.rb2 = ttk.Radiobutton(self, text='2 (Dual/Triple Slave)', variable=self.rb_var, value=2)
        self.rb3 = ttk.Radiobutton(self, text='3 (Triple Independent)', variable=self.rb_var, value=3)
        
        #Layout widgets
        self.label_1.grid(row=0, sticky=tk.W)
        self.entry_1.grid(row=0, column=1, sticky=tk.W)
        self.chk.grid(row=0, column=2, sticky=tk.E)
        self.label_2.grid(row=1, sticky=tk.W)
        self.rb1.grid(row=1, column=1, sticky=tk.W)
        self.rb2.grid(row=2, column=1, sticky=tk.W)
        self.rb3.grid(row=3, column=1, sticky=tk.W)

        self.rb1.invoke() #Set RadioButton rb1 to checked        

    def entryValidateIPv4(self, action, index, value_if_allowed, prior_value, text, validation_type, trigger_type, widget_name):
        #Validate text entry to be IPv4
        if self.validate_ip(value_if_allowed):
            self.chk.configure(state='normal')
            self.entry_1.configure(foreground ='black')
        else:
            self.chk.configure(state='disabled')
            self.entry_1.configure(foreground ='red')
        return True

    def validate_ip(self, s):
        #Check string is valid IPv4 address
        #Four integers '.' separated all in range 0...255
        a = s.split('.')
        if len(a) != 4:
            return False
        for x in a:
            if not x.isdigit():
                return False
            i = int(x)
            if i < 0 or i > 255:
                return False
        return True

    def chkvar_callback(self, *args):
        #Get here when 'Connect' has been checked or unchecked
        global tti_timer_thread, stopFlag
        if self.chkvar.get() == True:
            ip = self.ipaddr.get()
            self.entry_1.configure(state='disabled')
            self.rb1.configure(state='disabled')
            self.rb2.configure(state='disabled')
            self.rb3.configure(state='disabled')   
            channel = self.rb_var.get()
            print ('Start comms to {0} channel {1}'.format(ip,channel))
            with commQueueRx.mutex:
                commQueueRx.queue.clear()
            with commQueueTx.mutex:
                commQueueTx.queue.clear()
            stopFlag.set()
            stopFlag = threading.Event()
            tti_timer_thread = TimerThread(stopFlag, ip, channel)
            tti_timer_thread.setDaemon(True)
            tti_timer_thread.start()
        else:
            stopFlag.set()
            self.entry_1.configure(state='normal')
            self.rb1.configure(state='normal')
            self.rb2.configure(state='normal')
            self.rb3.configure(state='normal')

   

class FrameShowData(ttk.LabelFrame):
    
    def __init__(self, master):
        super().__init__(master, text='Readings', borderwidth=10, padding = 10)

        self.bool_output_enabled = False
        
        #Check the Rx queue for data when we receive this event
        root.bind('<<PsuGuiDisplayUpdate>>', self.displayUpdate)
        
        self.identity = tk.StringVar()
        self.datestr = tk.StringVar()
        self.powerstr = tk.StringVar()
        self.out_volts = tk.StringVar()
        self.out_amps = tk.StringVar()
        self.target_volts = tk.StringVar()
        self.target_amps = tk.StringVar()
        self.is_enabled = tk.StringVar()
        self.amp_range = tk.StringVar()
        
        self.setDefaultGuiStrings()
        
        #Create styles
        self.style = ttk.Style()
        self.style.configure('base.TLabel')
        self.style.configure('medium.base.TLabel',font=('ariel', 13, 'normal'), padding=(0,10,0,0))
        self.style.configure('large.base.TLabel',font=('ariel', 19, 'bold'), padding=(0,5,0,5)) # padding=(left, top, right, bottom)
        self.style.configure('red.large.base.TLabel', foreground='tomato')
        
        #Create widgets
        self.label_id = ttk.Label(self, textvariable=self.identity , style='base.TLabel')
        self.label_date = ttk.Label(self, textvariable=self.datestr , style='medium.base.TLabel')
        self.label_power= ttk.Label(self, textvariable=self.powerstr , style='large.base.TLabel')
        self.label_vout = ttk.Label(self, textvariable=self.out_volts , style='large.base.TLabel')
        self.label_iout = ttk.Label(self, textvariable=self.out_amps , style='large.base.TLabel')
        self.label_tvolts = ttk.Label(self, textvariable=self.target_volts , style='medium.base.TLabel')
        self.label_tamps = ttk.Label(self, textvariable=self.target_amps , style='medium.base.TLabel')
        self.label_enabled = ttk.Label(self, textvariable=self.is_enabled , style='large.base.TLabel')
        self.label_range = ttk.Label(self, textvariable=self.amp_range , style='base.TLabel')

        #Validate volts entry to be a float
        vfloat = (self.register(self.entryValidateFloat_volts),'%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        self.entry_volts = ttk.Entry(self, font = 'ariel 13', justify='center', width=10, validate='key', validatecommand=vfloat) #'ariel 13 bold'
        #Validate amps entry to be an integer (mA)
        vint = (self.register(self.entryValidateInteger_mA),'%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        self.entry_amps  = ttk.Entry(self, font = 'ariel 13', justify='center', width=10, validate='key', validatecommand=vint)
        #Process entry value when user hits return key
        self.entry_volts.bind('<Return>', self.set_volts)
        self.entry_amps.bind('<Return>', self.set_amps)        

        self.button_on_off = ttk.Button(self, text='Switch Output', command=self.buttonClick)
        
        #Layout widgets  sticky=tk.W
        self.label_id.grid(row=0, columnspan=2)
        self.label_date.grid(row=1, columnspan=2)
        self.label_power.grid(row=2, columnspan=2)
        self.label_vout.grid(row=3)
        self.label_iout.grid(row=3, column=1)
        self.label_tvolts.grid(row=4)
        self.label_tamps.grid(row=4, column=1)
        self.label_enabled.grid(row=7, columnspan=2, padx=0,pady=20)
        self.label_range.grid(row=6, column=1)
        self.entry_volts.grid(row=5, padx=40,pady=0)
        self.entry_amps.grid(row=5, column=1, padx=40,pady=0)
        self.button_on_off.grid(row=8, columnspan=2, sticky=tk.NSEW)

    def setDefaultGuiStrings(self):
        self.identity.set('Instrument ID')
        self.datestr.set('Date & Time')
        self.powerstr.set('Watts')
        self.out_volts.set('Volts')
        self.out_amps.set('Amps')
        self.target_volts.set('Setpoint Volts')
        self.target_amps.set('Setpoint mA')
        self.is_enabled.set('Output ON/OFF')
        self.amp_range.set('[Output Range Hi/Lo]')
        
    def entryValidateFloat_volts(self, action, index, value_if_allowed, prior_value, text, validation_type, trigger_type, widget_name):
        #Validate text entry to be a float
        #print(value_if_allowed)
        if value_if_allowed == '' or value_if_allowed == '.':
            return True
        if len(text) == 1:
            if text in '0123456789.':
                try:
                    f=float(value_if_allowed)
                    if f >= 0 and f <= float(max_volt_setting): #Volt range limit (some PL psu's are highish voltage)
                        return True
                except:
                    pass
            return False
        return True

    def entryValidateInteger_mA(self, action, index, value_if_allowed, prior_value, text, validation_type, trigger_type, widget_name):
        #Validate text entry to be an integer
        #print(value_if_allowed)
        if value_if_allowed == '':
            return True
        if len(text) == 1:
            if text in '0123456789':
                try:
                    i=int(value_if_allowed)
                    if i >= 0 and i <= int(max_milliamp_setting): #mA limit
                        return True
                except:
                    pass
            return False
        return True

    def setIndicator(self):
        #Set the gui output on/off indication
        if self.bool_output_enabled == False or stopFlag.is_set():
            self.label_enabled.configure(style='large.base.TLabel')
            self.label_vout.configure(style='large.base.TLabel')
            self.label_iout.configure(style='large.base.TLabel')
            self.is_enabled.set('Output is off')
        else:
            self.label_enabled.configure(style='red.large.base.TLabel')
            self.label_vout.configure(style='red.large.base.TLabel')
            self.label_iout.configure(style='red.large.base.TLabel')            
            self.is_enabled.set('Output is ON!')

    def displayUpdate(self, event):
        if stopFlag.is_set():
            self.setIndicator()
            self.setDefaultGuiStrings()
            self.entry_volts.delete(0, 'end') #clear entry widgets
            self.entry_amps.delete(0, 'end')
            return
        while not commQueueRx.empty(): #ensure we empty the queue to get latest data
            data = commQueueRx.get() #get a DataToGui object from the queue
            commQueueRx.task_done()
            nowstr = data.dtime.strftime('%c') #see http://strftime.org/
            if not data.valid:
                self.setDefaultGuiStrings()
                print(nowstr, 'Error no data')
                self.datestr.set(nowstr)
                self.powerstr.set('No response from PSU')
            else:
                #Populate display widgets with data
                self.identity.set(data.identity)                
                self.datestr.set(nowstr)                
                self.target_volts.set('Setpoint {0:2.3f} V'.format(data.target_volts))
                self.target_amps.set('Setpoint {0:4.0f} mA'.format(data.target_amps*1000))
                if data.amp_range == 1:
                    self.amp_range.set('[Low Range]')
                elif data.amp_range == 2:
                    self.amp_range.set('[High Range]')
                else:
                    self.amp_range.set('')
                self.bool_output_enabled = data.is_enabled
                self.setIndicator()
                if self.bool_output_enabled:
                    self.out_volts.set('{0:2.3f} V'.format(data.out_volts))
                    self.out_amps.set('{0:4.0f} mA'.format(data.out_amps*1000))
                    #When the output is enabled show the output power in milli-Watts or Watts
                    power = data.out_amps * data.out_volts
                    if power < 0.001:
                        power = 0
                    if power < 1:
                        self.powerstr.set('{0:3.0f} mW'.format(power*1000))
                    else:
                        self.powerstr.set('{0:3.2f} W'.format(power))
                else:
                    self.out_volts.set('{0:2.3f} V'.format(data.target_volts))
                    self.out_amps.set('{0:4.0f} mA'.format(data.target_amps*1000))
                    self.powerstr.set(' ')

    def buttonClick(self):
        if self.bool_output_enabled == False:
            print('Set output ON')
            cmd = CmdToTTi('OUTPUT ON',0)
        else:
            print('Set output OFF')
            cmd = CmdToTTi('OUTPUT OFF',0)
        commQueueTx.put(cmd)

    def set_volts(self,event):
        try:
            v = float(self.entry_volts.get())
            if v < 0 or v > max_volt_setting:
                #self.entry_volts.configure(foreground ='red')
                return            
            print('Set target {0:2.3f} Volts'.format(v))
            cmd = CmdToTTi('SET VOLTS', v)
            commQueueTx.put(cmd)
            #self.entry_volts.configure(foreground ='black')
            self.entry_volts.delete(0, 'end') #Clear entry box
        except:
            pass

    def set_amps(self,event):
        try:            
            i = float(self.entry_amps.get())
            if i < 0 or i > max_milliamp_setting:
                #self.entry_volts.configure(foreground ='red')
                return            
            print('Set target {0} mA'.format(int(i)))
            cmd = CmdToTTi('SET AMPS', float(i)/1000.0)
            commQueueTx.put(cmd)
            #self.entry_amps.configure(foreground ='black')
            self.entry_amps.delete(0, 'end') #Clear entry box
        except:
            pass




class Application:
    
    def __init__(self, root):
        self.root = root
        self.root.title('TTi PL-P Series Remote Control')
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        self.init_widgets()        
            
    def init_widgets(self):        
        #Create frames
        self.frame_window = ttk.Frame(self.root, padding=10)
        self.frame_ipaddr = FrameIpAddr(self.frame_window)
        self.frame_dataview = FrameShowData(self.frame_window)
        #Layout frames
        self.frame_window.grid(row=0, sticky='ew')        
        self.frame_ipaddr.grid(row=0, sticky='ew')
        self.frame_dataview.grid(row=1, sticky='ew')



'''
   _____ _______       _____ _______                 _____  _____  
  / ____|__   __|/\   |  __ \__   __|          /\   |  __ \|  __ \ 
 | (___    | |  /  \  | |__) | | |            /  \  | |__) | |__) |
  \___ \   | | / /\ \ |  _  /  | |           / /\ \ |  ___/|  ___/ 
  ____) |  | |/ ____ \| | \ \  | |          / ____ \| |    | |     
 |_____/   |_/_/    \_\_|  \_\ |_|         /_/    \_\_|    |_|     
                                                                   
'''

root = None

def on_closing():
    #if tk.messagebox.askokcancel('Quit', 'Do you want to quit?'):
    #    root.destroy()
    root.destroy()
    if stopFlag != None:
        stopFlag.set()
    


if __name__ == '__main__':
    #global root #Not required here as python 'if' doesn't start a new scope
    root = tk.Tk()
    #root.geometry('400x200+200+200')
    Application(root)
    root.protocol('WM_DELETE_WINDOW', on_closing)
    root.mainloop()
    root = None
