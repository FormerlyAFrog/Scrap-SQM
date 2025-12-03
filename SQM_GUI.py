"""
- Sends 'R' to request a reading
- Expects: "LUX:<value>,SQM:<value>"
"""

import tkinter as tk
from tkinter import ttk, messagebox
import time
import serial
import serial.tools.list_ports

# Global serial object
ser = None

BAUD_RATE = 115200  # Must match Serial.begin on Arduino


def list_serial_ports():  # Return a list of available serial port names.
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports]


def refresh_ports():  # Update ports upon press
    ports = list_serial_ports()
    port_combo["values"] = ports
    if ports:
        port_combo.current(0)  # select first port
    else:
        port_combo.set("")  # clear selection


def connect_serial():
    global ser

    port = port_combo.get().strip()
    try:
        # Close any previous serial connection
        # If serial is busy (via terminal, program or anything) it will not run
        # I2C only supports one at a time
        if ser and ser.is_open:
            ser.close()

        # Actually connect & Say Connected
        ser = serial.Serial(port, BAUD_RATE, timeout=3, write_timeout=3)
        status_var.set(f"Connected to {port}")
        print(f"[DEBUG] Connected to {port} at {BAUD_RATE} baud")

        # give the nano some time to catch it's breath (Reset)
        time.sleep(2.0)

        # Clear input buffer
        ser.reset_input_buffer()

    # A Little redundant but it works and isn't too bad
    except serial.SerialException as e:
        ser = None
        status_var.set("Not connected")
        messagebox.showerror("Connection error", f"Could not open port {port}:\n{e}")
        print(f"[ERROR] Could not open port {port}: {e}")


def get_reading():
    """
    Send 'R' and expect:
      LUX:XXXX,SQM:XXXX For all X as some real
    """
    global ser

    if ser is None or not ser.is_open:
        messagebox.showwarning("Not connected", "Please connect to a serial port first.")
        return

    try:
        # reset input buffer
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        # Send R (plus newline, which Arduino will mostly ignore)
        print("[DEBUG] Sending 'R'...")  # Only in terminal for debug
        ser.write(b"R\n")  # b is for byte!
        ser.flush()

        # Wait for reply
        print("[DEBUG] Waiting for reply line...")
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        print(f"[DEBUG] Raw line received: {repr(line)}")

        if not line:
            messagebox.showwarning("Timeout", "No data received (timeout).")
            # most annoying error of all time !!1!!111! ^^^
            raw_var.set("<no data>")
            lux_var.set("--")
            sqm_var.set("--")
            return

        # Show the raw line
        raw_var.set(line)

        # Try to parse LUX and SQM
        try:
            lux_str, sqm_str = parse_lux_sqm(line)
            lux_var.set(lux_str)
            sqm_var.set(sqm_str)
        except ValueError as e:
            # Raw line shown; just indicate parsing failed
            lux_var.set("--")
            sqm_var.set("--")
            print(f"[ERROR] Parse error: {e}")
            messagebox.showerror("Parse error", f"Could not understand data from Arduino:\n{e}")

    except serial.SerialException as e:
        messagebox.showerror("Serial error", f"Serial communication error:\n{e}")
        print(f"[ERROR] Serial communication error: {e}")


def parse_lux_sqm(line):
    """
    Parse :
      LUX:<value>,SQM:<value>
    Returns lux & sqm's values as strings.
    Raises ValueError if format is wrong.
    """
    if "LUX:" not in line or "SQM:" not in line:
        raise ValueError(f"No LUX:/SQM: markers in line: {line}")

    parts = line.split(",", 1)
    # First error is when data parsing is wrong. Often from arduino code changes or GUI Parsing Changes
    if len(parts) != 2:
        raise ValueError(f"Wrong number of fields (expected 2, got {len(parts)}). Line: {line}")
    lux_part = parts[0].strip() # take first part of two strings in list
    sqm_part = parts[1].strip() # take second part

    # If this error Arduino sending some error
    if not lux_part.startswith("LUX:") or not sqm_part.startswith("SQM:"):
        raise ValueError(f"Line does not start with LUX: and SQM:. Line: {line}")

    # Extract the numeric strings
    lux_str = lux_part.split(":", 1)[1].strip()
    sqm_str = sqm_part.split(":", 1)[1].strip()

    # Validate they’re numeric (allow "NaN" if for some reason you point it at a light or the sun or something)
    float(lux_str)
    if sqm_str.upper() != "NAN":
        float(sqm_str)

    return lux_str, sqm_str


# ----------------- GUI SETUP -----------------

root = tk.Tk()
root.title("Simple SQM (TSL2591) GUI")

# Top frame: port selection and connect
top_frame = tk.Frame(root, padx=10, pady=10)
top_frame.pack(fill=tk.BOTH)

# Port label
tk.Label(top_frame, text="Serial port:").grid(row=0, column=0, sticky="w")

# Combobox for port list
port_combo = ttk.Combobox(top_frame, width=25, state="readonly")
port_combo.grid(row=0, column=1, sticky="w", padx=(5, 5))

# Populate initial ports
refresh_ports()

# Refresh
refresh_button = tk.Button(top_frame, text="Refresh", command=refresh_ports)
refresh_button.grid(row=0, column=2, padx=(5, 0))

# Connect
connect_button = tk.Button(top_frame, text="Connect", command=connect_serial)
connect_button.grid(row=0, column=3, padx=(10, 0))

# Status
status_var = tk.StringVar(value="Not connected")
status_label = tk.Label(top_frame, textvariable=status_var, fg="blue")
status_label.grid(row=1, column=0, columnspan=4, sticky="w", pady=(5, 0))

# Middle frame: reading display
mid_frame = tk.Frame(root, padx=10, pady=10)
mid_frame.pack(fill=tk.BOTH)

# Get Reading
get_button = tk.Button(mid_frame, text="Get Reading", command=get_reading)
get_button.grid(row=0, column=0, columnspan=2, pady=(0, 10))

# LUX label & value
tk.Label(mid_frame, text="LUX:").grid(row=1, column=0, sticky="e", padx=(0, 5))
lux_var = tk.StringVar(value="--")
tk.Label(mid_frame, textvariable=lux_var, width=12).grid(row=1, column=1, sticky="w")

# SQM label & value
tk.Label(mid_frame, text="SQM (mag/arcsec²):").grid(row=2, column=0, sticky="e", padx=(0, 5))
sqm_var = tk.StringVar(value="--")
tk.Label(mid_frame, textvariable=sqm_var, width=12).grid(row=2, column=1, sticky="w")

# Raw line label & value
tk.Label(mid_frame, text="Raw line:").grid(row=3, column=0, sticky="e", padx=(0, 5), pady=(10, 0))
raw_var = tk.StringVar(value="")
tk.Label(mid_frame, textvariable=raw_var, width=40, anchor="w").grid(row=3, column=1, sticky="w", pady=(10, 0))

root.mainloop()
