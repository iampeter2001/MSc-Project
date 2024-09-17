import seabreeze
seabreeze.use('cseabreeze')
from seabreeze.spectrometers import list_devices, Spectrometer
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time
import os

def get_spectrometer():
    devices = list_devices()
    if not devices:
        print("No spectrometers found.")
        return None
    print("Available spectrometers:")
    for i, device in enumerate(devices):
        print(f"{i + 1}: {device}")

    while True:
        try:
            index = int(input("Enter the number of the spectrometer you want to use: ")) - 1
            if 0 <= index < len(devices):
                spec = Spectrometer.from_serial_number(devices[index].serial_number)
                print(f"Spectrometer initialized successfully with serial number: {spec.serial_number}")
                return spec
            else:
                print("Invalid selection. Please enter a number from the list.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

def set_integration_time(spec):
    while True:
        try:
            integration_time = int(input("Enter the integration time in microseconds (range: 8000 - 3600000): "))
            if 8000 <= integration_time <= 3600000:
                spec.integration_time_micros(integration_time)
                print(f"Integration time set to {integration_time} microseconds.")
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

def plot_spectrum(wavelengths, data, title, y_label):
    plt.figure()
    plt.plot(wavelengths, data)
    plt.xlabel('Wavelength (nm)')
    plt.ylabel(y_label)
    plt.title(title)
    plt.show()

def save_to_csv(wavelengths, absorbance):
    while True:
        file_path = input("Enter the file path to save the absorbance data (including the file name and .csv extension): ")
        if not file_path.endswith('.csv'):
            print("Invalid file extension. Please ensure the file name ends with .csv")
            continue
        
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory) and directory != '':
            print(f"Directory '{directory}' does not exist. Please enter a valid directory.")
            continue

        try:
            data = {'Wavelength': wavelengths, 'Absorbance': absorbance}
            df = pd.DataFrame(data)
            df.to_csv(file_path, index=False)
            print(f"Data has been written to {file_path}")
            break
        except Exception as e:
            print(f"Failed to save file: {e}. Please try again.")

if __name__ == "__main__":
    spec = get_spectrometer()
    if spec:
        integration_time = set_integration_time(spec)
        print(f"Spectrometer {spec.serial_number} is ready with an integration time of {integration_time} microseconds.")
        
        input("Press Enter to store the reference spectrum...")
        reference_intensities, wavelengths = collect_intensity_arrays(spec, integration_time, num_measurements=10)
        plot_spectrum(wavelengths, reference_intensities, "Reference Spectrum", "Intensity")

        input("Press Enter to collect the background spectrum...")
        background_intensities, _ = collect_intensity_arrays(spec, integration_time, num_measurements=10)
        plot_spectrum(wavelengths, background_intensities, "Background Spectrum", "Intensity")

        input("Press Enter to measure the absorbance of the sample...")
        sample_intensities, _ = collect_intensity_arrays(spec, integration_time, num_measurements=10)
        absorbance = calculate_absorbance(sample_intensities, reference_intensities, background_intensities)
        plot_spectrum(wavelengths, absorbance, "Absorbance Spectrum", "Absorbance")

        save_to_csv(wavelengths, absorbance)
        
        print("Absorbance measurement and data saving completed.")
    else:
        print("No spectrometer initialized.")

