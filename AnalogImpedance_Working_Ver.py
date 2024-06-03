"""
   DWF Python Example
   Author:  Digilent, Inc.
   Revision:  2018-07-28

   Requires:                       
       Python 2.7, 3
"""

from ctypes import *
from dwfconstants import *
import math
import time
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import pandas as pd
from datetime import datetime
import tkinter as tk
from tkinter import ttk
import os
import csv 
import threading
from tkinter import messagebox

# creation of directory
output_dir = "Impedance_Data_Collection"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

measurements_running = False
        
#How the impedance Anaylyzer actully works and makes Measurments
def makeMeasurement(steps, startFrequency, stopFrequency, reference, amplitude, makeMeasureTime):
    #Capture Current Date
    current_date = datetime.now()
    nowY = current_date.year
    nowD = current_date.day
    nowM = current_date.month
    now = str(nowM)+ '-' + str(nowD)+ '-' + str(nowY)

    #Capture Current Time
    t = time.localtime()
    current_time = time.strftime("%H-%M-%S", t)

    if sys.platform.startswith("win"):
        dwf = cdll.LoadLibrary("dwf.dll")
    elif sys.platform.startswith("darwin"):
        dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
    else:
        dwf = cdll.LoadLibrary("libdwf.so")

    version = create_string_buffer(16)
    dwf.FDwfGetVersion(version)
    print("DWF Version: "+str(version.value))

    hdwf = c_int()
    szerr = create_string_buffer(512)
    print("Opening first device\n")
    dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

    if hdwf.value == hdwfNone.value:
        dwf.FDwfGetLastErrorMsg(szerr)
        print(str(szerr.value))
        print("failed to open device")
        quit()

    # this option will enable dynamic adjustment of analog out settings like: frequency, amplitude...
    dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(3)) 

    sts = c_byte()

    # print("Reference: "+str(reference)+" Ohm  Frequency: "+str(startFrequency)+" Hz ... "+str(stopFrequency/1e3)+" kHz for nanofarad capacitors")
    dwf.FDwfAnalogImpedanceReset(hdwf)
    dwf.FDwfAnalogImpedanceModeSet(hdwf, c_int(8)) # 0 = W1-C1-DUT-C2-R-GND, 1 = W1-C1-R-C2-DUT-GND, 8 = AD IA adapter
    dwf.FDwfAnalogImpedanceReferenceSet(hdwf, c_double(reference)) # reference resistor value in Ohms
    dwf.FDwfAnalogImpedanceFrequencySet(hdwf, c_double(start_numeric_value)) # frequency in Hertz
    dwf.FDwfAnalogImpedanceAmplitudeSet(hdwf, c_double(amplitude)) # 1V amplitude = 2V peak2peak signal
    dwf.FDwfAnalogImpedanceConfigure(hdwf, c_int(1)) # start
    time.sleep(2)

    rgHz = [0.0]*steps
    rgRs = [0.0]*steps
    rgXs = [0.0]*steps
    rgPhase = [0.0]*steps
    rgZ = [0.0]*steps
    rgRv = [0.0]*steps # real voltage
    rgIv = [0.0]*steps # imag voltage
    rgRc = [0.0]*steps # real current
    rgIc = [0.0]*steps # imag current

    for i in range(steps):
        hz = stop_numeric_value * pow(10.0, 1.0*(1.0*i/(steps-1)-1)*math.log10(stop_numeric_value/start_numeric_value)) # exponential frequency steps
        print("Step: "+str(i)+" "+str(hz)+"Hz")

        # Add a label to display the step count
        log_label = tk.Label(frame_settings, text="Step Count: " + str(i + 1))
        log_label.grid(row=7, column=0, padx=5, pady=5, sticky='NW')

        # Update the step count label on the GUI thread
        total_steps = int(steps_entry.get())

        # Function to update step count
        # def update_step_count(current_step, total_steps, hz):
        #     log_label.config(text=f"Step Count: {current_step}/{total_steps - 1}")
        #     root.update_idletasks()

        # root.after(0, update_step_count, i, total_steps , hz)

        rgHz[i] = hz
        dwf.FDwfAnalogImpedanceFrequencySet(hdwf, c_double(hz)) # frequency in Hertz
        # if settle time is required for the DUT, wait and restart the acquisition
        # time.sleep(0.01) 
        # dwf.FDwfAnalogInConfigure(hdwf, c_int(1), c_int(1))
        while True:
            if dwf.FDwfAnalogImpedanceStatus(hdwf, byref(sts)) == 0:
                dwf.FDwfGetLastErrorMsg(szerr)
                print(str(szerr.value))
                quit()
            if sts.value == 2:
                break
        resistance = c_double()
        reactance = c_double()
        phase = c_double()
        impedance = c_double()
        realVoltage = c_double()
        imagVoltage = c_double()
        realCurrent = c_double()
        imagCurrent = c_double()

        dwf.FDwfAnalogImpedanceStatusMeasure(hdwf, DwfAnalogImpedanceResistance, byref(resistance))
        dwf.FDwfAnalogImpedanceStatusMeasure(hdwf, DwfAnalogImpedanceReactance, byref(reactance))
        dwf.FDwfAnalogImpedanceStatusMeasure(hdwf, DwfAnalogImpedanceImpedancePhase , byref(phase))
        dwf.FDwfAnalogImpedanceStatusMeasure(hdwf, DwfAnalogImpedanceImpedance, byref(impedance))
        dwf.FDwfAnalogImpedanceStatusMeasure(hdwf, DwfAnalogImpedanceVreal, byref(realVoltage))      
        dwf.FDwfAnalogImpedanceStatusMeasure(hdwf, DwfAnalogImpedanceVimag, byref(imagVoltage)) 
        dwf.FDwfAnalogImpedanceStatusMeasure(hdwf, DwfAnalogImpedanceIreal, byref(realCurrent))      
        dwf.FDwfAnalogImpedanceStatusMeasure(hdwf, DwfAnalogImpedanceIimag, byref(imagCurrent))                
        # add other measurements here (impedance, impedanceVReal impedanceVImag, impedancelreal, impedancelimag)

        rgRs[i] = abs(resistance.value) # absolute value for logarithmic plot
        rgXs[i] = abs(reactance.value)
        rgPhase[i] = (phase.value * 180)/3.14159265358979
        rgZ[i] = abs(impedance.value)
        rgRv[i] = abs(realVoltage.value)
        rgIv[i] = abs(imagVoltage.value)
        rgRc[i] = abs(realCurrent.value)
        rgIc[i] = abs(imagCurrent.value)

        now_time = now + '_at_' + current_time + '_data'

        data = pd.DataFrame({
                             'Frequency(Hz)': rgHz,'Impedance(Ohm)' : rgZ, 'Absolute Resistance(Ohm)': rgRs, 
                             'Absolute Reactance(Ohm)': rgXs, 'Phase(degrees)': rgPhase, 'Real Voltage(volts)': rgRv, 'Imaginary Voltage(volts)': rgIv, 
                              'Real Current(amps)': rgRc, 'Imaginary Current(amps)': rgIc })

        # Save the DataFrame to a CSV file
        csv_filename = os.path.join(output_dir, f"Impedance_Data_{now}_{current_time}.csv")
        data.to_csv(csv_filename, index=False)
        
        for iCh in range(2):
            warn = c_int()
            dwf.FDwfAnalogImpedanceStatusWarning(hdwf, c_int(iCh), byref(warn))
            if warn.value:
                dOff = c_double()
                dRng = c_double()
                dwf.FDwfAnalogInChannelOffsetGet(hdwf, c_int(iCh), byref(dOff))
                dwf.FDwfAnalogInChannelRangeGet(hdwf, c_int(iCh), byref(dRng))
                if warn.value & 1:
                    print("Out of range on Channel "+str(iCh+1)+" <= "+str(dOff.value - dRng.value/2)+"V")
                if warn.value & 2:
                    print("Out of range on Channel "+str(iCh+1)+" >= "+str(dOff.value + dRng.value/2)+"V")

    dwf.FDwfAnalogImpedanceConfigure(hdwf, c_int(0)) # stop
    dwf.FDwfDeviceClose(hdwf)

    print(f"Data saved to {csv_filename}")

    # Create the first graph
    fig1, ax1 = plt.subplots(figsize=(2,1))
    ax1.plot(rgXs, rgRs)
    fig1.suptitle('Nyquist', fontsize= 8)
    fig1.patch.set_alpha(0.0)  # Make the figure background transparent
    ax1.patch.set_alpha(0.0)   # Make the axes background transparent
    plt.xscale("log")
    plt.yscale("log")
    canvas1 = FigureCanvasTkAgg(fig1, master=frame_graphs)
    plt.xticks(fontsize=2)
    plt.yticks(fontsize=2)
    plt.xlabel("Reactance", fontsize = 5)
    plt.ylabel("Resistance", fontsize = 5)
    canvas1.draw()
    canvas1.get_tk_widget().grid(row=0, column=0, padx=5, pady=5, sticky='nsew')

    # tool bar functionality for first graph
    toolbar_frame1 = tk.Frame(frame_graphs)
    toolbar_frame1.grid(row=1, column=0, padx=2, pady=2, sticky='ew')
    toolbar1 = NavigationToolbar2Tk(canvas1, toolbar_frame1)

    # Create the second graph
    fig1, ax2 = plt.subplots(figsize=(2,1))
    # ax2.set_title('Impedance')
    fig1.suptitle('Impedance', fontsize = 8)
    # ax1.legend()
    ax2.plot(rgHz, rgZ)
    plt.xscale("log")
    plt.yscale("log")
    plt.xticks(fontsize=2)
    plt.yticks(fontsize=2)
    plt.xlabel("Frequency", fontsize = 5)
    plt.ylabel("Impedance", fontsize = 5)
    canvas2 = FigureCanvasTkAgg(fig1, master=frame_graphs)
    canvas2.draw()
    canvas2.get_tk_widget().grid(row=0, column=1, rowspan=3, padx=5, pady=5, sticky='nsew')

    # Create the third graph
    fig1, ax3 = plt.subplots(figsize=(2,1))
    # ax3.set_title('Phase Angle')
    fig1.suptitle('Phase Angle', fontsize=8)
    # ax3.legend()
    ax3.plot(rgHz, rgPhase)
    plt.xscale("log")
    plt.yscale("log")
    plt.xticks(fontsize=2)
    plt.yticks(fontsize=2)
    plt.xlabel("Frequency", fontsize = 5)
    plt.ylabel("Phase Angle", fontsize = 5)
    canvas3 = FigureCanvasTkAgg(fig1, master=frame_graphs)
    canvas3.draw()
    canvas3.get_tk_widget().grid(row=2, column=0, padx=5, pady=5, sticky='nsew')
    
