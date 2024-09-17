import seabreeze
seabreeze.use('cseabreeze')
from seabreeze.spectrometers import list_devices, Spectrometer
import numpy as np
import pandas as pd
import time
import serial
import os
from datetime import datetime
import matplotlib.pyplot as plt

class SyringePump:
    def __init__(self, port, baudrate=9600, timeout=1):
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        if self.ser.is_open:
            print(f"Connected to syringe pump on port {port}")
        else:
            print(f"Failed to connect to syringe pump on port {port}")

    def send_command(self, command):
        command += '\r'
        self.ser.write(command.encode())
        time.sleep(0.5)  # Increase the delay to ensure the command is processed
        response = self.ser.readline().decode('latin1').strip()
        print(f"Command sent: {command.strip()}, Response: {response}")
        return response

    def set_flow_rate(self, rate, unit):
        command = f"RAT {rate} {unit}"
        return self.send_command(command)

    def start_pump(self):
        command = "RUN"
        return self.send_command(command)

    def stop_pump(self):
        command = "STP"
        return self.send_command(command)

    def close(self):
        self.ser.close()
        print(f"Closed connection to syringe pump on port {self.ser.port}")

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

def collect_intensity_arrays(spec, integration_time, num_measurements=10):
    intensities_list = []
    wavelengths = spec.wavelengths()
    
    for _ in range(num_measurements):
        intensities = spec.intensities()
        intensities_list.append(intensities)
        time.sleep(integration_time / 1_000_000)
    
    averaged_intensities = np.mean(intensities_list, axis=0)
    return averaged_intensities, wavelengths

def calculate_absorbance(intensities_sample, intensities_reference, intensities_background):
    with np.errstate(divide='ignore', invalid='ignore'):
        absorbance = -1 * np.log10((intensities_sample - intensities_background) / (intensities_reference - intensities_background))
    return absorbance

def save_to_csv(wavelengths, absorbance, methyl_orange_concentration):
    data = {'Wavelength': wavelengths, 'Absorbance': absorbance}
    df = pd.DataFrame(data)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_name = f'absorbance_data_{timestamp}_{methyl_orange_concentration}mM.csv'
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    file_path = os.path.join(desktop_path, file_name)
    df.to_csv(file_path, index=False)
    print(f"Data has been written to {file_path}")

def plot_spectrum(wavelengths, intensities, title):
    plt.figure()
    plt.plot(wavelengths, intensities)
    plt.xlabel('Wavelength (nm)')
    plt.ylabel('Intensity')
    plt.title(title)
    plt.show()

def main():
    spec = get_spectrometer()
    if not spec:
        return
    integration_time = set_integration_time(spec)

    input("Press Enter to store the reference spectrum...")
    reference_intensities, wavelengths = collect_intensity_arrays(spec, integration_time)
    plot_spectrum(wavelengths, reference_intensities, "Reference Spectrum")

    input("Press Enter to collect the background spectrum...")
    background_intensities, _ = collect_intensity_arrays(spec, integration_time)
    plot_spectrum(wavelengths, background_intensities, "Background Spectrum")

    haucl4_pump = SyringePump('COM7')
    sodium_citrate_pump = SyringePump('COM8')
    milliq_water_pump = SyringePump('COM9')
    methyl_orange_pump = SyringePump('COM10')

    flow_rate_unit = input("Enter the unit for flow rate (uL/min, mL/min, uL/hr, mL/hr): ").strip()
    haucl4_flow_rate = input("Enter the flow rate for HAuCl4 Syringe Pump (COM7): ")
    sodium_citrate_flow_rate = input("Enter the flow rate for Sodium Citrate Syringe Pump (COM8): ")
    milliq_flow_rate_total = float(input("Enter the total flow rate for MilliQ Water and Methyl Orange Syringe Pumps: ").strip())

    haucl4_pump.set_flow_rate(haucl4_flow_rate, flow_rate_unit)
    sodium_citrate_pump.set_flow_rate(sodium_citrate_flow_rate, flow_rate_unit)

    while True:
        input("Press Enter to update the concentration and flow rates of MilliQ and Methyl Orange pumps...")
        methyl_orange_concentration = float(input("Enter the desired concentration of methyl orange (in mM): "))
        methyl_orange_flow_rate = (methyl_orange_concentration / 2.5) * milliq_flow_rate_total
        milliq_flow_rate = milliq_flow_rate_total - methyl_orange_flow_rate

        # Stop the pumps before updating the flow rates
        milliq_water_pump.stop_pump()
        methyl_orange_pump.stop_pump()

        # Update flow rates before starting the pumps
        milliq_water_pump.set_flow_rate(milliq_flow_rate, flow_rate_unit)
        methyl_orange_pump.set_flow_rate(methyl_orange_flow_rate, flow_rate_unit)

        print(f"Updated MilliQ Water Pump Flow Rate: {milliq_flow_rate} {flow_rate_unit}")
        print(f"Updated Methyl Orange Pump Flow Rate: {methyl_orange_flow_rate} {flow_rate_unit}")

        # Start MilliQ and Methyl Orange pumps together
        milliq_water_pump.start_pump()
        methyl_orange_pump.start_pump()
        print("MilliQ and Methyl Orange pumps started.")
        
        # Wait for 60 seconds
        time.sleep(60)

        # Start HAuCl4 pump
        haucl4_pump.start_pump()
        print("HAuCl4 pump started.")
        
        # Wait for another 30 seconds
        time.sleep(30)

        # Start Sodium Citrate pump
        sodium_citrate_pump.start_pump()
        print("Sodium Citrate pump started.")

        # Wait for user to press Enter to measure absorbance
        input("Press Enter to measure absorbance...")

        # Collect sample spectrum
        sample_intensities, _ = collect_intensity_arrays(spec, integration_time)
        absorbance = calculate_absorbance(sample_intensities, reference_intensities, background_intensities)
        plot_spectrum(wavelengths, absorbance, "Absorbance Spectrum")
        save_to_csv(wavelengths, absorbance, methyl_orange_concentration)

        choice = input("Press 'Q' to quit or Enter to continue with another methyl orange concentration: ").strip().lower()
        if choice == 'q':
            break

if __name__ == "__main__":
    main()



