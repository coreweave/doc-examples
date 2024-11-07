#!/usr/bin/python3

import subprocess 
import time
import struct


class SMBPBI:
    def __init__(self, timeout=5):
        self.delay = 0.05
        self.ipmi_timeout = timeout
        self.get_platform()
        if 'SYS-420GP-TNAR+' in self.platform:
            self.get_smbpbidata = self.get_smbpbidata_smc
            self.net = "0x06"
            self.cmd = "0x52"
            self.i2c = "0x05"
            self.i2c1 = "0x40"
            self.i2c2 = "0x41"
        elif 'SYS-821GE-TNHR' in self.platform:
            self.get_smbpbidata = self.get_smbpbidata_smc
            self.net = "0x06"
            self.cmd = "0x52"
            self.i2c = "0x05"
            self.i2c1 = "0x50"
            self.i2c2 = "0x51"
        else:
            raise "Unsupported platform"

    def get_platform(self):
        cmd = ['dmidecode','-s','system-product-name']
        self.platform = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=self.ipmi_timeout).decode('ASCII').strip()

    def get_system_serial(self):
        cmd = ['dmidecode','-s','system-serial-number']
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=self.ipmi_timeout).decode('ASCII').strip()

    def get_smbpbidata_smc(self, timeout=5):
        try:
            self.smbpbi_smc_disable_bmc_monitor()
            self.smbpbi_request_fencing()
            serial = self.smbpbi_request_baseboard_sn(self.i2c)
        except Exception as e:
            print(f'SMBPBI exception: {e}')
        finally:
            self.smbpbi_relinquish_fencing()
            self.smbpbi_smc_enable_bmc_monitor()
        return serial

    def smbpbi_run_commands(self, commands):
        result = []
        for command in commands:
            output = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, timeout=self.ipmi_timeout)
            result.append(output.stdout.strip())
            time.sleep(self.delay)
        return result

    def smbpbi_smc_disable_bmc_monitor(self):
        # disable bmc monitor and switch to GPU mux
        commands = ["ipmitool raw 0x30 0x70 0xdf 0x00",
                    "ipmitool raw {} {} {} 0x70 0x00 0x45".format(self.net, self.cmd, self.i2c),
                    "ipmitool raw {} {} {} 0xa8 0x00 0x41".format(self.net, self.cmd, self.i2c),
                    ]
        self.smbpbi_run_commands(commands)

    def smbpbi_smc_enable_bmc_monitor(self):
        commands = ["ipmitool raw 0x30 0x70 0xdf 0x01"]
        self.smbpbi_run_commands(commands)

    def smbpbi_smc_i2c1_mux(self):
        commands = ["ipmitool raw {} {} {} 0xa8 0x00 {}".format(self.net, self.cmd, self.i2c, self.i2c1)]
        self.smbpbi_run_commands(commands)

    def smbpbi_smc_i2c2_mux(self):
        commands = ["ipmitool raw {} {} {} 0xa8 0x00 {}".format(self.net, self.cmd, self.i2c, self.i2c2)]
        self.smbpbi_run_commands(commands)

    def smbpbi_request_fencing(self):
        commands = [
            "ipmitool raw {} {} {} 0xc0 0x0 0x5c 0x04 0xa3 0x01 0x00 0x80".format(self.net, self.cmd, self.i2c),
            "ipmitool raw {} {} {} 0xc0 0x0 0x5c 0x04 0xa3 0xFF 0x00 0x80".format(self.net, self.cmd, self.i2c),
        ]
        self.smbpbi_run_commands(commands)

    def smbpbi_relinquish_fencing(self):
        commands = [
            "ipmitool raw {} {} {} 0xc0 0x0 0x5c 0x04 0xa3 0x00 0x00 0x80".format(self.net, self.cmd, self.i2c),
            "ipmitool raw {} {} {} 0xc0 0x0 0x5c 0x04 0xa3 0xFF 0x00 0x80".format(self.net, self.cmd, self.i2c),
        ]
        self.smbpbi_run_commands(commands)

    def smbpbi_request_baseboard_sn(self, i2c):
        device = "0xC0" # FPGA
        opcode = "0x05" # Serials
        arg1 = "0xCC" # Baseboard serial
        serial = ""
        for arg2 in ["0x00", "0x01", "0x02", "0x03"]:
            commands = [
                "ipmitool raw {} {} {} {} 0x00 0x5c 0x04 {} {} {} 0x80".format(self.net, self.cmd, i2c, device, opcode, arg1, arg2),
                "ipmitool raw {} {} {} {} 0x05 0x5c".format(self.net, self.cmd, i2c, device),
                "ipmitool raw {} {} {} {} 0x05 0x5d".format(self.net, self.cmd, i2c, device)
            ]
            for command in commands:
                result = self.smbpbi_run_commands(commands)
            if result[1].split(' ')[4] != '1f':
                raise('SMBPBBI returned invalid data' + str(result))
            else:
                # add four bytes of serial number per arg to the output
                serial += bytearray.fromhex(result[2][3:]).decode()
        return serial


if __name__ == '__main__':
    handle = SMBPBI()
    system_serial = handle.get_system_serial()
    baseboard_serial = handle.get_smbpbidata_smc()
    print("System SN, Baseboard SN")
    print("%s, %s" % (system_serial, baseboard_serial))