# end of def makeMeasurement 

#Extracts Steps value from GUI
def update_steps(*args):
    global steps_int
    try:
        # Convert the entry to an integer
        steps_int = int(steps.get())
        if steps_int < 0:
            # raise ValueError("Steps cannot be negative.")
            messagebox.showerror('Invalid Input', 'Steps must be a positive integer')
            print("Updated Steps to:", steps_int)

    except ValueError as e:
        print("Invalid input for steps. Please enter a positive integer")

# Dictionary for frequency values
frequency_dict = {
    "1 Hz": 1,
    "10 Hz": 10,
    "100 Hz": 100,
    "1 kHz": 1000,
    "10 kHz": 10000,
    "100 kHz": 100000,
    "1 MHz": 1000000,
    "10 MHz": 10000000,
    "15 MHz": 15000000
}

startFrequency = None
stopFrequency = None 
amplitude = None
reference = None

def on_select_start(event):
    global startFrequency
    global start_numeric_value
    startFrequency = startF_dropdown.get()
    start_numeric_value = frequency_dict[startFrequency]
    print(f"Selected: {startFrequency}, Numeric Value: {start_numeric_value}")

    return start_numeric_value

# Function to handle selection for stop frequency
def on_select_stop(event):
    global stopFrequency
    global stop_numeric_value
    stopFrequency = stopF_dropdown.get()
    stop_numeric_value = frequency_dict[stopFrequency]
    print(f"Selected: {stopFrequency}, Numeric Value: {stop_numeric_value}")

    return stop_numeric_value

