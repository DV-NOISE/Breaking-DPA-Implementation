#include <cstdint>
#include <cstdlib>
#include <cmath>
#include <vector>
#include <random>
#include <algorithm>
#include <iostream>
#include <iomanip>
#include <chrono>

static constexpr int16_t Q = 3329;
static constexpr int16_t QINV = 3327;

static inline int16_t B(int32_t x) { return static_cast<int16_t>(x); }
static inline int16_t T(int32_t x) { return static_cast<int16_t>(x >> 16); }
static inline int32_t smul(int16_t x, int16_t y) { return static_cast<int32_t>(x) * static_cast<int32_t>(y); }
static inline unsigned hw32(int32_t x) { return static_cast<unsigned>(__builtin_popcount(static_cast<uint32_t>(x))); }

struct TemplateQ {
    float h[5];
};

struct TemplateQ2 {
    float h[13];
};

// Generate 5-state template for a1
TemplateQ compute_template_q(int16_t a1, int16_t b1, int16_t zeta) {
    TemplateQ t;
    constexpr int16_t a0 = 0;
    const int32_t poly1 = (static_cast<int32_t>(b1) << 16);
    const int32_t poly0 = (static_cast<int32_t>(a1) << 16) + a0;

    t.h[0] = static_cast<float>(hw32(poly0));
    int32_t tmp = smul(T(poly0), T(poly1));
    t.h[1] = static_cast<float>(hw32(tmp));

    int32_t tmp2 = smul(B(tmp), QINV);
    t.h[2] = static_cast<float>(hw32(tmp2));

    tmp2 = smul(Q, B(tmp2)) + tmp;
    t.h[3] = static_cast<float>(hw32(tmp2));

    tmp2 = smul(T(tmp2), zeta);
    t.h[4] = static_cast<float>(hw32(tmp2));
    return t;
}

// Generate 13-state template for (a0, a1)
TemplateQ2 compute_template_q2(int16_t a0, int16_t a1, int16_t b0, int16_t b1, int16_t zeta) {
    TemplateQ2 t;
    const int32_t poly1 = (static_cast<int32_t>(b1) << 16) | (static_cast<uint16_t>(b0));
    // CHANGELOG (2026-09-12): Corrected poly0 packing from (a1<<16)|a0 to (a0<<16)|a1
    // to match sim_engine.cpp and authors' q-squared-attack-sim.cpp (line 54).
    const int32_t poly0 = (static_cast<int32_t>(a0) << 16) | (static_cast<uint16_t>(a1));

    t.h[0] = static_cast<float>(hw32(static_cast<uint16_t>(a0)));
    int32_t tmp = smul(T(poly0), T(poly1));
    t.h[1] = static_cast<float>(hw32(tmp));

    int32_t tmp2 = smul(B(tmp), QINV);
    t.h[2] = static_cast<float>(hw32(tmp2));

    tmp2 = smul(Q, B(tmp2)) + tmp;
    t.h[3] = static_cast<float>(hw32(tmp2));

    tmp2 = smul(T(tmp2), zeta);
    t.h[4] = static_cast<float>(hw32(tmp2));

    tmp2 = tmp2 + smul(B(poly0), B(poly1));
    t.h[5] = static_cast<float>(hw32(tmp2));

    tmp = smul(B(tmp2), QINV);
    t.h[6] = static_cast<float>(hw32(tmp));

    tmp = smul(Q, B(tmp)) + tmp2;
    t.h[7] = static_cast<float>(hw32(tmp));

    tmp2 = smul(T(poly0), B(poly1)) + smul(B(poly0), T(poly1));
    t.h[8] = static_cast<float>(hw32(tmp2));

    int32_t tmp3 = smul(B(tmp2), QINV);
    t.h[9] = static_cast<float>(hw32(tmp3));

    tmp3 = smul(Q, B(tmp3)) + tmp2;
    t.h[10] = static_cast<float>(hw32(tmp3));

    int32_t mytmp = (tmp3 >> 16);
    tmp = (mytmp << 16) | (static_cast<uint16_t>(B(tmp)));
    t.h[11] = static_cast<float>(hw32(tmp));
    t.h[12] = static_cast<float>(hw32(tmp3));
    return t;
}

int main(int argc, char **argv) {
    int num_trials = 2000;
    if (argc > 1) {
        num_trials = std::atoi(argv[1]);
    }

    std::cout << "Running Noisy Simulation for q-templates (trials=" << num_trials << ")...\n";
    const int16_t b1 = 2345;
    const int16_t zeta = 2226;

    std::vector<TemplateQ> templates_q(Q);
    for (int a = 0; a < Q; ++a) {
        templates_q[a] = compute_template_q(static_cast<int16_t>(a), b1, zeta);
    }

    std::mt19937 rng(42);
    std::uniform_int_distribution<int> dist_secret(0, Q - 1);

    std::vector<double> sigmas = {0.3, 0.4, 0.5, 0.6, 0.7, 0.8};
    if (argc > 2) {
        sigmas = {std::atof(argv[2])};
    }

    std::cout << "\nTable 1 Reproduction (q-templates):\n";
    std::cout << std::fixed << std::setprecision(4);
    std::cout << "sigma\tTop 1\tTop 2\tTop 3\tTop 10\tTop 100\n";
    std::cout << "--------------------------------------------------------\n";

    for (double sigma : sigmas) {
        std::normal_distribution<float> noise(0.0f, static_cast<float>(sigma));

        int top1 = 0, top2 = 0, top3 = 0, top10 = 0, top100 = 0;

        for (int trial = 0; trial < num_trials; ++trial) {
            int true_secret = dist_secret(rng);
            const TemplateQ &true_t = templates_q[true_secret];

            // Simulated noisy trace L
            float L[5];
            for (int k = 0; k < 5; ++k) {
                L[k] = true_t.h[k] + noise(rng);
            }

            // Distance of true candidate
            float true_dist = 0.0f;
            for (int k = 0; k < 5; ++k) {
                float diff = L[k] - true_t.h[k];
                true_dist += diff * diff;
            }

            // Rank against all candidates
            int rank = 1;
            for (int cand = 0; cand < Q; ++cand) {
                if (cand == true_secret) continue;
                float d = 0.0f;
                const TemplateQ &cand_t = templates_q[cand];
                for (int k = 0; k < 5; ++k) {
                    float diff = L[k] - cand_t.h[k];
                    d += diff * diff;
                    if (d >= true_dist) break;
                }
                if (d < true_dist) {
                    ++rank;
                }
            }

            if (rank <= 1) ++top1;
            if (rank <= 2) ++top2;
            if (rank <= 3) ++top3;
            if (rank <= 10) ++top10;
            if (rank <= 100) ++top100;
        }

        std::cout << sigma << "\t"
                  << static_cast<double>(top1) / num_trials << "\t"
                  << static_cast<double>(top2) / num_trials << "\t"
                  << static_cast<double>(top3) / num_trials << "\t"
                  << static_cast<double>(top10) / num_trials << "\t"
                  << static_cast<double>(top100) / num_trials << "\n";
    }
    std::cout << "--------------------------------------------------------\n\n";

    return 0;
}
