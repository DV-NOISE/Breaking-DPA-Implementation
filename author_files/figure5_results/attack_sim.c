#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#define KYBER_N 256
#define KYBER_Q 3329

// assuming max weight = 32
#define NBINS_HW 32

typedef struct {
    int16_t coeffs[KYBER_N];
} poly;

const int16_t q = 3329;
const int16_t qinv = 3327;

const int16_t zetas[64] = { 2226, 430, 555, 843, 2078, 871, 1550, 105, 422, 587, 177, 3094, 3038, 2869,
1574, 1653, 3083, 778, 1159, 3182, 2552, 1483, 2727, 1119, 1739, 644, 2457, 349,
418, 329, 3173, 3254, 817, 1097, 603, 610, 1322, 2044, 1864, 384, 2114, 3193,
1218, 1994, 2455, 220, 2142, 1670, 2144, 1799, 2051, 794, 1819, 2475, 2459, 478,
3221, 3021, 996, 991, 958, 1869, 1522, 1628 };

const int16_t zetas_asm[128] = {
// 7 & 6 & 5 layers
2571, 2970, 1812, 1493, 1422, 287, 202,
// 1st loop of 4 & 3 & 2 layers
3158, 573, 2004, 1223, 652, 2777, 1015,
// 2nd loop of 4 & 3 & 2 layers
622, 264, 383, 2036, 1491, 3047, 1785,
// 3rd loop of 4 & 3 & 2 layers
1577, 2500, 1458, 516, 3321, 3009, 2663,
// 4th loop of 4 & 3 & 2 layers
182, 1727, 3199, 1711, 2167, 126, 1469,
// 5th loop of 4 & 3 & 2 layers
962, 2648, 1017, 2476, 3239, 3058, 830,
// 6th loop of 4 & 3 & 2 layers
2127, 732, 608, 107, 1908, 3082, 2378,
// 7th loop of 4 & 3 & 2 layers
1855, 1787, 411, 2931, 961, 1821, 2604,
// 8th loop of 4 & 3 & 2 layers
1468, 3124, 1758, 448, 2264, 677, 2054,
// 1 layer
2226, 430, 555, 843, 2078, 871, 1550, 105, 422, 587, 177, 3094, 3038, 2869, 1574, 1653, 3083, 778, 1159, 3182, 2552, 1483, 2727, 1119, 1739, 644, 2457, 349, 418, 329, 3173, 3254, 817, 1097, 603, 610, 1322, 2044, 1864, 384, 2114, 3193, 1218, 1994, 2455, 220, 2142, 1670, 2144, 1799, 2051, 794, 1819, 2475, 2459, 478, 3221, 3021, 996, 991, 958, 1869, 1522, 1628,
};

const int16_t zetas_inv_asm[128] = {
// 1 layer
1701, 1807, 1460, 2371, 2338, 2333, 308, 108, 2851, 870, 854, 1510, 2535, 1278, 1530, 1185, 1659, 1187, 3109, 874, 1335, 2111, 136, 1215, 2945, 1465, 1285, 2007, 2719, 2726, 2232, 2512, 75, 156, 3000, 2911, 2980, 872, 2685, 1590, 2210, 602, 1846, 777, 147, 2170, 2551, 246, 1676, 1755, 460, 291, 235, 3152, 2742, 2907, 3224, 1779, 2458, 1251, 2486, 2774, 2899, 1103,
// 1st loop of 2 & 3 & 4 layers
1275, 2652, 1065, 2881, 1571, 205, 1861,
// 2nd loop of 2 & 3 & 4 layers
725, 1508, 2368, 398, 2918, 1542, 1474,
// 3rd loop of 2 & 3 & 4 layers
951, 247, 1421, 3222, 2721, 2597, 1202,
// 4th loop of 2 & 3 & 4 layers
2499, 271, 90, 853, 2312, 681, 2367,
// 5th loop of 2 & 3 & 4 layers
1860, 3203, 1162, 1618, 130, 1602, 3147,
// 6th loop of 2 & 3 & 4 layers
666, 320, 8, 2813, 1871, 829, 1752,
// 7th loop of 2 & 3 & 4 layers
1544, 282, 1838, 1293, 2946, 3065, 2707,
// 8th loop of 2 & 3 & 4 layers
2314, 552, 2677, 2106, 1325, 2756, 171,
// 5 & 6 & 7 layers
3127, 3042, 1907, 1836, 1517, 359, 1932,
// 128^-1 * 2^32
1441
};



void print_bytes(char* ptr, int N) {
  int i;
  for(i = 0; i < N; i += 1) {
    printf("%hhx ", ptr[i]);
  }
  printf("\n");
}

void print_log(char* s, char* ptr, int N) {
  printf("%s: ", s);
  int i;
  for(i = 0; i < N; i += 1) {
    printf("%hhx ", ptr[i]);
  }
  printf("\n");
}

void print_poly(poly *a) {
  int i;
  for (i = 0; i < KYBER_N; i+= 1) {
    printf("%d ", a->coeffs[i]);
  }
  printf("\n");
}

// Take L1 difference between tuples and a random $x$.

// https://stackoverflow.com/questions/37711736/how-to-calculate-hamming-weight-a-k-a-population-count-i-e-number-of-1-bits
int weight(int32_t x) {
  return __builtin_popcount(x);
}

