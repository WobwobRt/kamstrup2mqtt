#!/usr/bin/env python3
# Testscript voor uitlezen van Kamstrup Multical parameter 0x56 (temp1)

from kamstrup_meter import kamstrup   # <-- pas dit aan naar de bestandsnaam van je originele script, zonder .py
import logging

# Optioneel: logging op console aanzetten
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Seriële poort waar de Kamstrup op zit (pas aan!)
SERIAL_PORT = '/dev/ttyUSB1'

def main():
    meter = kamstrup(SERIAL_PORT, ['temp1'])  # alleen parameter 0x56 uitlezen
    result = meter.run()

    if 'temp1' in result:
        print(f"Temperatuur 1 (0x56): {result['temp1']:.2f} °C")
    else:
        print("Kon parameter 0x56 (temp1) niet uitlezen.")

if __name__ == "__main__":
    main()

