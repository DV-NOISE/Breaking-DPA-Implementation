from joblib import Parallel, delayed
import trsfile
import numpy as np
import os
from numba import jit
import ast


def get_tested_trace(trs_name, i):
    # return the trace with index i from the trs file
    with trsfile.open(trs_name, 'r') as traces:
        return traces[i].samples


def euclidean_distance(a, b):
    return np.linalg.norm(a - b)


@jit(nopython=True)
def pearson_correlation(a, b):
    return np.corrcoef(a, b)[1, 0]


@jit(nopython=True, parallel=True)
def compare_pearson_RAM(tested_trace, traces):
    i = 0
    res = []
    for trace in traces:
        if i % 100000 == 0:
            print("Comparing trace: " + str(i))
        i += 1
        res.append(pearson_correlation(tested_trace, trace))
    return res


def compare_euclidean_RAM(tested_trace, traces, chunk=slice(None)):
    i = 0
    res = []
    for trace in traces:
        if i % 100000 == 0:
            print("Comparing trace: " + str(i))
        i += 1
        res.append(euclidean_distance(tested_trace[chunk], trace[chunk]))
    return res


def get_target_trace_number_from_coeffs(a, b):
    # return expected trace number corresponding to the coefficients
    return a * 3329 + b


def get_coeff_values_from_trace_number(trace_number):
    # return coefficients corresponding to the trace number
    b = trace_number % 3329
    a = (trace_number - b) // 3329
    return a, b


def get_multiplication_coeffs_for_trace(n):
    # return coefficients for the n-th trace
    i = 0
    coeffs = []
    for line in open("params.txt", "r"):
        if line.strip().endswith(",") or line.strip().endswith("}"):
            if i == n:
                line_coeffs = line.split("{")[1].split("}")[0].split(",")
                for j in range(0, len(line_coeffs), 2):
                    coeffs.append((line_coeffs[j], line_coeffs[j + 1]))
                return coeffs
            i += 1
    return


def find_chunk(tested_trace, tested_trace_num, data_traces, multiplication, size_start=40, size_end=100, offset=100,
               move_by=70):
    results = []
    for size in range(size_start, size_end + 1):
        for slide in range(offset + multiplication * move_by, offset + multiplication * move_by + size):

            if slide + size > len(tested_trace):
                break

            print("Testing slide: " + str(slide))
            a, b = get_multiplication_coeffs_for_trace(tested_trace_num)[multiplication]
            target = get_target_trace_number_from_coeffs(int(a), int(b))

            i = 0
            best_correlation = -1
            best_trace = None
            found_target = False

            for trace in data_traces:
                if i % 100000 == 0:
                    print(i)

                correlation = pearson_correlation(tested_trace[slice(slide, slide + size)],
                                                  trace[slice(slide, slide + size)])
                if correlation > best_correlation:
                    if found_target:  # target needs to be highest
                        break
                    else:
                        best_correlation = correlation
                        best_trace = i
                        if best_trace == target:
                            found_target = True
                i += 1

            if found_target:
                results.append(slice(slide, slide + size))
    return results


def get_multiplication_coeffs_for_all_traces(n):
    coeffs = []
    for line in open("params.txt", "r"):
        if line.strip().endswith(",") or line.strip().endswith("}"):
            line_coeffs = line.split("{")[1].split("}")[0].split(",")
            coeffs.append((line_coeffs[n * 2], line_coeffs[n * 2 + 1]))
    return coeffs


