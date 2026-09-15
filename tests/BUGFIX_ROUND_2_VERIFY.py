#!/usr/bin/env python3
"""Host-only tests for Bug fix round 2, validated directly against the current
firmware in firmware/User/:
  1. GetHeartRateSpO2 flat-signal divide-by-zero guard (un_max == un_min).
  2. GPS_RMC_Parse hemisphere sign (N/E stay positive, S/W become negative).

Run from the repository root: python3 tests/BUGFIX_ROUND_2_VERIFY.py
Requires a Clang toolchain with AddressSanitizer/UndefinedBehaviorSanitizer
(Part A additionally requires -fsanitize=float-divide-by-zero support).
Does not build, flash, or modify STM32 firmware; nothing under firmware/ is
written to. Does not re-check round 1 scope.
"""
from pathlib import Path
import re
import subprocess
import tempfile

REPO_ROOT = Path(__file__).resolve().parent.parent
FIRMWARE = REPO_ROOT / 'firmware'


def src(name):
    return (FIRMWARE / 'User' / name).read_bytes().decode('gb18030').replace('\r\n', '\n')


def function(text, name):
    m = re.search(r'(?m)^(?:static )?[\w* ]+\b' + re.escape(name) + r'\([^;]*?\)\s*(?://[^\n]*)?\s*\{', text)
    assert m, name
    start = m.start()
    brace = text.index('{', m.start())
    depth = 0
    tokens = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]')
    for t in tokens.finditer(text, brace):
        if t.group() == '{':
            depth += 1
        elif t.group() == '}':
            depth -= 1
            if depth == 0:
                return text[start:t.end()]
    raise AssertionError(name)


main = src('main.c')
fn = function(main, 'GetHeartRateSpO2')
assert 'un_max == un_min' in fn, 'expected the flat-signal guard to be present in GetHeartRateSpO2'

# ---------------------------------------------------------------------------
# Part A: GetHeartRateSpO2 flat-signal divide-by-zero guard
# ---------------------------------------------------------------------------
HEAD = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8;
#define MAX_BRIGHTNESS 255
uint32_t aun_ir_buffer[150];
uint32_t aun_red_buffer[150];
int32_t n_ir_buffer_length = 150;
int32_t n_spo2, n_heart_rate;
int8_t ch_spo2_valid, ch_hr_valid;
uint32_t un_min, un_max, un_prev_data, un_brightness;
short temperature;
int32_t hr_buf[16], hrSum, hrAvg;
int32_t spo2_buf[16], spo2Sum, spo2Avg;
int32_t spo2BuffFilled, hrBuffFilled;
int32_t hrValidCnt, spo2ValidCnt, hrThrowOutSamp, spo2ThrowOutSamp, spo2Timeout, hrTimeout;

static uint32_t fifo_ir_seq[512], fifo_red_seq[512];
static int fifo_call;
void maxim_max30102_read_fifo(uint32_t *ir, uint32_t *red) {
    *ir = fifo_ir_seq[fifo_call];
    *red = fifo_red_seq[fifo_call];
    fifo_call++;
}
void maxim_heart_rate_and_oxygen_saturation(uint32_t *ir, int32_t n, uint32_t *red, int32_t *spo2, int8_t *spo2_valid, int32_t *hr, int8_t *hr_valid) {
    (void)ir; (void)red; assert(n == 150);
    *spo2 = 98; *spo2_valid = 1; *hr = 85; *hr_valid = 1;
}
short DS18B20_Get_Temp(void) { return 258; }

