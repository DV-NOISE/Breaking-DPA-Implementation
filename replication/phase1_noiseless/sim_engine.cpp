#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <cmath>
#include <string>
#include <vector>
#include <unordered_map>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <chrono>
#include <algorithm>
#include <filesystem>

static constexpr int16_t Q = 3329;
static constexpr int16_t QINV = 3327;

static const int16_t ZETAS[64] = {
    2226, 430, 555, 843, 2078, 871, 1550, 105, 422, 587, 177, 3094, 3038, 2869, 1574, 1653,
    3083, 778, 1159, 3182, 2552, 1483, 2727, 1119, 1739, 644, 2457, 349, 418, 329, 3173, 3254,
    817, 1097, 603, 610, 1322, 2044, 1864, 384, 2114, 3193, 1218, 1994, 2455, 220, 2142, 1670,
    2144, 1799, 2051, 794, 1819, 2475, 2459, 478, 3221, 3021, 996, 991, 958, 1869, 1522, 1628
};

static inline int16_t B(int32_t x) {
    return static_cast<int16_t>(x);
}

static inline int16_t T(int32_t x) {
    return static_cast<int16_t>(x >> 16);
}

static inline int32_t smul(int16_t x, int16_t y) {
    return static_cast<int32_t>(x) * static_cast<int32_t>(y);
}

static inline unsigned hw32(int32_t x) {
    return static_cast<unsigned>(__builtin_popcount(static_cast<uint32_t>(x)));
}

// 5-state pack for q-template attack
static inline uint32_t pack5(unsigned h0, unsigned h1, unsigned h2, unsigned h3, unsigned h4) {
    return h0 | (h1 << 6) | (h2 << 12) | (h3 << 18) | (h4 << 24);
}

struct CollisionStats {
    double p_one = 0.0;
    double p_two = 0.0;
    double p_three = 0.0;
    double p_four = 0.0;
    double p_five = 0.0;
};

// Simulation of 5 intermediate states for odd coefficients (q-template)
// Evaluates over all a1 in [0, Q-1] for a fixed b1 and zeta
CollisionStats simulate_q_single_b(int16_t b1, int16_t zeta) {
    std::unordered_map<uint32_t, unsigned> counts;
    counts.reserve(Q * 2);

    constexpr int16_t a0 = 0;
    const int32_t poly1 = (static_cast<int32_t>(b1) << 16);

    for (int a = 0; a < Q; ++a) {
        const int16_t a1 = static_cast<int16_t>(a);
        const int32_t poly0 = (static_cast<int32_t>(a1) << 16) + a0;

        const unsigned h0 = hw32(poly0);
        int32_t tmp = smul(T(poly0), T(poly1));
        const unsigned h1 = hw32(tmp);

        int32_t tmp2 = smul(B(tmp), QINV);
        const unsigned h2 = hw32(tmp2);

        tmp2 = smul(Q, B(tmp2)) + tmp;
        const unsigned h3 = hw32(tmp2);

        tmp2 = smul(T(tmp2), zeta);
        const unsigned h4 = hw32(tmp2);

        ++counts[pack5(h0, h1, h2, h3, h4)];
    }

    uint64_t c1 = 0, c2 = 0, c3 = 0, c4 = 0, c5 = 0;
    for (const auto &kv : counts) {
        const unsigned m = kv.second;
        if (m == 1) c1 += 1;
        else if (m == 2) c2 += 2;
        else if (m == 3) c3 += 3;
        else if (m == 4) c4 += 4;
        else if (m == 5) c5 += 5;
    }

    CollisionStats res;
    res.p_one = static_cast<double>(c1) / Q;
    res.p_two = static_cast<double>(c2) / Q;
    res.p_three = static_cast<double>(c3) / Q;
    res.p_four = static_cast<double>(c4) / Q;
    res.p_five = static_cast<double>(c5) / Q;
    return res;
}

// Average q-template collision statistics over b1 in [0, Q-1]
CollisionStats simulate_q_average(int16_t zeta) {
    long double s1 = 0, s2 = 0, s3 = 0, s4 = 0, s5 = 0;
    for (int b = 0; b < Q; ++b) {
        CollisionStats s = simulate_q_single_b(static_cast<int16_t>(b), zeta);
        s1 += s.p_one;
        s2 += s.p_two;
        s3 += s.p_three;
        s4 += s.p_four;
        s5 += s.p_five;
    }
    CollisionStats avg;
    avg.p_one = static_cast<double>(s1 / Q);
    avg.p_two = static_cast<double>(s2 / Q);
    avg.p_three = static_cast<double>(s3 / Q);
    avg.p_four = static_cast<double>(s4 / Q);
    avg.p_five = static_cast<double>(s5 / Q);
    return avg;
}