# Dictionary for amplitude values
amplitude_dict = {
        "2 V" : 2,
        "1 V" : 1,
        "500 mV" : 0.5,
        "200 mV" : 0.2,
        "100 mV" : 0.1,
        "50 mV" : 0.05,
        "20 mV" : 0.02,
        "10 mV" : 0.01,
        "5 mV" : 0.005,
        "0 V" : 0
}

# Function to handle selection for amplitude
def on_select_amp(event):
    global amplitude
    global amplitude_numeric_value
    amplitude = amplitude_dropdown.get()
    amplitude_numeric_value = amplitude_dict[amplitude]
    print(f"Selected: {amplitude}, Numeric Value: {amplitude_numeric_value}")

    return amplitude_numeric_value

# Dictionary for resistance values
reference_dict = {
    "1 MΩ" : 1000000,
    "100 kΩ" : 100000,
    "10 kΩ" : 10000,
    "1 kΩ" : 1000,
    "100 Ω" : 100,
    "10 Ω" : 10
}

# Function to handle selection for resistance
def on_select_res(event):
    global reference
    global reference_numeric_value
    reference = resistance_dropdown.get()
    reference_numeric_value = reference_dict[reference]
    print(f"Selected: {reference}, Numeric Value: {reference_numeric_value}")

    return reference_numeric_value

