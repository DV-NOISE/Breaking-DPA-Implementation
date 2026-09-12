#include <stdio.h>
#include <string>
#include <unordered_map>

#define KYBER_N 256
#define KYBER_Q 3329

#define WEIGHT(x) __builtin_popcount(x)
#define B(x) ((int16_t)x)
#define T(x) ((int16_t)(x >> 16))

const int16_t q = 3329;
const int16_t qinv = 3327;

const int16_t zetas[64] = {
    2226, 430,  555,  843,  2078, 871,  1550, 105,  422,  587,  177,
    3094, 3038, 2869, 1574, 1653, 3083, 778,  1159, 3182, 2552, 1483,
    2727, 1119, 1739, 644,  2457, 349,  418,  329,  3173, 3254, 817,
    1097, 603,  610,  1322, 2044, 1864, 384,  2114, 3193, 1218, 1994,
    2455, 220,  2142, 1670, 2144, 1799, 2051, 794,  1819, 2475, 2459,
    478,  3221, 3021, 996,  991,  958,  1869, 1522, 1628};

int32_t smul(int16_t x, int16_t y) {
  int32_t product = x * y;
  return product;
}

int main() {
  FILE *fptr;
  char fname[0x100];
  char str[0x100];

  int HWS[13] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};

  int16_t a0, a1;
  int16_t b0 = 2682, b1;
  int32_t tmp, tmp2, tmp3 = 0;
  int32_t poly0, poly1 = 0;
  int32_t mytmp = 0;

  std::unordered_map<std::string, int> counts;
  std::unordered_map<int, int> hist;
  std::string serialized_tuple = "";

  // try for all possible b
  for (b1 = 2345; b1 < 2346; b1++) {
    counts.clear();
    hist.clear();
    poly1 = (b1 << 16) + b0;

    for (a0 = 0; a0 < 1; a0++) {
      for (a1 = 0; a1 < q; a1++) {
        // clear all registers
        tmp = 0;
        tmp2 = 0;
        tmp3 = 0;

        // simulate loads
        poly0 = (a1 << 16) + a0;
        HWS[0] = WEIGHT(a1);

        // simulate smul
        tmp = smul(T(poly0), b1); // a1 * b1
        HWS[1] = WEIGHT(tmp);

        // simulate montgomery
        tmp = smul(B(tmp), qinv); // (a1 * b1) * qinv
        HWS[2] = WEIGHT(tmp);

        // montgomery (ii)
        tmp = smul(B(tmp), q); // (a1 * b1 * qinv) * q
        tmp2 += tmp;           // accumulate in tmp2
        HWS[3] = WEIGHT(tmp);

        // smultb
        tmp2 = smul(T(tmp2), zetas[0]); // ((a1 * b1 * qinv) * q) * zeta
        HWS[4] = WEIGHT(tmp2);

        tmp2 =
            tmp2 + smul(B(poly0),
                        B(poly1)); // (a0 * b0) + ((a1 * b1 * qinv) * q) * zeta
        HWS[5] = WEIGHT(tmp2);

        // montgomery q, qinv, tmp2, tmp (but order switched this time)
        tmp2 = smul(B(tmp2), qinv);
        HWS[6] = WEIGHT(tmp2);

        /* // montgomery (ii) */
        tmp2 = smul(B(tmp2), q); //
        tmp += tmp2;             // accumulate in tmp2
        HWS[7] = WEIGHT(tmp2);

        // This produces top × bottom and bottom × top multiplication.
        tmp2 = smul(T(poly0), B(poly1)) + smul(B(poly0), T(poly1));
        HWS[8] = WEIGHT(tmp2);

        /* // montgomery q, qinv, tmp2, tmp3 */
        tmp2 = smul(B(tmp2), qinv);
        HWS[9] = WEIGHT(tmp2);

        /* // montgomery (ii) */
        tmp2 = smul(B(tmp2), q); //
        tmp3 += tmp2;            // accumulate in tmp2
        HWS[10] = WEIGHT(tmp2);

        // pkhTB tmp, tmp3, tmp
        mytmp = (tmp3 >> 16);
        tmp = (mytmp << 16) + B(tmp);
        HWS[11] = WEIGHT(tmp);

        // store tmp3 in at location rptr
        HWS[12] = WEIGHT(tmp3);

        snprintf(str, sizeof(str), "%d,%d,%d,%d,%d", HWS[0], HWS[1], HWS[2],
                 HWS[3], HWS[4]);

        // snprintf(str, sizeof(str), "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d%d",
        // HWS[0], HWS[1], HWS[2], HWS[3], HWS[4], HWS[5], HWS[6], HWS[7],
        // HWS[8], HWS[9], HWS[10], HWS[11], HWS[12]);

        serialized_tuple = str;
        if (counts.find(serialized_tuple) == counts.end()) {
          counts[serialized_tuple] = 1;
        } else {
          counts[serialized_tuple] += 1;
        }
      }
    }

    std::unordered_map<std::string, int>::iterator it = counts.begin();
    while (it != counts.end()) {
      if (hist.find(it->second) == hist.end()) {
        hist[it->second] = 1;
      } else {
        hist[it->second] += 1;
      }
      it++;
    }

    std::unordered_map<int, int>::iterator jt = hist.begin();
    while (jt != hist.end()) {
      printf("%d: %d, ", jt->first, jt->second);
      jt++;
    }
    printf("\n");
  }

  return 0;
}
