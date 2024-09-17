import seabreeze
seabreeze.use('cseabreeze')
from seabreeze.spectrometers import list_devices, Spectrometer
import numpy as np
import pandas as pd
import serial
import time
import os
from datetime import datetime
import matplotlib.pyplot as plt

def get_spectrometer():
    devices = list_devices()
    if not devices:
        print("No spectrometers found.")
        return None
    print("Available spectrometers:", devices)
    serial_number = input("Enter the serial number of the spectrometer you want to use: ")
    return Spectrometer.from_serial_number(serial_number)

def set_integration_time(spec):
    while True:
        try:
            integration_time = int(input("Enter the integration time in microseconds (range: 8000 - 3600000): "))
            if 8000 <= integration_time <= 3600000:
                spec.integration_time_micros(integration_time)
                return integration_time
            else:
                print("Integration time out of range. Please enter a value between 8000 and 3600000.")
        except ValueError:
            print("Invalid input. Please enter an integer value.")

def collect_intensity_arrays(spec, integration_time, num_measurements=1):
    intensities_list = []
    wavelengths = spec.wavelengths()
    
    for _ in range(num_measurements):
        intensities = spec.intensities()
        intensities_list.append(intensities)
        time.sleep(integration_time / 1_000_000)
    
    averaged_intensities = np.mean(intensities_list, axis=0)
    return averaged_intensities, wavelengths

def calculate_absorbance(intensities_sample, intensities_light_on, intensities_light_off):
    with np.errstate(divide='ignore', invalid='ignore'):
        absorbance = -1 * np.log10((np.array(intensities_sample) - np.array(intensities_light_off)) / (np.array(intensities_light_on) - np.array(intensities_light_off)))
    return absorbance

def save_to_csv(wavelengths, absorbance, directory_path):
    data = {'Wavelength': wavelengths, 'Absorbance': absorbance}
    df = pd.DataFrame(data)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_name = f'absorbance_data_{timestamp}.csv'
    file_path = os.path.join(directory_path, file_name)
    df.to_csv(file_path, index=False)
    print("Data has been written to", file_path)

def plot_and_save(wavelengths, intensities, title, save_path):
    plt.plot(wavelengths, intensities)
    plt.xlabel('Wavelength')
    plt.ylabel('Intensity')
    plt.title(title)
    plt.savefig(save_path)
    plt.show()

# Initialize syringe pumps
class SyringePump:
    def __init__(self, port, baudrate=9600, timeout=1):
        print(f"Initializing serial connection on port: {port}")
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        print("Serial connection initialized.")

    def is_open(self):
        status = self.ser.is_open
        print(f"Serial port open: {status}")
        return status

    def send_command(self, command):
        print(f"Sending command: {command}")
        command += '\r' # Correct line ending character
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

def main():
    # Initialize spectrometer
    spec = get_spectrometer()
    if not spec:
        return

    # Set integration time for spectrometer
    integration_time = set_integration_time(spec)

    # Prompt user to store reference spectrum
    input("Press Enter to store reference spectrum...")
    intensities_light_on, wavelengths_light_on = collect_intensity_arrays(spec, integration_time, num_measurements=20)
    plot_and_save(wavelengths_light_on, intensities_light_on, 'Reference Spectrum', 'C:/Users/py23pp/Desktop/Peter/baseline_with_light_on.png')

    # Prompt user to store background spectrum
    input("Press Enter to store background spectrum...")
    intensities_light_off, wavelengths_light_off = collect_intensity_arrays(spec, integration_time, num_measurements=20)
    plot_and_save(wavelengths_light_off, intensities_light_off, 'Background Spectrum', 'C:/Users/py23pp/Desktop/Peter/baseline_with_light_off.png')

    # Initialize and configure syringe pumps
    port1 = 'COM4' # Two inlet pump
    port2 = 'COM5' # One inlet pump

    try:
        pump1 = SyringePump(port=port1)
        pump2 = SyringePump(port=port2)

        if pump1.is_open() and pump2.is_open():
            diameter1 = float(input("Enter the diameter for the two inlet pump (in mm): "))
            diameter2 = float(input("Enter the diameter for the one inlet pump (in mm): "))

            volume1 = float(input("Enter the volume for the two inlet pump (in ml): "))
            volume2 = float(input("Enter the volume for the one inlet pump (in ml): "))

            flow_rate1 = float(input("Enter the flow rate for the two inlet pump: "))
            unit1 = input("Enter the unit for the two inlet pump flow rate (MH, UH, UM, MM): ")

            flow_rate2 = float(input("Enter the flow rate for the one inlet pump: "))
            unit2 = input("Enter the unit for the one inlet pump flow rate (MH, UH, UM, MM): ")

            # Set parameters for pump 1 (two inlet pump)
            pump1.set_syringe_diameter(diameter1)
            pump1.set_volume(volume1)
            pump1.set_flow_rate(flow_rate1, unit1)

            # Set parameters for pump 2 (one inlet pump)
            pump2.set_syringe_diameter(diameter2)
            pump2.set_volume(volume2)
            pump2.set_flow_rate(flow_rate2, unit2)

            # Prompt user to enter delay time for the one inlet pump
            delay_time = float(input("Enter the delay time in seconds for the one inlet pump: "))

            # Prompt user to start both pumps
            input("Press Enter to start both pumps...")

            # Start both pumps
            pump1.start_pump()

            # Wait for delay time before starting pump2
            time.sleep(delay_time)

            # Start one inlet pump after delay
            pump2.start_pump()

            # Wait for user to press Enter to measure absorbance
            input("Press Enter to measure absorbance...")

            # Collect intensity arrays for the sample
            intensities_sample, wavelengths_sample = collect_intensity_arrays(spec, integration_time, num_measurements=20)

            # Calculate absorbance
            absorbance = calculate_absorbance(intensities_sample, intensities_light_on, intensities_light_off)

            # Save absorbance to CSV
            save_to_csv(wavelengths_sample, absorbance, 'C:/Users/py23pp/Desktop/Peter/Time evolution')

            # Plot absorbance
            plot_and_save(wavelengths_sample, absorbance, 'Sample Absorbance', 'C:/Users/py23pp/Desktop/Peter/sample_absorbance.png')

            # Keep running until user presses 'Q' to stop pumps
            while True:
                action = input("Press 'Q' to stop both pumps: ")
                if action.lower() == 'q':
                    # Stop both pumps
                    pump1.stop_pump()
                    pump2.stop_pump()
                    break

    except Exception as e:
        print(f"Error: {e}")

    finally:
        pump1.close()
        pump2.close()

if __name__ == "__main__":
    main()