# Function to start the measurement
def measure():
    if not measurements_running:
        return
    global startFrequency, stopFrequency, amplitude, reference
    # Update global variables with the selected values
    steps = int(steps_entry.get())
    startFrequency = on_select_start(startFrequency)
    stopFrequency = on_select_stop(stopFrequency)
    reference = on_select_res(reference)
    amplitude = on_select_amp(amplitude)
    measure_interval = float(measure_interval_entry.get())

    if measurements_running:
        interval = int(measure_interval_entry.get()) * 60
        root.after(interval, measure)

    # Call the function to make the measurement
    threading.Thread(target=makeMeasurement(steps, startFrequency, stopFrequency, reference, amplitude, measure_interval)).start()

# Create the main window
root = tk.Tk()
fig, ax = plt.subplots()
root.title("Measurement Settings")

# Make the main window's grid layout adjustable
root.columnconfigure(0, weight=1)
root.columnconfigure(1, weight=1)
root.columnconfigure(2, weight=1)
root.rowconfigure(0, weight=1)
root.rowconfigure(1, weight=1)
root.rowconfigure(2, weight=2)
root.rowconfigure(3, weight=2)

# Create a frame for the settings
frame_settings = tk.Frame(root)
frame_settings.grid(row=0, column=0, rowspan=2, columnspan=3, padx=10, pady=10, sticky='nsew')

# Configure grid layout for frame_settings
frame_settings.columnconfigure(0, weight=1)
frame_settings.columnconfigure(1, weight=1)
frame_settings.columnconfigure(2, weight=1)
frame_settings.rowconfigure(0, weight=1)
frame_settings.rowconfigure(1, weight=1)
frame_settings.rowconfigure(2, weight=1)

# Create a frame for the graphs
frame_graphs = tk.Frame(root)
frame_graphs.grid(row=2, column=0, rowspan=2, columnspan=3, padx=10, pady=10, sticky='nsew')

# Make the frame expand with the window
frame_graphs.columnconfigure(0, weight=1)
frame_graphs.columnconfigure(1, weight=1)
frame_graphs.columnconfigure(2, weight=1)
frame_graphs.rowconfigure(0, weight=1)
frame_graphs.rowconfigure(1, weight=1)

# Set the window size
root.geometry("1200x600")

# Make the main window's grid layout adjustable
root.columnconfigure(0, weight=1)
root.columnconfigure(1, weight=1)
root.columnconfigure(2, weight=1)
root.rowconfigure(0, weight=1)
root.rowconfigure(1, weight=1)
root.rowconfigure(2, weight=2)
root.rowconfigure(3, weight=2)

# Create a frame for the settings
frame_settings = tk.Frame(root)
frame_settings.grid(row=0, column=0, rowspan=2, columnspan=3, padx=10, pady=10, sticky='nsew')

# Configure grid layout for frame_settings
frame_settings.columnconfigure(0, weight=1)
frame_settings.columnconfigure(1, weight=1)
frame_settings.columnconfigure(2, weight=1)
frame_settings.rowconfigure(0, weight=1)
frame_settings.rowconfigure(1, weight=1)
frame_settings.rowconfigure(2, weight=1)

# Add settings widgets to frame_settings
steps_label = tk.Label(frame_settings, text="Steps:")
steps_label.grid(row=0, column=0, padx=0, pady=0, sticky='NW')
steps_entry = tk.Entry(frame_settings)
steps_entry.insert(0, "151")  # Set default value to 151
steps_entry.grid(row=1, column=0, padx=0, pady=0, sticky='NW')