// 13-state simulation for q^2-templates with given b0, b1, zeta
// upto_instr in [0..12]
std::unordered_map<int, int> simulate_q2_histogram(int upto_instr, int16_t b0, int16_t b1, int16_t zeta, bool use_poly0_hw = false) {
    std::unordered_map<std::string, int> counts;
    counts.reserve(Q * Q / 2);

    int HWS[13];
    const int32_t poly1 = (static_cast<int32_t>(b1) << 16) | (static_cast<uint16_t>(b0));

    for (int a0_i = 0; a0_i < Q; ++a0_i) {
        const int16_t a0 = static_cast<int16_t>(a0_i);
        for (int a1_i = 0; a1_i < Q; ++a1_i) {
            const int16_t a1 = static_cast<int16_t>(a1_i);

            // CHANGELOG (2026-09-12): Corrected poly0 packing from (a1<<16)|a0 to (a0<<16)|a1
            // Discovered during pre-supervisor internal audit. Matches authors' q-squared-attack-sim.cpp (line 54)
            // and resolves the lower Figure 5 collision probability discrepancy (0.999346 -> 0.997523).
            const int32_t poly0 = (static_cast<int32_t>(a0) << 16) | (static_cast<uint16_t>(a1));
            
            // In q-squared-attack-sim.cpp (line 55), HWS[0] = WEIGHT(a0) yields Figure 5 lower table (0.997523).
            // In q^2-data-instr1.csv, HWS[0] = hw32(poly0) records full 32-bit register leakage (23 bins).
            if (use_poly0_hw) {
                HWS[0] = hw32(poly0);
            } else {
                HWS[0] = hw32(static_cast<uint16_t>(a0));
            }

            // Line 8: smultt tmp, poly0, poly1 (a1 * b1)
            int32_t tmp = smul(T(poly0), T(poly1));
            HWS[1] = hw32(tmp);

            // Line 9: montgomery (i) smulbt tmp2, tmp, qinv
            int32_t tmp2 = smul(B(tmp), QINV);
            HWS[2] = hw32(tmp2);

            // Line 9: montgomery (ii) smlabb tmp2, q, tmp2, tmp
            tmp2 = smul(Q, B(tmp2)) + tmp;
            HWS[3] = hw32(tmp2);

            // Line 10: smultb tmp2, tmp2, zeta
            tmp2 = smul(T(tmp2), zeta);
            HWS[4] = hw32(tmp2);

            // Line 11: smlabb tmp2, poly0, poly1, tmp2 (a0*b0 + tmp2)
            tmp2 = tmp2 + smul(B(poly0), B(poly1));
            HWS[5] = hw32(tmp2);

            // Line 12: montgomery (i) smulbt tmp, tmp2, qinv
            tmp = smul(B(tmp2), QINV);
            HWS[6] = hw32(tmp);

            // Line 12: montgomery (ii) smlabb tmp, q, tmp, tmp2
            tmp = smul(Q, B(tmp)) + tmp2;
            HWS[7] = hw32(tmp);

            // Line 14: smuadx tmp2, poly0, poly1 (a1*b0 + a0*b1)
            tmp2 = smul(T(poly0), B(poly1)) + smul(B(poly0), T(poly1));
            HWS[8] = hw32(tmp2);

            // Line 15: montgomery (i) smulbt tmp3, tmp2, qinv
            int32_t tmp3 = smul(B(tmp2), QINV);
            HWS[9] = hw32(tmp3);

            // Line 15: montgomery (ii) smlabb tmp3, q, tmp3, tmp2
            tmp3 = smul(Q, B(tmp3)) + tmp2;
            HWS[10] = hw32(tmp3);

            // pkhTB tmp, tmp3, tmp
            int32_t mytmp = (tmp3 >> 16);
            tmp = (mytmp << 16) | (static_cast<uint16_t>(B(tmp)));
            HWS[11] = hw32(tmp);

            // store tmp3
            HWS[12] = hw32(tmp3);

            std::string key = "";
            for (int k = 0; k <= upto_instr; ++k) {
                key.push_back(static_cast<char>('A' + HWS[k]));
            }
            ++counts[key];
        }
    }

    std::unordered_map<int, int> hist;
    for (const auto &kv : counts) {
        ++hist[kv.second];
    }
    return hist;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        std::cout << "Usage: sim_engine <command> [args]\n";
        std::cout << "Commands:\n";
        std::cout << "  q_single <zeta>              : Compute Figure 5 row for given zeta\n";
        std::cout << "  q_all <output_dir>           : Generate all 128 zeta .dat files for compute_expectation.py\n";
        std::cout << "  q2_single <zeta>             : Compute q^2 Figure 5 row for given zeta\n";
        std::cout << "  q2_instr <upto_instr> <csv>  : Run q^2 simulation up to instruction [0..12] and write CSV\n";
        return 1;
    }

    std::string cmd = argv[1];

    if (cmd == "q_single") {
        int16_t zeta = (argc >= 3) ? static_cast<int16_t>(std::atoi(argv[2])) : 2226;
        auto start = std::chrono::high_resolution_clock::now();
        CollisionStats s = simulate_q_average(zeta);
        auto end = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = end - start;

        std::cout << std::fixed << std::setprecision(6);
        std::cout << "zeta: " << zeta << "\n";
        std::cout << "1-way: " << s.p_one << "\n";
        std::cout << "2-way: " << s.p_two << "\n";
        std::cout << "3-way: " << s.p_three << "\n";
        std::cout << "4-way: " << s.p_four << "\n";
        std::cout << "5-way: " << s.p_five << "\n";
        std::cout << "Elapsed: " << elapsed.count() << "s\n";
    }
    else if (cmd == "q_all") {
        std::string out_dir = (argc >= 3) ? argv[2] : "zetas";
        std::filesystem::create_directories(out_dir);
        std::cout << "Generating 128 zeta .dat files in directory: " << out_dir << "\n";
        auto start = std::chrono::high_resolution_clock::now();

        std::ofstream res_file("q_simulation_results_generated.txt");

        std::vector<CollisionStats> all_stats(128);
        for (int i = 0; i < 64; ++i) {
            int16_t z_pos = ZETAS[i];
            int16_t z_neg = -ZETAS[i];

            CollisionStats s_pos = simulate_q_average(z_pos);
            CollisionStats s_neg = simulate_q_average(z_neg);

            all_stats[i] = s_pos;
            all_stats[i + 64] = s_neg;

            // Format for compute_expectation.py:
            // "1:0.8696,2:0.1080,3:0.0177,4:0.0012,5:0.0000\n"
            char fname_pos[256], fname_neg[256];
            std::snprintf(fname_pos, sizeof(fname_pos), "%s/zeta-%d-%d.dat", out_dir.c_str(), i, z_pos);
            std::snprintf(fname_neg, sizeof(fname_neg), "%s/zeta-%d-%d.dat", out_dir.c_str(), i, z_neg);

            std::ofstream f_pos(fname_pos);
            f_pos << std::fixed << std::setprecision(10);
            f_pos << "1:" << s_pos.p_one << ",2:" << s_pos.p_two << ",3:" << s_pos.p_three
                  << ",4:" << s_pos.p_four << ",5:" << s_pos.p_five << "\n";
            f_pos.close();

            std::ofstream f_neg(fname_neg);
            f_neg << std::fixed << std::setprecision(10);
            f_neg << "1:" << s_neg.p_one << ",2:" << s_neg.p_two << ",3:" << s_neg.p_three
                  << ",4:" << s_neg.p_four << ",5:" << s_neg.p_five << "\n";
            f_neg.close();

            std::cout << "Root " << std::setw(2) << i << ": zeta=" << std::setw(5) << z_pos 
                      << " -> 1-way: " << std::setprecision(4) << s_pos.p_one
                      << " | -zeta=" << std::setw(6) << z_neg << " -> 1-way: " << s_neg.p_one << "\n";
        }

        auto end = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = end - start;
        std::cout << "All 128 zetas generated in " << elapsed.count() << "s\n";
    }
    else if (cmd == "q2_single") {
        int16_t zeta = (argc >= 3) ? static_cast<int16_t>(std::atoi(argv[2])) : 2226;
        int16_t b0 = 2682, b1 = 2345;
        auto start = std::chrono::high_resolution_clock::now();
        auto hist = simulate_q2_histogram(12, b0, b1, zeta);
        auto end = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = end - start;

        const double total = static_cast<double>(Q) * Q;
        double p1 = (hist.count(1) ? hist[1] : 0) / total;
        double p2 = (hist.count(2) ? hist[2] * 2 : 0) / total;
        double p3 = (hist.count(3) ? hist[3] * 3 : 0) / total;

        std::cout << std::fixed << std::setprecision(8);
        std::cout << "q^2 for zeta=" << zeta << " (b0=" << b0 << ", b1=" << b1 << "):\n";
        std::cout << "1-way: " << p1 << "\n";
        std::cout << "2-way: " << p2 << "\n";
        std::cout << "3-way: " << p3 << "\n";
        std::cout << "Elapsed: " << elapsed.count() << "s\n";
    }
    else if (cmd == "q2_instr") {
        int upto_instr = (argc >= 3) ? std::atoi(argv[2]) : 0;
        std::string csv_file = (argc >= 4) ? argv[3] : "q2_out.csv";
        int16_t b0 = 2682, b1 = 2345, zeta = 2226;

        std::cout << "Running q^2 simulation up to instruction " << upto_instr << "...\n";
        auto start = std::chrono::high_resolution_clock::now();
        auto hist = simulate_q2_histogram(upto_instr, b0, b1, zeta, true);
        auto end = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = end - start;

        std::ofstream f(csv_file);
        // Write in author format: multiplicity, count (sorted by multiplicity)
        std::vector<std::pair<int, int>> sorted_hist(hist.begin(), hist.end());
        std::sort(sorted_hist.begin(), sorted_hist.end());

        for (const auto &p : sorted_hist) {
            f << p.first << ", " << p.second << "\n";
        }
        f.close();

        std::cout << "Wrote " << sorted_hist.size() << " collision bins to " << csv_file 
                  << " in " << elapsed.count() << "s\n";
    }
    else {
        std::cerr << "Unknown command: " << cmd << "\n";
        return 1;
    }

    return 0;
}
