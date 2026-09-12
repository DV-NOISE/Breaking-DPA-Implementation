#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <unordered_map>

// Clean reproducer for the upper (q-template) part of Figure 5 in
// "Breaking DPA-protected Kyber via the pair-pointwise multiplication".
//
// It mirrors the old q-attack simulator's five Hamming-weight states,
// while making the averaging over public b1 explicit.

static constexpr int16_t Q = 3329;
static constexpr int16_t QINV = 3327;

static inline int16_t B(int32_t x) {
    return static_cast<int16_t>(x);
}

static inline int16_t T(int32_t x) {
    return static_cast<int16_t>(x >> 16);
}

static inline int32_t smul(int16_t x, int16_t y) {
    return static_cast<int32_t>(x) * static_cast<int32_t>(y);
}

// The old code used __builtin_popcount on an int. Casting to uint32_t
// makes the intended 32-bit two's-complement Hamming weight explicit.
static inline unsigned hw32(int32_t x) {
    return static_cast<unsigned>(__builtin_popcount(static_cast<uint32_t>(x)));
}

// Each Hamming weight is <= 32, so 6 bits per component are enough.
static inline uint32_t pack5(unsigned h0, unsigned h1, unsigned h2,
                             unsigned h3, unsigned h4) {
    return h0 | (h1 << 6) | (h2 << 12) | (h3 << 18) | (h4 << 24);
}

struct Probabilities {
    double one = 0.0;
    double two = 0.0;
    double three = 0.0;
};

static Probabilities distribution_for_b(int16_t b1, int16_t zeta) {
    std::unordered_map<uint32_t, unsigned> counts;
    counts.reserve(Q * 2);

    // For the odd-coefficient experiment a0 is irrelevant to the five
    // selected states. Setting it to zero avoids the uninitialized a0
    // present in the historical q-attack-sim.cpp snapshot.
    constexpr int16_t a0 = 0;
    const int32_t poly1 = (static_cast<int32_t>(b1) << 16);

    for (int a = 0; a < Q; ++a) {
        const int16_t a1 = static_cast<int16_t>(a);

        // Same five states as HWS[0]..HWS[4] in the old simulator.
        const int32_t poly0 = (static_cast<int32_t>(a1) << 16) + a0;
        const unsigned h0 = hw32(poly0); // equivalently HW(a1) because a0=0

        int32_t tmp = smul(T(poly0), T(poly1)); // a1 * b1
        const unsigned h1 = hw32(tmp);

        int32_t tmp2 = smul(B(tmp), QINV);
        const unsigned h2 = hw32(tmp2);

        tmp2 = smul(Q, B(tmp2)) + tmp;
        const unsigned h3 = hw32(tmp2);

        tmp2 = smul(T(tmp2), zeta);
        const unsigned h4 = hw32(tmp2);

        ++counts[pack5(h0, h1, h2, h3, h4)];
    }

    uint64_t in_one_way = 0;
    uint64_t in_two_way = 0;
    uint64_t in_three_way = 0;

    // Figure 5 probabilities are coefficient probabilities: if a tuple
    // occurs m times, all m coefficients belong to an m-way collision.
    for (const auto &kv : counts) {
        const unsigned m = kv.second;
        if (m == 1) in_one_way += 1;
        else if (m == 2) in_two_way += 2;
        else if (m == 3) in_three_way += 3;
    }

    return {
        static_cast<double>(in_one_way) / Q,
        static_cast<double>(in_two_way) / Q,
        static_cast<double>(in_three_way) / Q
    };
}

int main(int argc, char **argv) {
    // Default reproduces the first q-template row of Figure 5.
    int zeta_arg = 2226;
    if (argc >= 2) {
        zeta_arg = std::atoi(argv[1]);
    }
    if (zeta_arg < INT16_MIN || zeta_arg > INT16_MAX) {
        std::cerr << "zeta must fit in int16_t\n";
        return 1;
    }
    const int16_t zeta = static_cast<int16_t>(zeta_arg);

    long double sum1 = 0.0L, sum2 = 0.0L, sum3 = 0.0L;

    // These are the bounds that reproduce the published Figure 5 values:
    // b1 = 0,...,q-1.  (The prose in Appendix B says [1,...,q-1], which
    // does not exactly match the published numbers.)
    for (int b = 0; b < Q; ++b) {
        const auto p = distribution_for_b(static_cast<int16_t>(b), zeta);
        sum1 += p.one;
        sum2 += p.two;
        sum3 += p.three;
    }

    std::cout << std::fixed << std::setprecision(10);
    std::cout << "zeta = " << zeta << "\n";
    std::cout << "average over b1 = 0,...," << (Q - 1) << "\n";
    std::cout << "1-way: " << static_cast<double>(sum1 / Q) << "\n";
    std::cout << "2-way: " << static_cast<double>(sum2 / Q) << "\n";
    std::cout << "3-way: " << static_cast<double>(sum3 / Q) << "\n";

    return 0;
}