# Add Start Frequency entry to frame_settings
startF_label = tk.Label(frame_settings, text="Start Frequency")
startF_label.grid(row=0, column=1, padx=5, pady=5, sticky='NW')
startF_dropdown = ttk.Combobox(frame_settings, values=list(frequency_dict.keys()))
startF_dropdown.bind("<<ComboboxSelected>>", on_select_start)
startF_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky='NW')
startF_dropdown.current(list(frequency_dict.keys()).index("100 Hz"))  # Set default value to 100 Hz

# Add Stop Frequency entry to frame_settings
stopF_label = tk.Label(frame_settings, text="Stop Frequency")
stopF_label.grid(row=0, column=2, padx=5, pady=5, sticky='NW')
stopF_dropdown = ttk.Combobox(frame_settings, values=list(frequency_dict.keys()))
stopF_dropdown.bind("<<ComboboxSelected>>", on_select_start)
stopF_dropdown.grid(row=1, column=2, padx=5, pady=5, sticky='NW')
stopF_dropdown.current(list(frequency_dict.keys()).index("1 MHz"))  # Set default value to 100 Hz

# Add amplitude entry to frame_settings
amplitude_label = tk.Label(frame_settings, text="Amplitude")
amplitude_label.grid(row=2, column=0, padx=5, pady=5, sticky='NW')
amplitude_dropdown = ttk.Combobox(frame_settings, values=list(amplitude_dict.keys()))
amplitude_dropdown.bind("<<ComboboxSelected>>", on_select_amp)
amplitude_dropdown.grid(row=3, column=0, padx=5, pady=5, sticky='NW')
amplitude_dropdown.current(list(amplitude_dict.keys()).index("1 V"))  # Set default value to 100 Hz

# Add reference resistance entry to frame_settings
resistance_label = tk.Label(frame_settings, text="Reference Resistance")
resistance_label.grid(row=2, column=1, padx=5, pady=5, sticky='NW')
resistance_dropdown = ttk.Combobox(frame_settings, values=list(reference_dict.keys()))
resistance_dropdown.bind("<<ComboboxSelected>>", on_select_res)
resistance_dropdown.grid(row=3, column=1, padx=5, pady=5, sticky='NW')
resistance_dropdown.current(list(reference_dict.keys()).index("1 kΩ"))  # Set default value to 100 Hz

# Add Measurement Interval entry to frame_settings
measure_interval_label = tk.Label(frame_settings, text="Measure Intervals for Every  ")
measure_interval_label.grid(row=2, column=2, padx=5, pady=5, sticky='NW')
measure_interval_entry = ttk.Entry(frame_settings)
measure_interval_entry.grid(row=3, column=2, padx=5, pady=5, sticky='NW')
measure_interval_entry.insert(0, "1")  # Default value

measure_interval_entry_time_length = ttk.Combobox(frame_settings, textvariable='interval')
measure_interval_entry_time_length.grid(row=4, column=2, padx=5, pady=5, sticky='NW')
measure_interval_entry_time_length['values'] = ('minute', 'hour')
measure_interval_entry_time_length.current(0)

# Add a Text widget to display log messages
# log_text = tk.Text(frame_graphs, wrap='word', height=10)
# log_text.grid(row=8, column=0, columnspan=3, padx=5, pady=5, sticky='nsew')

# Add a label to display the step count
# log_label = tk.Label(frame_settings, text="Step: 0")
# log_label.grid(row=7, column=0, padx=5, pady=5, sticky='NW')

# # Add step count label
# step_count_label = tk.Label(frame_settings, text="Step Count: 0/0")
# step_count_label.grid(row=7, column=0, padx=5, pady=5, sticky='NW')

# starts measurement process
def start_measurements():
    global measurements_running 
    measurements_running = True
    measure()

def stop_measurements():
    global measurements_running
    measurements_running = False

# start button
start_button = ttk.Button(
    frame_settings,
    text='Start Measurement',
    command=start_measurements
)
start_button.grid(column=0, row=6, padx=10, pady=10, sticky='NW')

stop_button = ttk.Button(
    frame_settings,
    text='Stop',
    command=stop_measurements
)
stop_button.grid(column=1, row=6, padx=10, pady=10, sticky='NW')

# Run the application
root.mainloop()