int32_t smul(int16_t x, int16_t y) {
  /* int32_t product = x * y; */
  int32_t product = x * y;
  return product;
}

int16_t bottom(int32_t x) {
  return (int16_t) x;
}

int16_t top(int32_t x) {
  return (int16_t) (x << 16);
}


void montgomery(int32_t* a, int32_t* tmp) {
  //   smulbt \tmp, \a, \qinv
  int32_t reg;
  reg = smul(bottom(*a), qinv);
  /* print_bytes((char*) tmp, sizeof(*tmp)); */
  /* printf("tmp: %d\n", *tmp); */
  //   smlabb \tmp, \q, \tmp, \a
  reg = smul(bottom(reg), q); // SWITCH ON for full montgomery
  *a = reg;
}

void clear_array(int* arr, int N) {
  int i;
  for (i = 0; i < N; ++i) {
    arr[i] = 0;
  }
}

void clear_float_array(float* arr, int N) {
  int i;
  for (i = 0; i < N; ++i) {
    arr[i] = 0;
  }
}

void print_array(int* arr, int N) {
  printf("[");
  int i;
  for (i = 0; i < N-1; ++i) {
    printf("%d, ", arr[i]);
  }
  printf("%d],\n", arr[i]);
}

void print_tuple(int* arr, int N) {
  int i;
  for (i = 0; i < N-1; ++i) {
    printf("%d, ", arr[i]);
  }
  printf("%d\n", arr[i]);
}

void print_float_array(float* arr, int N) {
  printf("[");
  int i;
  for (i = 0; i < N-1; ++i) {
    printf("%.2f, ", arr[i]);
  }
  printf("%.2f],\n", arr[i]);
}


int max(int* arr, int N) {
  int i;
  int max = arr[0];
  int max_i = 0;
  for (i = 0; i < N; ++i) {
    if (arr[i] > max) {
      max = arr[i];
      max_i = i;
    }
  }
  return max_i;
}

float mean(int* hist, int N) {// unnormalized hist
  int i, sum = 0;
  float mu = 0;
  for (i = 0; i < N; ++i) {
    mu += i*hist[i];
    sum += hist[i];
  }
  return mu/sum;
}

int main() {

  int bins[NBINS_HW] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
			0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};

  int tuple[5] = {0, 0, 0, 0, 0};
  int results[5] = {0, 0, 0, 0, 0};

  int i, j, k, wt = 0;

  FILE *fptr;
  char fname[0x100];

  // try for all possible b
  for (i = 2; i < q; i++) {
    snprintf(fname, sizeof(fname), "templates-b-%d.txt", i);
    fptr = fopen(fname, "w");

    clear_array(bins, NBINS_HW);
    clear_array(tuple, 4);
    for (j = 0; j < q; j++) {
      int32_t tmp = 0; // r9
      int32_t tmp2 = 0; // r10, used also as accumulator
      int32_t tmp4 = 0;
      int32_t tmp5 = 0;

      // simulate loads
      wt = weight(j);
      /* printf("!(%d,", wt); */
      tuple[0] = wt;
      results[0] = j;

      // simulate smul
      tmp = smul(j, i);
      wt = weight(tmp);
      /* printf("%d,", wt); */
      tuple[1] = wt;
      results[1] = tmp;

      // simulate montgomery
      // montgomery (i)
      tmp = smul(bottom(tmp), qinv);
      /* printf("tmp=%d\n", tmp); */
      /* print_bytes((char*)&tmp, sizeof(tmp)); */

      wt = weight(tmp);
      /* printf("%d,", wt); */
      tuple[2] = wt;
      results[2] = tmp;

      // montgomery (ii)
      tmp = smul(bottom(tmp), q);
      tmp2 += tmp; // accumulate in tmp2
      wt = weight(tmp);
      tuple[3] = wt;
      results[3] = tmp;

      // smultb
      tmp2 = smul(top(tmp2), zetas[0]);

      // smlabb
      tmp4 = tmp2;
      tmp2 = smul(j, i);
      tmp2 += tmp4;

      // second montgomery
      // montgomery (i)
      tmp2 = smul(bottom(tmp2), qinv);
      // montgomery (ii)
      tmp2 = smul(bottom(tmp2), q);
      tmp += tmp2;
      wt = weight(tmp2);
      tuple[4] = wt;
      results[4] = tmp2;


      /* printf("tmp=%d, tmp2=%d\n", tmp, tmp2); */

      // smuadx tmp2, poly0, poly1
      // If X is present, the multiplications are bottom × top and top × bottom.
      tmp5 = smul(bottom(j), top(i));
      tmp4 = smul(top(j), bottom(i));

      /* printf("tmp4=%d, tmp5=%d\n", tmp4, tmp5); */


      /* tmp2 = tmp5 + tmp4; */
      /* wt = weight(tmp2); */
      /* tuple[4] = wt; */
      /* results[4] = tmp2; */


      /* print_tuple(tuple, 5); */
      fprintf(fptr,"%d, %d, %d, %d, %d\n", tuple[0], tuple[1],
	      tuple[2], tuple[3], tuple[4]);

      /* print_tuple(results, 5); */

      bins[wt] += 1;
    }

    fclose(fptr);

    printf("%d\n", i);


    /* print_array(bins, NBINS_HW); */
  }

  return 0;
}