def generate_report_pearson(filename="report.txt", targets=0, lines=50, set_a=None, set_b=None, target_num=None,
                            multiple_targets=False):
    files = os.listdir(r"res")
    files.remove("backup")
    files.sort(key=lambda x: int(x.split("_")[1]))
    score = 0

    with open(filename, "w") as f:

        for file in files:
            pearson = []
            print("Processing " + file)
            for line in open(r"res/" + file, "r"):
                pearson.append(float(line))

            if pearson == []:
                continue

            pearson = list(enumerate(pearson))
            pearson.sort(key=lambda x: x[1], reverse=True)
            print("sorting done")

            trace_number = int(file.split("_")[1])

            print("trace number: " + str(trace_number))
            if set_a is not None:
                a, b = get_multiplication_coeffs_for_all_traces(targets)[trace_number]
                a = set_a
            elif set_b is not None:
                a, b = get_multiplication_coeffs_for_all_traces(targets)[trace_number]
                b = set_b
            else:
                a, b = get_multiplication_coeffs_for_all_traces(targets)[trace_number]
            if target_num is not None:
                target = target_num
            else:
                target = get_target_trace_number_from_coeffs(int(a), int(b))
            print("target: " + str(target))

            if not multiple_targets:
                pearson_place = ([i for i, v in enumerate(pearson) if v[0] == target])[0] + 1
            else:
                target = []
                for a in range(3328):
                    target.append(get_target_trace_number_from_coeffs(a, int(b)))
                pearson_place = ([i for i, v in enumerate(pearson) if v[0] in target])[0] + 1

            score += pearson_place - 1
            print(a, b, target, pearson_place)

            f.write(f"Trace {trace_number}:\n")
            f.write("Pearson Correlation\n")
            f.write(f"{a: >8}\t\t{b: >8}\t\t{target: >8}\t\t{pearson_place}\n")

            for l in range(lines):
                if pearson[l][0] == target:
                    f.write(f"{l + 1}\t\t{pearson[l][0]: >8}\t\t{pearson[l][1]: >8} * \n")
                else:
                    f.write(f"{l + 1}\t\t{pearson[l][0]: >8}\t\t{pearson[l][1]: >8}\n")
            f.write("\n")
            f.write("score: " + str(score) + "\n")
    print("Score: " + str(score))

    for file in os.listdir("res"):
        if file.endswith(".txt"):
            os.rename("res/" + file, "res/backup/" + file)

    return score


def test_slice(data_traces, chunk, indices=None, trace_range=15):
    print("Testing slice: " + str(chunk))

    if indices is not None:
        data_t = [np.array([trace[i] for i in indices]) for trace in data_traces]
        chunk = None

    for trace_number in range(0, trace_range):
        print("Testing trace: ", trace_number)
        tested_trace = get_tested_trace(trs_tested, trace_number)  # CHOOSE TRACE

        if indices is not None:
            tested_trace = [tested_trace[i] for i in indices]
            chunk = None

        if chunk is not None:
            start = chunk.start
            stop = chunk.stop
            data_t = [trace[chunk] for trace in data_traces]
            tested_trace = tested_trace[chunk]
        else:
            start = indices[0]
            stop = indices[-1]

        res = compare_pearson_RAM(tested_trace, data_t)
        f = open("res/trace_" + str(trace_number) + "_pearson_" + str(start) + "-" + str(stop) + ".txt",
                 "w")

        # write results to file
        for i in range(len(res)):
            f.write(str(res[i]) + "\n")
        f.close()


def shift(data_traces, chunk_start, chunk_end, name, direction="left", targets=1, set_a=None, set_b=None):
    best_score = 999999999
    while True:
        for file in os.listdir("res"):
            if file.endswith(".txt"):
                os.rename("res/" + file, "res/backup/" + file)
        test_slice(data_traces, slice(chunk_start, chunk_end))
        score = generate_report_pearson(name + "_pearson_" + str(chunk_start) + "-" + str(chunk_end) + ".txt",
                                        targets=targets, set_a=set_a, set_b=set_b)
        if score < best_score:
            best_score = score
            if direction == "left":
                chunk_start -= 1
                chunk_end -= 1
            elif direction == "right":
                chunk_start += 1
                chunk_end += 1
            elif direction == "grow":
                chunk_end += 1
            elif direction == "shrink":
                chunk_end -= 1
            print("Best score: ", best_score, "continue...")
        else:
            break


def test_positions_file(file_name):
    positions = []
    with open(file_name, "r") as f:
        for line in f:
            if line.startswith("["):
                positions.append(ast.literal_eval(line))

    mult = 0
    for pos in positions:
        print("Testing values: ", mult, pos)
        chunk = None
        test_slice(data_traces, None, indices=pos, trace_range=15)
        generate_report_pearson("pearson_mult" + str(mult) + ".txt", targets=mult, lines=20000, target_num=None)
        mult += 1


def attack(positions_file="positions_0_33_best.txt"):
    trs_tested = r"fixedTraces-2023-06-14-01-53-01_cut_0-15.trs"
    trs_local = r"fixedTraces-2023-06-14-01-53-01_cut_665830-end.trs"
    data_traces = []

    print("Loading traces...")
    i = 0
    with trsfile.open(trs_local, 'r') as traces:
        for t in traces:
            data_traces.append(np.array(t.samples[:9090]))
            i += 10
            if i % 100000 == 0:
                print(i)
    print("Loaded!")

    test_positions_file(positions_file)