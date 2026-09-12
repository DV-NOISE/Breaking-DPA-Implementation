import chipwhisperer as cw
import subprocess
from tqdm import tqdm
import numpy as np
import os
import datetime
from math import ceil
from trsfile import trs_open, Trace, SampleCoding, TracePadding, Header
from trsfile.parametermap import TraceParameterMap
from trsfile.traceparameter import ByteArrayParameter, StringParameter

PLATFORM = 'CWLITEARM'


# convert an integer to a hex string for communication
def hex_str(num):
    return " ".join(["%02x" % ((num >> (8 * i)) & 0xff) for i in range(63, -1, -1)])


# run bash command and return output
def run_cmd(cmd):
    return subprocess.check_output(cmd, shell=True).decode('utf-8')


def chunk_data(data):
    chunked_data = []
    current_part = 0
    total_parts = ceil(len(data) / 30) - 1  # -1 because indexed from 0

    while current_part <= total_parts:
        if len(data) < 30:  # pad the rest with zeros
            data += [0] * (32 - len(data))

        chunked_data.append([current_part, total_parts] + data[:30])
        data = data[30:]
        current_part += 1

    return chunked_data



def capture_trace(data):
    chunks = chunk_data(data)
    coefs_str = ""
    for chunk in chunks:
        coefs_int = 0
        tmp = chunk[::-1]  # reverse random_coefs

        for i in range(0, len(chunk)):
            coefs_int += tmp[i] * hex_10000 ** i

        coefs_str += hex_str(coefs_int)[11:]
        ktp.setInitialText(hex_str(coefs_int))
        key, text = ktp.next()  # manual creation of a key, text pair can be substituted here

        print("TEXT IN:  ", hex_str(coefs_int))
        ret = cw.capture_trace(scope, target, text, key)
    return ret, coefs_str


cmd_make1 = "make clean PLATFORM={}".format(PLATFORM)
cmd_make2 = "make PLATFORM='CW308_STM32F4' CRYPTO_TARGET=NONE"  # SS_VER='SS_VER_2_0'
cmd_make3 = "mkdir objdir; cd objdir; mkdir crypto_kem; cd crypto_kem; mkdir kyber768; cd kyber768; mkdir m4; cd ../..; mkdir common; cd ..; make PLATFORM={}".format(
    PLATFORM)

# compile the firmware
print(run_cmd(cmd_make1))
print(run_cmd(cmd_make2))
print(run_cmd(cmd_make3))

# CONNECT THE DEVICE AND FIND NUMSAMPLES AND DOWNSAMPLING RATE:
scope = cw.scope()
scope.default_setup()
number_of_points = 9148
scope.adc.samples = number_of_points
target = cw.target(scope, cw.targets.SimpleSerial, flush_on_err=False)
target.output_len = 64
hex_10000 = 0x10000
# set the amount of communicated data like this => target.output_len = 4

prog = cw.programmers.STM32FProgrammer
fw_path = './simpleserial-masked-kyber-{}.hex'.format(PLATFORM)
cw.program_target(scope, prog, fw_path)
ktp = cw.ktp.Basic()  # object to generate fixed/random key and text (default fixed key, random text)
ktp.fixed_text = True
ktp.fixed_key = True
time_to_save = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

# make a new directory for the created files
prep = "./"  # "/media/sf_test/"
os.mkdir(prep + "Traces/%s" % time_to_save)

path_fixed = prep + "Traces/%s/fixedTraces-%s.trs" % (time_to_save, time_to_save)

with trs_open(
        path_fixed,  # File name of the trace set
        'w',  # Mode: r, w, x, a (default to x)
        # Zero or more options can be passed (supported options depend on the storage engine)
        engine='TrsEngine',  # Optional: how the trace set is stored (defaults to TrsEngine)
        headers={  # Optional: headers (see Header class)
            Header.TRS_VERSION: 2,
            Header.SCALE_X: 1e-6,
            Header.SCALE_Y: 0.1,
            Header.DESCRIPTION: 'Testing trace creation',
            # Header.TRACE_PARAMETER_DEFINITIONS: TraceParameterDefinitionMap(
            #    {'LEGACY_DATA': TraceParameterDefinition(ParameterType.BYTE, 4, 0),
            #     'COEFFICIENTS': TraceParameterDefinition(ParameterType.STRING, 11, 4)}),

        },
        padding_mode=TracePadding.AUTO,  # Optional: padding mode (defaults to TracePadding.AUTO)
        live_update=False  # Optional: updates the TRS file for live preview (small performance hit)
        #   0 (False): Disabled (default)
        #   1 (True) : TRS file updated after every trace
        #   N        : TRS file is updated after N traces
) as traces:
    N = 1
    known_coeffs = []                       # list of known coefficients
    res_len = 128 - len(known_coeffs) // 2
    for x in range(0, 3329):
        for y in range(0, 3329):
            random_coefs = known_coeffs + [x, y] * res_len     # 128 is the number of coefficients

            for i in tqdm(range(N), desc='Capturing traces, iteration = ' + str(
                    x)):
                successful = False

                while not successful:

                    ret = None

                    while (not ret):
                        ret, coefs_str = capture_trace(random_coefs)
                        text_out = ret.textout.hex()
                        print("TEXT OUT: ", ' '.join(text_out[i:i + 2] for i in range(0, len(text_out), 2)))

                    if (scope.adc.trig_count < 5000000):
                        successful = True

                    if successful:
                        samples = np.array(ret.wave[:])
                        data = ret.textout
                        t = Trace(
                            SampleCoding.FLOAT,
                            samples,
                            TraceParameterMap({'LEGACY_DATA': ByteArrayParameter(data),
                                               'COEFFICIENTS': StringParameter(coefs_str)}),
                            title='Kyber'
                        )
                        traces.append(
                            t
                        )
with open(prep + "Traces/%s/params.txt" % time_to_save, "w") as f:
    f.write("N = %d\nnumPoints = %d" % (N, number_of_points))
