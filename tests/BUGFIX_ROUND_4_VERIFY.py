#!/usr/bin/env python3
"""Host-only test for Bug fix round 4: the GSM startup infinite-retry fix in
gsm_atcmd_send()/gsm_init(), validated directly against the current firmware
in firmware/User/main.c.

Validates:
  - gsm_atcmd_send() retries a finite, bounded number of times (does not hang).
  - gsm_init() still returns (with explicit failure) even if every AT command
    fails, so the rest of the firmware can start.
  - The successful modem-response path is unchanged: one send per command,
    no retries, when the modem answers normally.

Run from the repository root: python3 tests/BUGFIX_ROUND_4_VERIFY.py
Requires a Clang toolchain with AddressSanitizer/UndefinedBehaviorSanitizer.
Does not build, flash, or modify STM32 firmware; nothing under firmware/ is
written to. Does not re-check earlier rounds' scope.
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

send_fn = function(main, 'gsm_atcmd_send')
init_fn = function(main, 'gsm_init')
assert re.search(r'\bu8\s+gsm_atcmd_send\(', main), 'gsm_atcmd_send must return u8 (explicit success/failure)'
assert re.search(r'\bu8\s+gsm_init\(', main), 'gsm_init must return u8 (explicit success/failure)'
assert 'GSM_ATCMD_MAX_RETRY' in main, 'expected a finite retry-limit macro'
assert 'while(gsm_rev_okflag == 0)' not in send_fn, 'the old unbounded outer retry loop must not be present'
m = re.search(r'#define\s+GSM_ATCMD_MAX_RETRY\s+(\d+)', main)
assert m, 'GSM_ATCMD_MAX_RETRY macro not found'
MAX_RETRY = int(m.group(1))

# Extract the macro definition line plus both functions as one contiguous block for compilation.
idx_start = main.index('#define GSM_ATCMD_MAX_RETRY')
idx_end = main.index(init_fn) + len(init_fn)
block = main[idx_start:idx_end]
assert send_fn in block and init_fn in block

HEAD = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
typedef uint8_t u8;

u8 gsm_rev_start;
u8 gsm_rev_okflag;

static int send_count;
static int delay_count;
/* mode: 0 = modem never answers; 1 = every attempt answers quickly (after
   `quick_delay` DelayMs calls); 2 = only the `target_send`'th uart_send's
   attempt answers, after `target_delay` DelayMs calls. */
static int mode;
static int quick_delay;
static int target_send;
static int target_delay;

void uart_send(unsigned char *bufs, unsigned char len) {
    (void)bufs; (void)len;
    send_count++;
    delay_count = 0;
}
void DelayMs(int ms) {
    (void)ms;
    delay_count++;
    if (mode == 1 && delay_count >= quick_delay) {
        gsm_rev_okflag = 1;
    } else if (mode == 2 && send_count == target_send && delay_count >= target_delay) {
        gsm_rev_okflag = 1;
    }
}
'''

RUNNER = r'''
static void reset(void) {
    send_count = 0; delay_count = 0; gsm_rev_start = 0; gsm_rev_okflag = 0;
    mode = 0; quick_delay = 0; target_send = 0; target_delay = 0;
}

int main(void) {
    u8 r;

    /* 1. Immediate OK: modem answers within the first couple of ms of the first attempt. */
    reset();
    mode = 1; quick_delay = 1;
    r = gsm_atcmd_send("AT\r\n");
    assert(r == 1);
    assert(send_count == 1);                         /* no retry needed */
    printf("PASS 1: immediate OK -> success on first attempt, no retries sent.\n");

    /* 2. Delayed OK: modem stays silent on attempt 1, answers partway into attempt 2. */
    reset();
    mode = 2; target_send = 2; target_delay = 5;
    r = gsm_atcmd_send("AT\r\n");
    assert(r == 1);
    assert(send_count == 2);                         /* confirms the AT string was re-sent once */
    printf("PASS 2: OK delayed until a retry -> success, AT command re-sent exactly once.\n");

    /* 3. No OK at all: gsm_atcmd_send must exit after exactly GSM_ATCMD_MAX_RETRY sends. */
    reset();
    r = gsm_atcmd_send("AT\r\n");
    assert(r == 0);
    assert(send_count == GSM_ATCMD_MAX_RETRY);
    printf("PASS 3a: no OK ever -> gsm_atcmd_send exits after exactly %d attempts (does not hang).\n", GSM_ATCMD_MAX_RETRY);

    /* 3b. gsm_init must also return (not hang) and report explicit failure when the modem never answers. */
    reset();
    r = gsm_init();
    assert(r == 0);
    assert(send_count == 6 * GSM_ATCMD_MAX_RETRY);   /* all six AT commands attempted, each bounded */
    printf("PASS 3b: no OK ever -> gsm_init still returns (failure=0) after running all six commands.\n");

    /* 4. Normal modem: every command answers quickly -> unchanged one-send-per-command behavior. */
    reset();
    mode = 1; quick_delay = 1;
    r = gsm_init();
    assert(r == 1);
    assert(send_count == 6);                         /* one send per command, no retries: unchanged from before the fix */
    printf("PASS 4: normal modem responses -> unchanged one-send-per-command behavior preserved.\n");

    puts("PASS: GSM startup infinite-retry fix verified for all scenarios.");
    return 0;
}
'''

parts = [HEAD, block, RUNNER]

with tempfile.TemporaryDirectory(prefix='round4-verify-') as td:
    d = Path(td)
    (d / 'test.c').write_text('\n'.join(parts))
    cmd = ['clang', '-std=c99', '-O1', '-g', '-fsanitize=address,undefined',
           '-fno-sanitize-recover=all', str(d / 'test.c'), '-o', str(d / 'test')]
    subprocess.run(cmd, check=True)
    subprocess.run([str(d / 'test')], check=True)

print('Host harness only, scoped to Bug fix round 4. No Keil firmware build or hardware verification.')
