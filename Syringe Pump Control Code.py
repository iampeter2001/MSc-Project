
import serial
import time

class SyringePump:
    def __init__(self, port, baudrate=9600, timeout=1):
        print(f"Initializing serial connection on port: {port}")
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        if self.ser.isOpen():
            print("Serial connection initialized.")
        else:
            print("Failed to open serial connection.")
            raise Exception("Failed to open serial connection.")

    def is_open(self):
        status = self.ser.is_open
        print(f"Serial port open: {status}")
        return status

    def send_command(self, command):
        command += '\r'  # Ensure correct line ending character
        print(f"Sending command: {command}")
        self.ser.write(command.encode())
        print(f"Encoded command: {command.encode()}")
        time.sleep(0.1)
        response = self.ser.readline().decode().strip()
        print(f"Received response: {response}")
        return response

    def set_syringe_diameter(self, diameter):
        command = f"DIA {diameter}"
        return self.send_command(command)

    def set_flow_rate(self, rate, unit):
        command = f"RAT {rate} {unit}"
        return self.send_command(command)

    def set_volume(self, volume):
        command = f"VOL {volume}"
        return self.send_command(command)

    def start_pump(self):
        command = "RUN"
        return self.send_command(command)

    def stop_pump(self):
        command = "STP"
        return self.send_command(command)

    def close(self):
        print("Closing serial connection.")
        self.ser.close()
        print("Serial connection closed.")

if __name__ == "__main__":
    port = input("Enter the COM port for the syringe pump (e.g., COM7): ")
    try:
        pump = SyringePump(port=port)
        if pump.is_open():
            diameter = float(input("Enter the syringe diameter in mm: "))
            rate = float(input("Enter the flow rate: "))
            unit = input("Enter the unit for flow rate (e.g., UM, MM, UH, MH): ")
            volume = float(input("Enter the volume in mL: "))
            pump.set_syringe_diameter(diameter)
            pump.set_flow_rate(rate, unit)
            pump.set_volume(volume)
            pump.start_pump()
            input("Press Enter to stop the pump...")
            pump.stop_pump()
        pump.close()
    except Exception as e:
        print(f"Error: {e}")

