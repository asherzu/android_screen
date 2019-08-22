import io
import subprocess
import threading
from queue import Queue
import logging
import time

from PIL import Image, ImageTk
import tkinter as tk
from io import StringIO,BytesIO 


class Keypad(tk.Tk):
    def __init__(self,*args,**kargs):
        tk.Tk.__init__(self,*args,**kargs)
        tk.Tk.wm_title(self,"Keypad by monkey")
        
        # initial default variable
        self.zoom_value = 1
        container = tk.Frame(self)
        container.pack(side="top")#, fill="both", expand=True)
        self.container = container
        
        line1 = self.make_line()
        
        self.make_button(line1,"BACK","press BACK")
        self.make_button(line1,"HOME","press HOME")
        self.make_button(line1,"MENU","press MENU")
        self.make_button(line1,"+","press VOLUME_UP")
        self.make_button(line1,"-","press VOLUME_DOWN")
        
        line2 = self.make_line()
        self.make_button(line2,"Up","press DPAD_UP")
        self.make_button(line2,"Down","press DPAD_DOWN")
        self.make_button(line2,"Left","press DPAD_LEFT")
        self.make_button(line2,"Right","press DPAD_RIGHT")
        self.make_button(line2,"Center","press DPAD_CENTER")
        
        line3 = self.make_line()
        self.make_button(line3,"Wake","wake")
        # self.make_button(line3,"Sleep","wake")
        self.make_zoom_button(line3)
        
        lineCanvas = self.make_line()
        
        
        self.start_monkey_server_thread()
        
        self.start_monkey_thread()
        self.start_screen_cap_thread(lineCanvas)
        
    def make_line(self):
        line = tk.Frame(self.container)
        line.pack(side=tk.TOP)
        return line
    def start_monkey_thread(self):
        monkey_queue = Queue()
        x = threading.Thread(target=thread_monkey_event, args=(monkey_queue,))
        x.daemon = True
        x.start()
        self.monkey_queue = monkey_queue
    def start_monkey_server_thread(self):
        x = threading.Thread(target=monkey_server_thread, args=())
        x.daemon = True
        x.start()
        
    def OnMouseDown(self,event):
        x, y = event.x, event.y
        self.penDown = event
        logging.info('down {}, {}'.format(x, y))
    def OnMouseUp(self,event):
        x, y = event.x, event.y
        logging.info('UP {}, {}'.format(x, y))
        x0, y0 = self.penDown.x, self.penDown.y
        if self.zoom_value != 1:
            scale = 1.0
            if self.zoom_value > 1:
                scale = 1.0/self.zoom_value
            else:
                scale = (2 - self.zoom_value)
            x0,y0 = int(x0*scale), int(y0*scale)
            x,y = int(x*scale), int(y*scale)
        if abs(x0 - x) < 10 and abs(y0 - y) < 10:
            cmd = 'tap  {} {}'.format(x0,y0)
            self.send_cmd(cmd)
        else:
            self.send_cmd('touch down {} {}'.format(x0,y0))
            self.send_cmd('touch move {} {}'.format(x,y))
            self.send_cmd('touch up {} {}'.format(x,y))
    def start_screen_cap_thread(self,line):
        label = tk.Label(line)
        label.pack(side=tk.TOP)
        label.bind("<ButtonPress-1>", self.OnMouseDown)
        label.bind("<ButtonRelease-1>", self.OnMouseUp)
        self.canvas = label
        
        x = threading.Thread(target=screen_capture_thread, args=(self.canvas,self))
        x.daemon = True
        x.start()
    def send_cmd(self,cmd):
        logging.info("Keypad send_cmd %s",cmd)
        self.monkey_queue.put(cmd)
    def make_zoom_button(self,line):
        zoom_in = tk.Button(line, text="Zoom in", width = 8, command=lambda :self.zoom_in())
        zoom_out = tk.Button(line, text="Zoom out", width = 8, command=lambda :self.zoom_out())
        zoom_in.pack(side=tk.LEFT)
        zoom_out.pack(side=tk.LEFT)
    def zoom_in(self):
        self.zoom_value += 1
        logging.info("zoom value %d",self.zoom_value)
    def zoom_out(self):
        self.zoom_value -= 1
        logging.info("zoom value %d",self.zoom_value)
    def make_button(self,line,name,cmd):
        button = tk.Button(line,text = name,width = 8,command = lambda cmd = cmd:self.send_cmd(cmd))
        button.pack(side=tk.LEFT)

def pull_image():
        cmd='adb shell screencap -p'
        process = subprocess.Popen(cmd, shell=True,
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE)
        out, err = process.communicate()
        if out.startswith(bytearray(b"\x89\x50\x4e\x47")):
            
            pngheader=bytearray(b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a")
            while not out.startswith(pngheader):
                out = out.replace(b"\x0D\x0A",b"\x0A")
                #print len(out)
            return out
            #os.system("echo 1 >1.flag")
        return None

def monkey_server_thread():
    telnet_cmd=['adb', 'shell', 'monkey --port 1080']
    proc = subprocess.Popen(
                            telnet_cmd,
                            # shell=True,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            )
    stdin = io.TextIOWrapper(
                            proc.stdin,
                            encoding='utf-8',
                            line_buffering=True,  # send data on newline
                            )
    stdout = io.TextIOWrapper(
                            proc.stdout,
                            encoding='utf-8',
                            )
    while True:
        # logging.info("Moneky server thread read line")
        output = stdout.readline()
        if output != "":
            logging.info(output.rstrip())

def screen_capture_thread(canvas,app):
    logging.info("screen_capture_thread")
    while True:
        logging.info("pull image")
        png = pull_image()
        logging.info("pull image finish zoom_value %d",app.zoom_value)
        # print(repr(png))
        image=Image.open(BytesIO (png))
        width, height = image.size
        if app.zoom_value != 1:
            
            if app.zoom_value >1:
                width *= app.zoom_value
                height *= app.zoom_value
            else:
                width /=(2-app.zoom_value)
                height /=(2-app.zoom_value)
            width = int(width)
            height = int(height)
            if width == 0 or height == 0:
                width = 5
                height = 5
            
            image=image.resize((width,height))
            logging.info("resize %d %d",width,height)
        image1 = ImageTk.PhotoImage(image)
        canvas.configure(image=image1)
def thread_monkey_event(queue):
    #
    # Moneky thread function
    #
    logging.info("monkey event thread start")
    time.sleep(3)
    
    telnet_cmd=['adb', 'shell', 'busybox telnet 127.0.0.1:1080']
    
    proc = subprocess.Popen(
                            telnet_cmd,
                            # shell=True,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            )
    stdin = io.TextIOWrapper(
                            proc.stdin,
                            encoding='utf-8',
                            line_buffering=True,  # send data on newline
                            )
    stdout = io.TextIOWrapper(
                            proc.stdout,
                            encoding='utf-8',
                            )
    while True:
        cmd = queue.get()
        logging.info("monkey cmd %s",cmd)
        stdin.write(cmd+'\n')
        output = stdout.readline()
        print(output.rstrip())
    
    

if __name__ == '__main__':
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")
    # monkey_queue = Queue.Queue()
    # x = threading.Thread(target=thread_monkey_event, args=(monkey_queue,))
    # x.start()
    
    app = Keypad()
    # app.geometry("320x240")
    app.mainloop()



