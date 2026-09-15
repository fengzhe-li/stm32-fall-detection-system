#!/usr/bin/env python3
"""Host-only test for Bug fix round 3: the KEY4 cancel-alarm / fall-suppression
control-logic fix (FallDetection / KeySettings / AlarmAndSendSMS), validated
directly against the current firmware in firmware/User/.

Validates:
  - Cancel pressed during an active, still-counting-down fall suppresses the
    pending fall SMS for that event and silences the buzzer immediately.
  - Cancel pressed after the fall alarm already fired silences the buzzer and
    does not cause a duplicate SMS.
  - After recovery, a later, independent fall event still alarms normally —
    cancel does not permanently suppress future falls.

Run from the repository root: python3 tests/BUGFIX_ROUND_3_VERIFY.py
Requires a Clang toolchain with AddressSanitizer/UndefinedBehaviorSanitizer.
Does not build, flash, or modify STM32 firmware; nothing under firmware/ is
written to. Does not re-check round 1/2 scope.
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

ks = function(main, 'KeySettings')
assert 'if(FallFlag==1)' in ks, 'expected the cancel branch to key off the current-fall state'
assert 'if(((u16)acc)<40)' not in ks, 'the old recovery-threshold guard must not be present in the cancel branch'

HEAD = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "GPS.h"
typedef uint8_t u8;
typedef uint16_t u16;

u8 setn = 0;
float adx, ady, adz;
float acc;
u8 alarmFlag = 0;
u8 FallFlag = 0;
u8 InitFlag = 1;
u8 SendFlag = 0;
u8 GpsInitOkFlag = 0;
u8 SOS_Flag = 0;
u8 Twinkle = 0;
u8 FallTime = 10;
u8 getData = 0;
u8 SetPhoneNumFlag = 0;
u8 CancelAlarm = 0;
short temperature = 300;
u8 hrMin = 60, hrMax = 120;
u16 teMin = 200, teMax = 370;
u8 spoMin = 85;
u8 BEEP = 0;
int32_t hrAvg = 0, spo2Avg = 0;
char PhoneNumber[11] = "12345678910";
char ConversionNum[44];
GPS_INFO GPS;

static float test_acc_x;
void adxl345_read_average(float *x, float *y, float *z, int n) {
    (void)n; *x = test_acc_x; *y = 0; *z = 0;
}
void OLED_CLS(void) {}
void OLED_ShowChar(u8 x, u8 y, u8 c, u8 size, u8 mode) { (void)x; (void)y; (void)c; (void)size; (void)mode; }
void OLED_ShowCN(u8 x, u8 y, u8 no, u8 mode) { (void)x; (void)y; (void)no; (void)mode; }
void OLED_ShowStr(int x, int y, u8 *s, int size) { (void)x; (void)y; (void)s; (void)size; }
void DelayMs(int x) { (void)x; }
static u8 test_keynum;
u8 KEY_Scan(u8 mode) { (void)mode; return test_keynum; }
void DisplaySetValue(void) {}
static void SavePhoneNumber(const char *number) { (void)number; }
void PhoneNumTranscoding(void) {}

static int sms_count;
static char last_sms[512];
void gsm_send_msg(const char *n, char *s) {
    (void)n; assert(strlen(s) < sizeof(last_sms));
    strcpy(last_sms, s); sms_count++;
}

#define FLASH_SAVE_ADDR ((u32)0x0800F000)
typedef uint32_t u32;
'''

RUNNER = r'''
static void reset_all(void) {
    setn = 0; alarmFlag = 0; FallFlag = 0; FallTime = 10; CancelAlarm = 0;
    BEEP = 0; SOS_Flag = 0; getData = 0; SetPhoneNumFlag = 0;
    hrAvg = 0; spo2Avg = 0; temperature = 300; teMin = 200; teMax = 370;
    sms_count = 0; last_sms[0] = 0; test_keynum = 0;
}
static void press_cancel(void) { test_keynum = 5; KeySettings(); test_keynum = 0; }

int main(void) {
    /* --- Scenario 1: cancel during an active fall, before FallTime==0 --- */
    reset_all();
    test_acc_x = 250; FallDetection();               /* fall entry: FallFlag=1, FallTime=10 */
    assert(FallFlag == 1 && FallTime == 10);
    AlarmAndSendSMS();                                 /* FallTime!=0: must not fire yet */
    assert(sms_count == 0);
    press_cancel();                                    /* user cancels while still fallen */
    assert(CancelAlarm == 1 && BEEP == 0);
    assert((alarmFlag & 0x10) != 0);                   /* fix: suppression armed immediately */
    FallTime = 0;                                       /* simulate countdown having elapsed (unchanged logic) */
    AlarmAndSendSMS();                                  /* must NOT send the fall SMS */
    assert(sms_count == 0 && BEEP == 0);
    printf("PASS 1: cancel during active fall suppresses the pending fall SMS; buzzer stays off.\n");

    /* --- Scenario 2: cancel after the fall alarm already fired --- */
    reset_all();
    test_acc_x = 250; FallDetection();
    FallTime = 0;
    AlarmAndSendSMS();                                  /* fires: bit 0x10 set, BEEP=1, one SMS sent */
    assert(sms_count == 1 && BEEP == 1 && (alarmFlag & 0x10) != 0);
    press_cancel();
    assert(BEEP == 0);                                  /* buzzer off immediately */
    AlarmAndSendSMS();                                  /* next loop pass: must not re-fire/duplicate */
    assert(sms_count == 1 && BEEP == 0);
    printf("PASS 2: cancel after the fall alarm fired silences the buzzer and sends no duplicate SMS.\n");

    /* --- Scenario 3: recovery clears suppression; a later NEW fall still alarms --- */
    reset_all();
    FallFlag = 1; FallTime = 0; alarmFlag = 0x10; CancelAlarm = 1; BEEP = 0; /* prior cancelled+fired fall */
    test_acc_x = 10; FallDetection();                   /* recovery: FallFlag -> 0 */
    assert(FallFlag == 0);
    assert(sms_count == 0);                             /* CancelAlarm still 1: recovery SMS suppressed too */
    AlarmAndSendSMS();                                  /* FallFlag==0 branch clears the suppression bit */
    assert((alarmFlag & 0x10) == 0);
    test_acc_x = 250; FallDetection();                   /* a brand-new fall event */
    assert(FallFlag == 1 && FallTime == 10);
    FallTime = 0;                                        /* simulate its own countdown elapsing */
    AlarmAndSendSMS();                                   /* must alarm normally: not stuck suppressed */
    assert(sms_count == 1 && (alarmFlag & 0x10) != 0);
    printf("PASS 3: after recovery, a later new fall event still triggers its own alarm normally.\n");

    puts("PASS: KEY4 cancel-alarm fix verified for all three scenarios.");
    return 0;
}
'''

parts = [HEAD]
for name in ['AddressTranscoding', 'ContentHandle', 'FallDetection', 'KeySettings', 'AlarmAndSendSMS']:
    parts.append(function(main, name))
parts.append(RUNNER)

with tempfile.TemporaryDirectory(prefix='round3-verify-') as td:
    d = Path(td)
    (d / 'test.c').write_text('\n'.join(parts))
    cmd = ['clang', '-std=c99', '-O1', '-g', '-fsanitize=address,undefined',
           '-fno-sanitize-recover=all', '-I' + str(FIRMWARE / 'User'), str(d / 'test.c'), '-o', str(d / 'test')]
    subprocess.run(cmd, check=True)
    subprocess.run([str(d / 'test')], check=True)

print('Host harness only, scoped to Bug fix round 3. No Keil firmware build or hardware verification.')
