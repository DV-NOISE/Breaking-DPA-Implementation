#include <cstdint>
#include <cstdlib>
#include <cmath>
#include <vector>
#include <random>
#include <algorithm>
#include <iostream>
#include <iomanip>
#include <fstream>
#include <chrono>
#include <omp.h>

static constexpr int16_t Q = 3329;
static constexpr int16_t QINV = 3327;
static constexpr int32_t NUM_CANDIDATES = static_cast<int32_t>(Q) * Q; // 11,082,241

static inline int16_t B(int32_t x) { return static_cast<int16_t>(x); }
static inline int16_t T(int32_t x) { return static_cast<int16_t>(x >> 16); }
static inline int32_t smul(int16_t x, int16_t y) { return static_cast<int32_t>(x) * static_cast<int32_t>(y); }
static inline uint8_t hw32(int32_t x) { return static_cast<uint8_t>(__builtin_popcount(static_cast<uint32_t>(x))); }

// Compact 13-byte template structure for minimal cache footprint (11M * 13 = ~144 MB)
struct alignas(16) TemplateQ2Compact {
    uint8_t h[13];
    uint8_t pad[3]; // Align to 16 bytes for SIMD efficiency
};

// Compute 13 intermediate Hamming weight states for pair (a0, a1)
inline void compute_template_q2_compact(int16_t a0, int16_t a1, int16_t b0, int16_t b1, int16_t zeta, TemplateQ2Compact &out) {
    const int32_t poly1 = (static_cast<int32_t>(b1) << 16) | (static_cast<uint16_t>(b0));
    // Verified poly0 packing: (a0 << 16) | a1 matching authors' q-squared-attack-sim.cpp
    const int32_t poly0 = (static_cast<int32_t>(a0) << 16) | (static_cast<uint16_t>(a1));

    out.h[0] = hw32(static_cast<uint16_t>(a0));
    int32_t tmp = smul(T(poly0), T(poly1));
    out.h[1] = hw32(tmp);

    int32_t tmp2 = smul(B(tmp), QINV);
    out.h[2] = hw32(tmp2);

    tmp2 = smul(Q, B(tmp2)) + tmp;
    out.h[3] = hw32(tmp2);

    tmp2 = smul(T(tmp2), zeta);
    out.h[4] = hw32(tmp2);

    tmp2 = tmp2 + smul(B(poly0), B(poly1));
    out.h[5] = hw32(tmp2);

    tmp = smul(B(tmp2), QINV);
    out.h[6] = hw32(tmp);

    tmp = smul(Q, B(tmp)) + tmp2;
    out.h[7] = hw32(tmp);

    tmp2 = smul(T(poly0), B(poly1)) + smul(B(poly0), T(poly1));
    out.h[8] = hw32(tmp2);

    int32_t tmp3 = smul(B(tmp2), QINV);
    out.h[9] = hw32(tmp3);

    tmp3 = smul(Q, B(tmp3)) + tmp2;
    out.h[10] = hw32(tmp3);

    int32_t mytmp = (tmp3 >> 16);
    tmp = (mytmp << 16) | (static_cast<uint16_t>(B(tmp)));
    out.h[11] = hw32(tmp);
    out.h[12] = hw32(tmp3);
}