'''

RUNNER = r'''
static void fill_flat(uint32_t v) {
    int i;
    for (i = 0; i < 512; i++) { fifo_ir_seq[i] = 123; fifo_red_seq[i] = v; }
}
static void fill_rising(uint32_t start) {
    int i;
    for (i = 0; i < 512; i++) { fifo_ir_seq[i] = 123; fifo_red_seq[i] = start + (uint32_t)i; }
}
static void seed_buffers_from_seq(void) {
    int i;
    fifo_call = 0;
    for (i = 0; i < 150; i++) { aun_ir_buffer[i] = fifo_ir_seq[fifo_call]; aun_red_buffer[i] = fifo_red_seq[fifo_call]; fifo_call++; }
}
int main(int argc, char **argv) {
    const char *mode = argc > 1 ? argv[1] : "flat";
    un_brightness = 0; un_prev_data = 0;
    if (!strcmp(mode, "flat")) {
        fill_flat(456);
    } else {
        fill_rising(100);
    }
    seed_buffers_from_seq();
    GetHeartRateSpO2();
    printf("%u\n", un_brightness);
    return 0;
}
'''


def build_and_run(tag, mode):
    src_text = HEAD + fn + RUNNER
    with tempfile.TemporaryDirectory(prefix='round2-verify-') as td:
        d = Path(td)
        (d / 'test.c').write_text(src_text)
        exe = d / ('test_' + tag)
        cmd = ['clang', '-std=c99', '-O1', '-g',
               '-fsanitize=address,undefined,float-divide-by-zero',
               '-fno-sanitize-recover=all', str(d / 'test.c'), '-o', str(exe)]
        subprocess.run(cmd, check=True)
        return subprocess.run([str(exe), mode], capture_output=True, text=True)


# 1. A flat (no-signal) reading must NOT trap under -fsanitize=float-divide-by-zero.
#    If the guard were missing or wrong, this run would itself abort here.
r = build_and_run('flat', 'flat')
assert r.returncode == 0, 'current GetHeartRateSpO2 must not trap on a flat signal (un_max==un_min): ' + r.stderr
assert int(r.stdout.strip()) == 0, 'flat signal must leave un_brightness at its untouched initial value'
print('PASS A1: flat/no-signal input (un_max==un_min) does not divide by zero; un_brightness left unchanged.')

# 2. Normal (non-flat) operation must still work: deterministic, in-range output,
#    proving the guard did not break the existing brightness calculation.
r1 = build_and_run('rising1', 'rising')
r2 = build_and_run('rising2', 'rising')
assert r1.returncode == 0 and r2.returncode == 0
v1, v2 = int(r1.stdout.strip()), int(r2.stdout.strip())
assert v1 == v2, 'non-flat brightness output is not deterministic: %r vs %r' % (v1, v2)
assert 0 <= v1 <= 255, 'brightness output out of expected [0,255] range: %r' % v1
print('PASS A2: normal (non-flat) signal still produces a deterministic, in-range brightness value (%d).' % v1)

# ---------------------------------------------------------------------------
# Part B: GPS hemisphere sign handling
# ---------------------------------------------------------------------------
gps_head = r'''
#include <assert.h>
#include <stdio.h>
#include <math.h>
#include <string.h>
#include "GPS.h"
'''
gps_runner = r'''
int main(void) {
    GPS_INFO GPS;
    const char *ne = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A\r\n";
    const char *sw = "$GPRMC,123519,A,4807.038,S,01131.000,W,022.4,084.4,230394,003.1,W*6A\r\n";
    memset(&GPS, 0, sizeof GPS);
    assert(GPS_RMC_Parse((char*)ne, &GPS) == 1);
    assert(GPS.latitude_Degree > 0 && fabs(GPS.latitude_Degree - 48.1173) < 0.00001);
    assert(GPS.longitude_Degree > 0 && fabs(GPS.longitude_Degree - 11.516667) < 0.00001);

    memset(&GPS, 0, sizeof GPS);
    assert(GPS_RMC_Parse((char*)sw, &GPS) == 1);
    assert(GPS.latitude_Degree < 0 && fabs(GPS.latitude_Degree - (-48.1173)) < 0.00001);
    assert(GPS.longitude_Degree < 0 && fabs(GPS.longitude_Degree - (-11.516667)) < 0.00001);

    puts("PASS B: GPS hemisphere sign correct for N/E (positive) and S/W (negative).");
    return 0;
}
'''
gps_src = gps_head + src('GPS.c') + gps_runner
with tempfile.TemporaryDirectory(prefix='round2-gps-verify-') as td:
    d = Path(td)
    (d / 'test_gps.c').write_text(gps_src)
    exe = d / 'test_gps'
    cmd = ['clang', '-std=c99', '-O1', '-g', '-fsanitize=address,undefined',
           '-fno-sanitize-recover=all', '-I' + str(FIRMWARE / 'User'), str(d / 'test_gps.c'), '-o', str(exe)]
    subprocess.run(cmd, check=True)
    r = subprocess.run([str(exe)], check=True, capture_output=True, text=True)
    print(r.stdout.strip())

print('Host harness only, scoped to Bug fix round 2. No Keil firmware build or hardware verification.')
