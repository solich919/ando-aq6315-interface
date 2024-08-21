# Jakub Solich
# this module functions as a wrapper for AQ6315A/B spectrum analyzer
# the goal is to create roubust and simple interface thorugh class methods
# the final form is to create 'virtual clone' of the machine, by keeping 
# the state of all params and being able to save the state of a machine

# Most wrapper functions should return talker data if no argument given

import pyvisa
import time
import logging

logging.basicConfig(level=logging.INFO)

class AQ6315:
    """Definicja klasy modułu"""
    def __init__(self, instrument_res_name=None, debug=False):
        """Definicja konstruktora. Przyjmuje dwa opcjnalne argumenty.
        Jeśli nie podano nazwy zasobu, konstruktor wywołuje discover_device()
        """
        # Turn on debug if true
        if debug is True:
            pyvisa.log_to_screen()
            logging.basicConfig(level=logging.DEBUG)
        # Create ResourceManager for pyVISA
        self.resourceman = pyvisa.ResourceManager()
        # if none resource name given, discover device
        if instrument_res_name is None:
            try:
                self.discover_device()
            except Exception:
                # if none found, raise and exception and exit
                print("No Ando AQ6315 found.")
                exit(1)
        else:
            self.resource_name = instrument_res_name
        self.connect()
        
    def get_trace(self):
        """Set delimiter format and ask for trace data. Write to trace and return trace"""
        self.instrument.write('SD0,LDATA')
        self.trace = self.instrument.read_ascii_values()
        return self.trace
        
    def connect(self): #'GPIB0::1::INSTR'
        # Connect
        self.instrument = self.resourceman.open_resource(self.resource_name)
        # set termination
        self.instrument.write_termination = '\r\n'
        self.instrument.read_termination = '\r\n'
        self.instrument.query_delay = 0.1
        
    def close_conn(self):
        self.resourceman.close()
        
    def discover_device(self):
        # list resources to array
        found_resources = self.resourceman.list_resources()
        # look for AQ6315
        for resource in found_resources:
            # temporarily open resource
            temp_res = self.resourceman.open_resource(resource)
            # specify delimiter format for Ando and ask for IDN
            temp_res.write('SD0,*IDN?')
            # Ando spits random bytes at the end of the idn string, this should work
            idn = temp_res.read_raw()
            # check if IDN return contains AQ6315 and return, othewise look next res
            if b'AQ6315' in idn:
                logging.info(f"Found {idn}")
                temp_res.close()
                self.resource_name = resource
                return resource
            else:
                temp_res.close()
        # in case none found
        raise Exception("No Ando AQ6315 found.")
        
        
    def sweep_start_auto(self):
        self.instrument.write('AUTO')
        
    def sweep_start_repeat(self):
        self.instrument.write('RPT')
        
    def sweep_start_single(self):
        self.instrument.write('SGL')
        
    def sweep_stop(self):
        self.instrument.write('STP')
        
    def sweep_await_finish(self, max_timeout=25000):
        # the more elegant way would be to use SRQ, however implementation
        # needed for it's function are not always present. For now, we will
        # just ask repeatedly in what state sweep is. works so far
        t0 = time.time()
        while(self.sweep_check() != "STOP"):
            if time.time()-t0 >= max_timeout:
                return
            time.sleep(0.5)
        
    def sweep_check(self)->str:
        ret = self.instrument.query('SWEEP?')
        return ["STOP", "SINGLE", "REPEAT", "AUTO", "SEGMENT MEASURE"][int(ret)]
    
    def center_wavelenght(self, center_wl=None):
        if center_wl is None:
            return float(self.instrument.query('CTRWL?'))
        elif center_wl >= 350.0 and center_wl <= 1750.00:
            self.instrument.write(f'CTRWL{center_wl}')
            return center_wl
        else:
            raise ValueError(f"Invalid value {center_wl}")
    
    def start_wavelenght(self, start_wl=None):
        if start_wl is None:
            return float(self.instrument.query('STAWL?'))
        elif start_wl >= -400.0 and start_wl <= 1750.00:
            self.instrument.write(f'STAWL{start_wl}')
            return start_wl
        else:
            raise ValueError(f"Invalid value {start_wl}")
        
    def stop_wavelenght(self, stop_wl=None):
        if stop_wl is None:
            return float(self.instrument.query('STPWL?'))
        elif stop_wl >= 350.0 and stop_wl <= 2500.00:
            self.instrument.write(f'STPWL{stop_wl}')
            return stop_wl
        else:
            raise ValueError(f"Invalid value {stop_wl}")
        
    def span(self, span_wl=None):
        if span_wl is None:
            return float(self.instrument.query('SPAN?'))
        elif 1.0 <= span_wl <= 1500.0 or span_wl == 0:
            self.instrument.write(f'SPAN{span_wl}')
            return span_wl
        else:
            raise ValueError(f"Invalid value {span_wl}")
        
    def span_set_by_width(self):
        self.instrument.write('SPN=W')
        
    def reference_level(self, level=None, unit="dBm"):
        if level is None:
            return self.instrument.query('REFL?')
        
        match unit:
            case "dBm":
                if -90.0 <= level <= 20.0:
                    self.instrument.write(f'REFL{level}')
            case "pW":
                if 1.0 <= level <= 999:
                    self.instrument.write(f'REFLP{level}')
            case "nW":
                if 1.0 <= level <= 999:
                    self.instrument.write(f'REFLN{level}')
            case "uW":
                if 1.0 <= level <= 999:
                    self.instrument.write(f'REFLU{level}')
            case "Mw":
                if 1.0 <= level <= 100:
                    self.instrument.write(f'REFLM{level}')
            case _:
                raise ValueError(f"Invalid value {unit} or {level}")
        
    def center_peak(self):
        self.instrument.write('CTR=P')
        
    def setup_resolution(self, res=None):
        if res is None:
            return float(self.instrument.query('RESLN?'))
        ## TODO better check for stepping 1-2-5
        elif 0.05 <= res <= 10.0 and res%0.05 == 0:
            self.instrument.write(f'RSLN{res}')
        else:
            raise ValueError(f"Invalid value {res}")
        
    def setup_sensitivity(self, sens=None):
        if sens is None:
            ret = self.instrument.query('SENS?')
            return ["SENS HIGH1", "SENS HIGH2", "SENS HIGH3", "SENS NORM HOLD", "SENS NORM AUTO"][int(ret)-1]

        match sens:
            case "HIGH1":
                self.instrument.write("SHI1")
            case "HIGH2":
                self.instrument.write('SHI2')
            case "HIGH3":
                self.instrument.write('SHI3')
            case "NORM_HOLD":
                self.instrument.write('SNHD')
            case "NORM_AUTO":
                self.instrument.write('SNAT')
            case _:
                raise ValueError(f"Invalid value {sens}")

    def average_samples(self, avg=None):
        if avg is None:
            return int(self.instrument.query('AVG?'))
        elif 1 <= avg <= 1000:
            self.instrument.write(f'AVG{avg}')
        else:
            raise ValueError(f"Invalid value {avg}")
    
    def sampling_size(self, samples=None):
        if samples is None:
            return int(self.instrument.query('SMPL?'))
        elif 11 <= samples <= 1001:
            self.instrument.write(f'SMPL{samples}')
        else:
            raise ValueError(f"Invalid value {samples}")
                
    def peak_search(self):
        self.instrument.write('PKSR')
        
    def bottom_search(self):
        self.instrument.write('BTSR')
        
    def next_search(self):
        self.instrument.write('NSR')
        
    def next_search_right(self):
        self.instrument.write('NSRR')
        
    def next_search_left(self):
        self.instrument.write('MSRL')

    def marker_clear(self):
        self.instrument.write('LMKCL')
        
    def get_marker(self):
        return float(self.instrument.query('MKR?'))
        
    def set_output_data_delimiter(self, delimiter=None):
        # SD0 for ',' ; SD1 for 'CRLF'
        if delimiter is None:
            return [',', 'CRLF'][int(self.instrument.query('SD?'))]
        match(delimiter):
            case ',':
                self.instrument.write('SD0')
            case 'CRLF':
                self.instrument.write('SD1')
            case _:
                raise ValueError(f"Invalid value {delimiter}")
            
    def save_trace_to_file(self, filename):
        # TODO add check if file exists
        with open(f'{filename}', 'w') as f:
            for point in self.trace[1:]:
                f.write(f"{point}\n")
        logging.info(f"Saved trace to file {filename}")
        
    def setup_monochromator_mode(self, mode=None):
        if mode is None:
            return ['SINGLE', 'DOUBLE'][int(self.instrument.query('MONO?'))]
        match(mode):
            case "SINGLE":
                self.instrument.write('MONO1')
            case "DOUBLE":
                self.instrument.write('MONO2')
            case _:
                raise ValueError(f"Invalid value {mode}")
            
    def setup_light_measure_mode(self, mode=None):
        if mode is None:
            return ['PULSE', 'CW'][int(self.instrument.query('CWPLS?'))]
        match(mode):
            case "PULSE":
                self.instrument.write('PLMES')
            case "CW":
                self.instrument.write('CLMES')
            case _:
                raise ValueError(f"Invalid value {mode}")
       