int main(int argc, char **argv) {
    int num_trials = 2000;
    std::string out_filename = "replication/phase2_noisy/q2_noisy_sweep_results.txt";

    if (argc > 1) {
        num_trials = std::atoi(argv[1]);
    }
    if (argc > 2) {
        out_filename = argv[2];
    }

    std::cout << "======================================================================\n";
    std::cout << "    FULL-SCALE q^2 NOISY MONTE CARLO SIMULATOR (11,082,241 CANDIDATES)\n";
    std::cout << "======================================================================\n";
    std::cout << "[*] Candidates per trial: " << NUM_CANDIDATES << " (3329 x 3329 full space)\n";
    std::cout << "[*] Trials per sigma:     " << num_trials << "\n";
    std::cout << "[*] OpenMP Max Threads:   " << omp_get_max_threads() << "\n";
    std::cout << "[*] Output file:          " << out_filename << "\n\n";

    const int16_t b0 = 2682;
    const int16_t b1 = 2345;
    const int16_t zeta = 2226;

    // 1. Precompute all 11,082,241 candidate templates
    std::cout << "[*] Precomputing full template table (11,082,241 templates, ~177 MB)..." << std::flush;
    auto t_start_pre = std::chrono::high_resolution_clock::now();
    std::vector<TemplateQ2Compact> all_templates(NUM_CANDIDATES);

    #pragma omp parallel for schedule(static)
    for (int a0 = 0; a0 < Q; ++a0) {
        for (int a1 = 0; a1 < Q; ++a1) {
            int32_t idx = a0 * Q + a1;
            compute_template_q2_compact(static_cast<int16_t>(a0), static_cast<int16_t>(a1), b0, b1, zeta, all_templates[idx]);
        }
    }
    auto t_end_pre = std::chrono::high_resolution_clock::now();
    double pre_secs = std::chrono::duration<double>(t_end_pre - t_start_pre).count();
    std::cout << " Done (" << std::fixed << std::setprecision(2) << pre_secs << "s)!\n\n";

    // 2. Setup Noise Sweep
    std::vector<double> sigmas = {0.5, 0.6, 0.7, 0.8, 0.9, 1.0};
    if (argc > 3) {
        sigmas = {std::atof(argv[3])};
    }

    struct ResultRow {
        double sigma;
        double p1;
        double p2;
        double p3;
        double p10;
        double p100;
        double elapsed;
    };
    std::vector<ResultRow> results;

    std::cout << "sigma\tTop 1\tTop 2\tTop 3\tTop 10\tTop 100\tRuntime\n";
    std::cout << "----------------------------------------------------------------------\n";

    for (double sigma : sigmas) {
        auto t_start_sigma = std::chrono::high_resolution_clock::now();

        int top1 = 0, top2 = 0, top3 = 0, top10 = 0, top100 = 0;

        #pragma omp parallel
        {
            // Thread-local RNG
            std::mt19937 rng(1337 + omp_get_thread_num() * 10007 + static_cast<int>(sigma * 1000));
            std::uniform_int_distribution<int32_t> dist_cand(0, NUM_CANDIDATES - 1);
            std::normal_distribution<float> noise_dist(0.0f, static_cast<float>(sigma));

            int local_top1 = 0, local_top2 = 0, local_top3 = 0, local_top10 = 0, local_top100 = 0;

            #pragma omp for schedule(dynamic, 16)
            for (int trial = 0; trial < num_trials; ++trial) {
                int32_t true_idx = dist_cand(rng);
                const TemplateQ2Compact &true_t = all_templates[true_idx];

                // Generate simulated noisy trace L (13 samples)
                float L[13];
                for (int k = 0; k < 13; ++k) {
                    L[k] = static_cast<float>(true_t.h[k]) + noise_dist(rng);
                }

                // Calculate Euclidean distance for true candidate
                float true_dist = 0.0f;
                for (int k = 0; k < 13; ++k) {
                    float diff = L[k] - static_cast<float>(true_t.h[k]);
                    true_dist += diff * diff;
                }

                // Rank against all 11,082,241 candidates with early break
                int rank = 1;
                for (int32_t c = 0; c < NUM_CANDIDATES; ++c) {
                    if (c == true_idx) continue;

                    const TemplateQ2Compact &cand = all_templates[c];
                    float d = 0.0f;

                    // Unrolled 13-step loop with early distance cutoff
                    #pragma unroll
                    for (int k = 0; k < 13; ++k) {
                        float diff = L[k] - static_cast<float>(cand.h[k]);
                        d += diff * diff;
                        if (d >= true_dist) break;
                    }

                    if (d < true_dist) {
                        ++rank;
                        // If rank exceeds 100, we already know it is not in Top 1, 2, 3, 10, or 100
                        // (Optimization: can continue for full rank or prune if only Top 100 needed)
                        // To be 100% exact for Top 1..100, we only need to count up to 101:
                        if (rank > 100) break;
                    }
                }

                if (rank <= 1) ++local_top1;
                if (rank <= 2) ++local_top2;
                if (rank <= 3) ++local_top3;
                if (rank <= 10) ++local_top10;
                if (rank <= 100) ++local_top100;
            }

            #pragma omp atomic
            top1 += local_top1;
            #pragma omp atomic
            top2 += local_top2;
            #pragma omp atomic
            top3 += local_top3;
            #pragma omp atomic
            top10 += local_top10;
            #pragma omp atomic
            top100 += local_top100;
        }

        auto t_end_sigma = std::chrono::high_resolution_clock::now();
        double elapsed_sigma = std::chrono::duration<double>(t_end_sigma - t_start_sigma).count();

        double p1 = static_cast<double>(top1) / num_trials;
        double p2 = static_cast<double>(top2) / num_trials;
        double p3 = static_cast<double>(top3) / num_trials;
        double p10 = static_cast<double>(top10) / num_trials;
        double p100 = static_cast<double>(top100) / num_trials;

        std::cout << std::fixed << std::setprecision(4)
                  << sigma << "\t"
                  << p1 << "\t"
                  << p2 << "\t"
                  << p3 << "\t"
                  << p10 << "\t"
                  << p100 << "\t"
                  << std::setprecision(1) << elapsed_sigma << "s\n";

        results.push_back({sigma, p1, p2, p3, p10, p100, elapsed_sigma});
    }

    std::cout << "----------------------------------------------------------------------\n\n";

    // 3. Write results to file
    std::ofstream out_file(out_filename);
    if (out_file.is_open()) {
        out_file << "# Full-Scale q^2 Independent Monte Carlo Noise Sweep\n";
        out_file << "# Candidates: " << NUM_CANDIDATES << " | Trials per sigma: " << num_trials << "\n";
        out_file << "sigma\tTop 1\tTop 2\tTop 3\tTop 10\tTop 100\n";
        for (const auto &r : results) {
            out_file << std::fixed << std::setprecision(4)
                     << r.sigma << "\t"
                     << r.p1 << "\t"
                     << r.p2 << "\t"
                     << r.p3 << "\t"
                     << r.p10 << "\t"
                     << r.p100 << "\n";
        }
        out_file.close();
        std::cout << "[+] Successfully exported independent results to: " << out_filename << "\n";
    } else {
        std::cerr << "[-] Error: Failed to open output file " << out_filename << "\n";
    }

    return 0;
}
