import trsfile
from trsfile.parametermap import TraceParameterMap
from trsfile.traceparameter import StringParameter
import numpy as np


def mean(X):
    return np.mean(X, axis=0)


def std_dev(X, _):
    return np.std(X, axis=0, ddof=len(X)-1)


def cov(X, X_bar, Y, Y_bar):
    return np.sum((X-X_bar)*(Y-Y_bar), axis=0)


def cor(a, b):
    return np.corrcoef(a, b, rowvar=False)[-1][:-1]


def get_positions(absolute=False, number=20, save=False):
    import os
    import ast
    files = []
    positions = []

    for file in os.listdir("correlation_test/res"):
        if file.endswith(".txt"):
            files.append(file)

    files.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))

    for file in files:
        with open("correlation_test/res/" + file, "r") as f:

            data = ast.literal_eval(f.read())
            absol = [abs(ele) for ele in data]

            if absolute:
                positions.append(sorted(range(len(absol)), key=lambda i: absol[i], reverse=False)[-number:])
            else:
                positions.append(sorted(range(len(data)), key=lambda i: data[i], reverse=True)[-number:])

    if save:
        with open("correlation_test/" + save + ".txt", "w") as f:
            for item in positions:
                f.write("%s\n" % item)
    return positions


zoomS=0
zoomE=9148
start = 0
number_of_traces = 100000
trace_file = "positions.trs"
mult = 0

for i in range(0, 256, 2):
    dataS = i
    dataN = i + 1
    data = np.zeros((dataN - dataS, number_of_traces), int)
    trace_array = np.zeros((number_of_traces, zoomE - zoomS), float)
    scale_X = None
    print("Processing multiplication ", mult+1, " of 128")
    with trsfile.open(trace_file, 'r') as traces:
        scale_X = traces.get_headers().get(trsfile.Header.SCALE_X)

        for i, trace in enumerate(traces[start:start + number_of_traces]):
            trace_array[i] = trace.samples[zoomS:zoomE]
            for j in range(dataS, dataN+1):  #+1 because range is exclusive

                coefficients_str = trace.parameters['COEFFICIENTS'].value.split()[:-28]                                         # remove last 28 coefficients - data is transfered in chunks of 30 coefficients
                coefficients_str = [coefficients_str[i] + coefficients_str[i+1] for i in range(0, len(coefficients_str), 2)]    # merge pairs of strings - 2 per coefficient
                coefficients = [int(x, 16) for x in coefficients_str]                                                           # convert to int
                data_index = min(j - dataS, len(data)-1)
                data[data_index][i] = coefficients[j]                                                                           # start from 0

    with trsfile.trs_open(
            trace_file[0:-4] + "_mult" + str(mult) + "_CORR.trs",                 # File name of the trace set
            'w',                             # Mode: r, w, x, a (default to x)
            # Zero or more options can be passed (supported options depend on the storage engine)
            engine = 'TrsEngine',            # Optional: how the trace set is stored (defaults to TrsEngine)
            headers = {                      # Optional: headers (see Header class)
                trsfile.Header.TRS_VERSION: 1,
                trsfile.Header.SCALE_X: scale_X,
                trsfile.Header.SCALE_Y: 1,
                trsfile.Header.DESCRIPTION: 'Correlation Traces',
            },
            padding_mode = trsfile.TracePadding.AUTO,# Optional: padding mode (defaults to TracePadding.AUTO)
            live_update = True               # Optional: updates the TRS file for live preview (small performance hit)
                                             #   0 (False): Disabled (default)
                                             #   1 (True) : TRS file updated after every trace
                                             #   N        : TRS file is updated after N traces
        ) as ctraces:

        for j in range(dataS,dataN):
            intermediate = np.array([data[j - dataS]]).transpose()  # index from 0
            correlation = cor(trace_array, intermediate)

            # Adding one Trace
            ctraces.append(
                trsfile.Trace(
                    trsfile.SampleCoding.FLOAT,
                    correlation,
                    TraceParameterMap({'COEFFICIENTS': StringParameter(str(j))})
                )
            )

    # save the correlation list into a file
    with open(trace_file[0:-4] + "_mult" + str(mult) + "_CORR.txt", "w") as f:
        f.write("[")
        for item in correlation:
            f.write("%s," % item)
        f.write("]")
    mult += 1