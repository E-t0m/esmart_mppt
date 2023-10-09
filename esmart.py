# Library for communicating with eSmart 3 MPPT charger
# skagmo.com, 2018
# modified for data export

import time, serial #, struct, socket, requests


# States
STATE_START = 0
STATE_DATA = 1

REQUEST_MSG0	= b"\xaa\x01\x01\x01\x00\x03\x00\x00\x1e\x32"
LOAD_OFF		= b"\xaa\x01\x01\x02\x04\x04\x01\x00\xfe\x13\x38"
LOAD_ON 		= b"\xaa\x01\x01\x02\x04\x04\x01\x00\xfd\x13\x39"

DEVICE_MODE = ["IDLE", "CC", "CV", "FLOAT", "START"]

class esmart:
	def __init__(self):
		self.state = STATE_START
		self.data = []
		self.fields = {}
		self.callback = False
		self.port = ""
		self.timeout = 0
		self.name = ""
		self.ext_temp_name = "bat"

	def __del__(self):
		self.close()

	def set_callback(self, function):
		self.callback = function

	def set_name(self, name):
		self.name = name

	def set_ext_temp_name(self, name):
		self.ext_temp_name = name

	def open(self, port):
		self.ser = serial.Serial(port,9600,timeout=0.1)
		self.port = port

	def close(self):
		try:
			self.ser.close()
			self.ser = False
		except AttributeError:
			pass

	def send(self, pl):
		self.ser.write(self.pack(pl))

	def parse(self, data):
		for c in data:
			if (self.state == STATE_START):
				if (c == 0xaa):
					# Start character detected
					self.state = STATE_DATA
					self.data = []
					self.target_len = 255
				#else:
					#print c

			elif (self.state == STATE_DATA):
				self.data.append(c)
				# Received enough of the packet to determine length
				if (len(self.data) == 5):
					self.target_len = 6 + self.data[4]

				# Received whole packet
				if (len(self.data) == self.target_len):
					self.state = STATE_START

					#print " ".join("{:02x}".format(ord(c)) for c in self.data)

					# Source 3 is MPPT device
					if (self.data[2] == 3):
						msg_type = self.data[3]

						# Type 0 packet contains most data
						if (self.data[3] == 0):
							self.fields = {}
							self.fields['chg_mode']	= int.from_bytes(self.data[7:9],	byteorder='little')
							self.fields['pv_volt']	= int.from_bytes(self.data[9:11],	byteorder='little') / 10.0
							self.fields['bat_volt']	= int.from_bytes(self.data[11:13],	byteorder='little') / 10.0
							self.fields['chg_cur']	= int.from_bytes(self.data[13:15],	byteorder='little') / 10.0
							self.fields['load_volt']	= int.from_bytes(self.data[17:19],	byteorder='little') / 10.0
							self.fields['load_cur']	= int.from_bytes(self.data[19:21],	byteorder='little') / 10.0
							self.fields['chg_power']	= int.from_bytes(self.data[21:23],	byteorder='little')
							self.fields['load_power']= int.from_bytes(self.data[23:25],	byteorder='little')
							self.fields['ext_temp']	= self.data[25]
							self.fields['int_temp']	= self.data[27] if self.data[27] < 200 else self.data[27] - 256
							self.fields['soc']		= self.data[29]
							self.fields['co2_gram']	= int.from_bytes(self.data[33:35], byteorder='little')
							self.fields['name']		= self.name
							self.fields['ext_temp_name']	= self.ext_temp_name
							self.callback(self.fields)

	def tick(self):
		try:
			while (self.ser.inWaiting()):
				self.parse(self.ser.read(100))

			# Send poll packet to request data every x seconds
			if (time.time() - self.timeout) > 1:
				self.ser.write(REQUEST_MSG0)
				self.timeout = time.time()
				#time.sleep(0.5)
				#self.ser.write(LOAD_OFF)

		except IOError:
			print("Serial port error, fixing")
			self.ser.close()
			opened = 0
			while not opened:
				try:
					self.ser = serial.Serial(self.port,38400,timeout=0)
					#time.sleep(0.1)
					if self.ser.read(100):
						opened = 1	
					else:
						self.ser.close()		
				except serial.serialutil.SerialException:
					time.sleep(0.5)
					self.ser.close()
			print("Error fixed")

