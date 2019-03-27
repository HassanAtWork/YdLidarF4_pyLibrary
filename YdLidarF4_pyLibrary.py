import serial
import time
import math
name = "PyLidar2"
class YdLidarF4:
    """Deals with F4 version of Ydlidar from http://www.ydlidar.com/"""
    def __init__(self, port):
        """Initialize the connection and set port and baudrate."""
        self.__port = port
        self.__baudrate = 230400
        self.__is_scanning = False
        self.__is_connected = False
        print("F4")
    def Connect(self):
        """Begin serial connection with Lidar by opening serial port.\nReturn success status True/False.\n"""
        try:
            if(not self.__is_connected):
                self.__s=serial.Serial(self.__port, self.__baudrate)
                self.__is_connected = True
                print("connected")
                return True
                self.__stop_motor()
                time.sleep(0.5)
                information = self.__s.read_all()
                if(self.GetHealthStatus()):
                    return True
                else:
                    return False
            else:
                return False
        except Exception as e:
            return False
        
    def __start_motor(self):
        if(self.__is_connected):
            self.__s.setDTR(1)
            time.sleep(0.5)
            return True
        else:
            return False
        
    def __stop_motor(self):
        if(self.__is_connected and (not self.__is_scanning)):
            self.__s.setDTR(0)
            time.sleep(0.5)
            return True
        else:
            return False
    @classmethod
    def __AngleCorr(cls, dist):
        if dist==0:
            return 0
        else:
            return math.atan(21.8*((155.3-dist)/(155.3*dist)))
    @classmethod
    def __addhex(cls, h,l):
        return ord(h)+(ord(l)*0x100)
    @classmethod
    def __calculate(cls, d):
        ddict=[]
        LSN=ord(d[1])
        Angle_fsa = ((YdLidarF4.__addhex(d[2],d[3])>>1)/64.0)+YdLidarF4.__AngleCorr(YdLidarF4.__addhex(d[8],d[9]))
        Angle_lsa = ((YdLidarF4.__addhex(d[4],d[5])>>1)/64.0)+YdLidarF4.__AngleCorr(YdLidarF4.__addhex(d[LSN+6],d[LSN+7]))
        if Angle_fsa<Angle_lsa:
            Angle_diff = Angle_lsa-Angle_fsa
        else:
            Angle_diff = 360+Angle_lsa-Angle_fsa
        for i in range(0,2*LSN,2):
            dist_i = YdLidarF4.__addhex(d[8+i],d[8+i+1])
            Angle_i_tmp = ((Angle_diff/float(LSN))*(i/2))+Angle_fsa+YdLidarF4.__AngleCorr(dist_i)
            if Angle_i_tmp > 360:
                Angle_i = Angle_i_tmp-360
            elif Angle_i_tmp < 0:
                Angle_i = Angle_i_tmp+360
            else:
                Angle_i = Angle_i_tmp
            ddict.append((dist_i,Angle_i))
        return ddict
    @classmethod
    def __checksum(cls, data):
        try:
            ocs = YdLidarF4.__addhex(data[6],data[7])
            LSN = ord(data[1])
            cs = 0x55AA^YdLidarF4.__addhex(data[0],data[1])^YdLidarF4.__addhex(data[2],data[3])^YdLidarF4.__addhex(data[4],data[5])
            for i in range(0,2*LSN,2):
                cs = cs^YdLidarF4.__addhex(data[8+i],data[8+i+1])
            if(cs==ocs):
                return True
            else:
                return False
        except Exception as e:
            return False
        
    def StartScanning(self):
        """Begin the lidar and returns a generator which returns a dictionary consisting angle(degrees) and distance(meters).\nReturn Format : {angle(1):distance, angle(2):distance,....................,angle(360):distance}\nReturn False in case of exception."""
        try:
            if(self.__is_connected and (not self.__is_scanning)):
            #if (self.__is_connected):
                self.__is_scanning = True
                print("scanning is made true")
                self.__s.reset_input_buffer()
                self.__start_motor()
                self.__s.write(chr(0xA5)+chr(0x60))
                time.sleep(0.5)
                self.__s.read(7)
                while self.__is_scanning == True:
                    data = self.__s.read(1024).split("\xaa\x55")[1:-1]
                    distdict = {}
                    countdict = {}
                    for i in range(0,361):
                        distdict.update({i:0})
                        countdict.update({i:0})
                    for e in data:
                        if(ord(e[0])==0):
                            if(self.__checksum(e)):
                                d = self.__calculate(e)
                                for ele in d:
                                    angle = int(round(ele[1]))
                                    prev = distdict[angle]
                                    countdict.update({angle:(countdict[angle]+1)})
                                    curr = prev+((ele[0]-prev)/float(countdict[angle]))
                                    distdict.update({angle:curr})
                    for i in distdict.iterkeys():
                        distdict[i]=int(round(distdict[i]))
                        print(distdict[i])
                    yield distdict

            else:
                yield False
        except Exception as e:
            yield False
            
    def StopScanning(self):
        """Stops scanning but keeps serial connection alive.\nReturn True on success\nReturn False in case of exception."""
        try:
            if(self.__is_connected and self.__is_scanning):
                self.__is_scanning = False
                self.__s.write(chr(0xA5)+chr(0x65))
                time.sleep(0.5)
                self.__s.reset_input_buffer()
                self.__stop_motor()
                return True
            else:
                return False
        except Exception as e:
            return False

    def GetHealthStatus(self):
        """Returns Health status of lidar\nTrue: good\nFalse: Not good or Exception or not connected\n"""
        try:
            if(self.__is_connected):
                if self.__is_scanning == True:
                    self.StopScanning()
                self.__s.write(chr(0xA5)+chr(0x91))
                time.sleep(0.5)
                data = self.__s.read(10)
                if ord(data[9])==0 and ord(data[8])==0 and (ord(data[7])==0 or ord(data[7])==1):
                    return True
                else:
                    return False
            else:
                return False
        except Exception as e:
            return False
        
    def GetDeviceInfo(self):
        """Return device information of lidar in form of dictonary\n{"model_number":model_number,"firmware_version":firmware_version,"hardware_version":hardware_version,"serial_number":serial_number}\nReturn "False" Not good or Exception or not connected"""
        try:
            if(self.__is_connected):
                if self.__is_scanning == True:
                    self.StopScanning()
                self.__s.write(chr(0xA5)+chr(0x90))
                time.sleep(0.5)
                data = self.__s.read(27)
                model_number = str(ord(data[7]))
                firmware_version = str(ord(data[9]))+"."+str(ord(data[8]))
                hardware_version = str(ord(data[10]))
                serial_number = ""
                for i in range(11,20):
                    serial_number = serial_number+str(ord(data[i]))
                return {"model_number":model_number,"firmware_version":firmware_version,"hardware_version":hardware_version,"serial_number":serial_number}
            else:
                return False
        except Exception as e:
            return False
        
    def Reset(self):
        """Reboots the Lidar.\nReturn True on success.\nReturn False in case of exception."""
        try:
            if(self.__is_connected):
                self.__s.write(chr(0xA5)+chr(0x40))
                time.sleep(0.5)
                self.Disconnect()
                self.Connect()
                return True
            else:
                return False
        except Exception as e:
            return False
        
    def Disconnect(self):
        """Stop scanning and close serial communication with Lidar."""
        try:
            if(self.__is_connected):
                self.__s.close()
                self.__is_connected=False
                return True
            else:
                return False
        except Exception as e:
            return False

    def SetDirClockwise(self):
        self.__s.write(chr(0xA5) + chr(0x06))
        print"Clockwise Direction"

    def SetDirCounterClockwise(self):
        self.__s.write(chr(0xA5) + chr(0x07))
        print"CounterClockwise Direction"

    def ToggleRangingFrequency(self): # Toggle the ranging freq b/w 4k & 6k
        self.__s.write(chr(0xA5) + chr(0xD0))
        s = self.__s.read(8)
        print(ord(s[7]))
        if (ord(s[7]) == 1):
            print"6K ranging frequency"
        else:
            print"4K ranging frequency"

    def IncreaseScanFrequency(self): #Increase scanning frequency by 1hz
        self.__s.write(chr(0xA5) + chr(0x0B))
        print("Scanning Frequency is increased by 1 Hz")

    def DecreaseScanFrequency(self): #Decrease scanning frequency by 1hz
        self.__s.write(chr(0xA5) + chr(0x0C))
        print("Scanning Frequency is deccreased by 1 Hz")
