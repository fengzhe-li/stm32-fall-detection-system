#!/usr/bin/env python3
"""Host-only boundary tests for Bug fix round 1, using extracted firmware
functions and hardware mocks.

Validates directly against the current firmware in firmware/User/:
  - Flash read/write bounds and address-unit (byte vs. halfword) handling
  - UART1/UART3 receive-buffer bounds and termination
  - Truncated / malformed GPS and SMS input parsing safety
  - Initialized / bounded sensor-buffer behavior (MAX30102 startup read)

Run from the repository root: python3 tests/BUGFIX_ROUND_1_VERIFY.py
Requires a Clang toolchain with AddressSanitizer/UndefinedBehaviorSanitizer.
Does not build, flash, or modify STM32 firmware; nothing under firmware/ is
written to. All temporary build products go to the system temp directory.
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

head = r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <float.h>
#include "GPS.h"
typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32;
#define STM32_FLASH_BASE 0x08000000U
#define STM32_FLASH_SIZE 64
#define STM_SECTOR_SIZE 1024
#define FLASH_SAVE_ADDR 0x0800F000U
#define USART1_RXBUFF_SIZE 400
#define USART3_RXBUFF_SIZE 80
#define STM32_RX1BUFF_SIZE USART1_RXBUFF_SIZE
#define STM32_RX1_BUF Usart1RecBuf
#define STM32_Rx1Counter RxCounter
#define RESET 0
#define SET 1
#define USART1 1
#define USART3 3
#define USART_IT_RXNE 1
#define USART_FLAG_ORE 2
static unsigned char flash_bytes[65536];
u16 STMFLASH_BUF[512];
static unsigned flash_writes;
void FLASH_Unlock(void) {} void FLASH_Lock(void) {}
void FLASH_ErasePage(u32 a) {assert(a>=STM32_FLASH_BASE && a<=STM32_FLASH_BASE+65536-1024); memset(flash_bytes+(a-STM32_FLASH_BASE),255,1024);}
void FLASH_ProgramHalfWord(u32 a,u16 v) {assert(!(a&1) && a>=STM32_FLASH_BASE && a<=STM32_FLASH_BASE+65534);memcpy(flash_bytes+(a-STM32_FLASH_BASE),&v,2);flash_writes++;}
u16 STMFLASH_ReadHalfWord(u32 a) {u16 v;assert(!(a&1) && a>=STM32_FLASH_BASE && a<=STM32_FLASH_BASE+65534);memcpy(&v,flash_bytes+(a-STM32_FLASH_BASE),2);return v;}
void STMFLASH_Read(u32 a,u16 *p,u16 n);
char PhoneNumber[11],ConversionNum[44];
void DelayMs(int x) {(void)x;}
GPS_INFO GPS;
static char last_display[32],last_sms[400],last_serial[128];
void OLED_ShowStr(int x,int y,u8 *s,int size) {(void)x;(void)y;(void)size;assert(strlen((char*)s)<=11);strcpy(last_display,(char*)s);}
void gsm_send_msg(const char *n,char *s) {(void)n;assert(strlen(s)<sizeof(last_sms));strcpy(last_sms,s);}
int SendFlag,hrAvg=85,spo2Avg=98,temperature=258,GpsInitOkFlag;
char Usart1RecBuf[400],Usart3RecBuf[80];
unsigned int RxCounter;
u8 gsm_rev_start,gsm_rev_okflag,GPS_rx_flag=1;
unsigned char rev_start,rev_stop,gps_flag,num;
static u8 next_byte;
int USART_GetITStatus(int u,int s) {(void)u;(void)s;return SET;}
int USART_GetFlagStatus(int u,int s) {(void)u;(void)s;return RESET;}
u8 USART_ReceiveData(int u) {(void)u;return next_byte;}
void USART_ClearFlag(int u,int s) {(void)u;(void)s;}
void USART_ClearITPendingBit(int u,int s) {(void)u;(void)s;}
u8 CancelAlarm,alarmFlag,BEEP,getData,SetPhoneNumFlag;
static u32 primask;
u32 __get_PRIMASK(void) {return primask;}
void __disable_irq(void) {primask=1;}
void __set_PRIMASK(u32 v) {primask=v;}
void uart_send(char *s,int len) {(void)len;assert(strlen(s)<sizeof(last_serial));strcpy(last_serial,s);}
uint32_t aun_red_buffer[150],aun_ir_buffer[150],un_min,un_max,un_prev_data,un_brightness;
int32_t n_ir_buffer_length,n_spo2,n_heart_rate;int8_t ch_spo2_valid,ch_hr_valid;u8 uch_dummy;
#define REG_INTR_STATUS_1 0
void bsp_InitI2C(void) {} void maxim_max30102_reset(void) {} void maxim_max30102_init(void) {}
void maxim_max30102_read_reg(int reg,u8 *v) {(void)reg;*v=0;}
void maxim_max30102_read_fifo(uint32_t *a,uint32_t *b) {*a=123;*b=456;}
void maxim_heart_rate_and_oxygen_saturation(uint32_t *a,int32_t n,uint32_t *b,int32_t *s,int8_t *sv,int32_t *h,int8_t *hv) {(void)a;(void)b;assert(n==150);*s=98;*sv=1;*h=85;*hv=1;}
'''
parts = [head]
for name in ['STMFLASH_Write_NoCheck', 'STMFLASH_Write', 'STMFLASH_Read']:
    parts.append(function(src('stmflash.c'), name))
for name in ['PhoneNumTranscoding', 'SavePhoneNumber', 'CheckNewMcu', 'AddressTranscoding', 'DisplayLongitudeAndLatitude', 'ContentHandle', 'Init_MAX30102']:
    parts.append(function(main, name))
for file, name in [('usart1.c', 'USART1_IRQHandler'), ('usart3.c', 'USART3_IRQHandler')]:
    parts.append(function(src(file), name))
parts.append(function(main, 'SMS_Receive'))
parts.append(src('GPS.c'))
parts.append(r'''
static void uart3_text(const char *s) {while(*s){next_byte=(u8)*s++;USART3_IRQHandler();}}
static void reset_gps_rx(void) {num=rev_start=rev_stop=gps_flag=0;memset(Usart3RecBuf,0,sizeof Usart3RecBuf);}
static void set_sms(const char *s) {memset(Usart1RecBuf,0,sizeof Usart1RecBuf);strncpy(Usart1RecBuf,s,sizeof Usart1RecBuf-1);SetPhoneNumFlag=0;}
int main(void) {
    u16 words[4]={0x1122,0x3344,0x5566,0x7788},result[4]={0};unsigned before;int i,j;char text[500],coordinate[64];
    const char *rmc="$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A\r\n";
    memset(flash_bytes,255,sizeof flash_bytes);CheckNewMcu();
    assert(memcmp(PhoneNumber,"12345678910",11)==0);assert(memcmp(flash_bytes+0xF010,"FDYDZ",6)==0);
    assert(flash_bytes[0xF016]==255 && flash_bytes[0xF04C]==255);
    SavePhoneNumber("10987654321");CheckNewMcu();assert(memcmp(PhoneNumber,"10987654321",11)==0);
    /* Old-format flash retains meaningful first 11 bytes even with dirty trailing bytes. */
    memcpy(flash_bytes+0xF040,"12345678910",11);memset(flash_bytes+0xF04B,0xA5,11);CheckNewMcu();assert(memcmp(PhoneNumber,"12345678910",11)==0);
    memset(flash_bytes,255,2048);STMFLASH_Write(STM32_FLASH_BASE+1022,words,4);STMFLASH_Read(STM32_FLASH_BASE+1022,result,4);assert(!memcmp(words,result,sizeof words));
    words[0]=7;STMFLASH_Write(STM32_FLASH_BASE+1022,words,4);STMFLASH_Read(STM32_FLASH_BASE+1022,result,4);assert(!memcmp(words,result,sizeof words));
    before=flash_writes;STMFLASH_Write(STM32_FLASH_BASE+65534,words,2);STMFLASH_Write(STM32_FLASH_BASE+1,words,1);STMFLASH_Write(STM32_FLASH_BASE,words,0);assert(flash_writes==before);
    result[0]=0xABCD;STMFLASH_Read(STM32_FLASH_BASE+65534,result,2);assert(result[0]==0xABCD);
    Init_MAX30102();assert(un_prev_data==456);
    for(i=0;i<7;i++) {double vals[]={0,180,-180,90,-90,DBL_MAX,NAN};GPS.longitude_Degree=GPS.latitude_Degree=vals[i];DisplayLongitudeAndLatitude();for(j=0;j<6;j++){SendFlag=j;ContentHandle();assert(strlen(last_sms)<400);}}
    GPS.latitude_Degree=31.123456;snprintf(coordinate,sizeof coordinate,"%10.6f ",GPS.latitude_Degree);DisplayLongitudeAndLatitude();assert(!strcmp(coordinate,last_display));
    for(i=0;i<10000;i++){next_byte='A';USART1_IRQHandler();assert(RxCounter<400 && Usart1RecBuf[RxCounter]==0);}
    next_byte='O';USART1_IRQHandler();next_byte='K';USART1_IRQHandler();assert(gsm_rev_okflag==1);
    reset_gps_rx();text[0]='$';memset(text+1,'A',77);text[78]='\n';text[79]=0;uart3_text(text);assert(rev_stop==1 && strlen(Usart3RecBuf)==79);
    reset_gps_rx();text[78]='A';text[79]='\n';text[80]=0;uart3_text(text);assert(rev_stop==0);uart3_text(rmc);assert(rev_stop==1 && !strcmp(Usart3RecBuf,rmc));
    assert(GPS_RMC_Parse((char*)rmc,&GPS)==1);assert(fabs(GPS.latitude_Degree-48.1173)<0.00001);
    assert(Get_Double_Number("1234567890,")==0);assert(Get_Double_Number("12345")==0);assert(Get_Double_Number("x,")==0);assert(Get_Int_Number("x,")==0);assert(Get_Float_Number("x,")==0);
    assert(Get_Double_Number("12345.678,")>12345);
    assert(GPS_RMC_Parse(NULL,&GPS)==0);assert(GPS_GGA_Parse(NULL,&GPS)==0);assert(GPS_GSV_Parse(NULL,&GPS)==0);
    /* Exact-size allocations make short-frame reads observable to ASan. */
    for(i=0;i<(int)strlen(rmc);i++){char *p=malloc((size_t)i+1);memcpy(p,rmc,(size_t)i);p[i]=0;GPS_RMC_Parse(p,&GPS);GPS_GGA_Parse(p,&GPS);GPS_GSV_Parse(p,&GPS);free(p);}
    for(i=0;i<1000;i++){int n=i%499;for(j=0;j<n;j++)text[j]="123x.,$AC"[(i+j*7)%8];text[n]=0;GPS_RMC_Parse(text,&GPS);GPS_GGA_Parse(text,&GPS);GPS_GSV_Parse(text,&GPS);Get_Double_Number(text);Get_Int_Number(text);Get_Float_Number(text);}
    set_sms("8BBE7F6E624B673A53F77801");SMS_Receive();assert(SetPhoneNumFlag==2);
    set_sms("8BBE7F6E624B673A53F7780100310032003300340035003600370038003900310030\r");SMS_Receive();assert(SetPhoneNumFlag==1 && !memcmp(PhoneNumber,"12345678910",11));
    memset(Usart1RecBuf,'A',400);memcpy(Usart1RecBuf+375,"8BBE7F6E624B673A53F77801",24);SMS_Receive();assert(SetPhoneNumFlag==2);
    set_sms("+CMTI: \"SM\",");last_serial[0]=0;SMS_Receive();assert(last_serial[0]==0);
    set_sms("+CMTI: \"SM\",1\r");SMS_Receive();assert(strstr(last_serial,"AT+CMGR=")==last_serial);
    primask=1;set_sms("");SMS_Receive();assert(primask==1);
    puts("PASS: Flash, coordinate formatting, sensor bounds, UART1/UART3, GPS malformed/truncated inputs, SMS bounds; ASan/UBSan.");return 0;
}
''')
with tempfile.TemporaryDirectory(prefix='round1-verify-') as td:
    d = Path(td)
    (d / 'test.c').write_text('\n'.join(parts))
    cmd = ['clang', '-std=c99', '-O1', '-g', '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
           '-I' + str(FIRMWARE / 'User'), str(d / 'test.c'), '-o', str(d / 'test')]
    subprocess.run(cmd, check=True)
    subprocess.run([str(d / 'test')], check=True)
print('PASS: Round 1 — Flash bounds, UART/GPS receive bounds, malformed/truncated parsing, sensor buffer bounds.')
print('Host harness only. No Keil firmware build or hardware verification.')
