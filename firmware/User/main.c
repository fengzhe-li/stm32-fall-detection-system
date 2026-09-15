#include "stm32f10x.h"
#include "OLED_I2C.h"
#include "ds18b20.h"
#include "usart1.h"
#include "usart3.h"
#include "delay.h"
#include "algorithm.h"
#include "max30102.h"
#include "myiic.h"
#include "key.h"
#include "iic.h"
#include "stdio.h"
#include "string.h"
#include "adxl345.h"
#include "stmflash.h"
#include "GPS.h"

#define FLASH_SAVE_ADDR  ((u32)0x0800F000) 				//设置FLASH 保存地址(必须为偶数)

#define STM32_RX1_BUF       Usart1RecBuf 
#define STM32_Rx1Counter    RxCounter
#define STM32_RX1BUFF_SIZE  USART1_RXBUFF_SIZE

#define STM32_RX3_BUF       Usart3RecBuf 
#define STM32_Rx3Counter    Rx3Counter
#define STM32_RX3BUFF_SIZE  USART3_RXBUFF_SIZE
u8 oled_buffer[50];
char   PhoneNumber[11];//手机号码
char ConversionNum[44];//手机号码转码后存放数组

u8 setn=0;//设置键按下次数记录
float adx,ady,adz;
float acc;
u8 alarmFlag=0x00;
u8 FallFlag=0;						//摔倒标志
u8 InitFlag=1;						//初始化标志
u8 SendFlag=0;						//不同报警标志，发送不同内容短信
u8 GpsInitOkFlag=0; 			//GPS定位接收成功标志
u8 SOS_Flag=0;						//一键SOS标志
u8 Twinkle=0;             //取反闪烁标志
u8 FallTime=10;           //持续跌倒时间，大概5秒钟
u8 getData=0;             //获取数据标志
u8 SetPhoneNumFlag=0;     //1：设置成功，2设置失败
u8 CancelAlarm = 0;       //取消报警标志
short temperature=0;
u8  hrMin=60, hrMax=120;//心率下限上限
u16 teMin=200,teMax=370;//温度下限上限
u8  spoMin=85;          //血氧下限

#define GPS_STR_LEN 48
GPS_INFO   GPS;  //GPS信息结构体

extern unsigned char rev_start;
extern unsigned char rev_stop;
extern unsigned char gps_flag;
u8 GPS_rx_flag = 0;

#define MAX_BRIGHTNESS 255

uint32_t aun_ir_buffer[150]; //infrared LED sensor data
uint32_t aun_red_buffer[150];  //red LED sensor data
int32_t n_ir_buffer_length; //data length
int32_t n_spo2;  //SPO2 value
int8_t ch_spo2_valid;  //indicator to show if the SPO2 calculation is valid
int32_t n_heart_rate; //heart rate value
int8_t  ch_hr_valid;  //indicator to show if the heart rate calculation is valid
uint8_t uch_dummy;

int32_t hr_buf[16];
int32_t hrSum;
int32_t hrAvg;//心率 
int32_t spo2_buf[16];
int32_t spo2Sum;
int32_t spo2Avg;//血氧浓度
int32_t spo2BuffFilled;
int32_t hrBuffFilled;
int32_t hrValidCnt = 0;
int32_t spo2ValidCnt = 0;
int32_t hrThrowOutSamp = 0;
int32_t spo2ThrowOutSamp = 0;
int32_t spo2Timeout = 0;
int32_t hrTimeout = 0;
uint32_t un_min, un_max,un_prev_data;
uint32_t  un_brightness;  //variables to calculate the on-board LED brightness that reflects the heartbeats

void Init_MAX30102(void)
{
    int32_t i;

    un_brightness = 0;
    un_min = 0x3FFFF;
    un_max = 0;
    
	  bsp_InitI2C();//IIC初始化
	  maxim_max30102_reset(); //resets the MAX30102
    maxim_max30102_read_reg(REG_INTR_STATUS_1, &uch_dummy); //Reads/clears the interrupt status register
    maxim_max30102_init();  //initialize the MAX30102
	
    n_ir_buffer_length = 150; //buffer length of 150 stores 3 seconds of samples running at 50sps

    //read the first 150 samples, and determine the signal range
    for(i = 0; i < n_ir_buffer_length; i++)
    {
        //while(KEY0 == 1); //wait until the interrupt pin asserts
        maxim_max30102_read_fifo((aun_ir_buffer+i), (aun_red_buffer+i));  //新版本 //read from MAX30102 FIFO

        if(un_min > aun_red_buffer[i])
            un_min = aun_red_buffer[i]; //update signal min
        if(un_max < aun_red_buffer[i])
            un_max = aun_red_buffer[i]; //update signal max
    }
    un_prev_data = aun_red_buffer[i - 1];
    //calculate heart rate and SpO2 after first 150 samples (first 3 seconds of samples)
    maxim_heart_rate_and_oxygen_saturation(aun_ir_buffer, n_ir_buffer_length, aun_red_buffer, &n_spo2, &ch_spo2_valid, &n_heart_rate, &ch_hr_valid);
}

void GetHeartRateSpO2(void)
{
	  int32_t i;
	  float f_temp;
	  static u8 COUNT=8;
	
		i = 0;
		un_min = 0x3FFFF;
		un_max = 0;

		//dumping the first 50 sets of samples in the memory and shift the last 100 sets of samples to the top
		for(i = 50; i < 150; i++)
		{
				aun_red_buffer[i - 50] = aun_red_buffer[i];
				aun_ir_buffer[i - 50] = aun_ir_buffer[i];

				//update the signal min and max
				if(un_min > aun_red_buffer[i])
						un_min = aun_red_buffer[i];
				if(un_max < aun_red_buffer[i])
						un_max = aun_red_buffer[i];
		}

		//take 50 sets of samples before calculating the heart rate.
		for(i = 100; i < 150; i++)
		{
				un_prev_data = aun_red_buffer[i - 1];
				maxim_max30102_read_fifo((aun_ir_buffer+i), (aun_red_buffer+i));  //新版本

				//calculate the brightness of the LED
				if(un_max == un_min)
				{
						//flat/no signal: skip brightness update rather than divide by zero
				}
				else if(aun_red_buffer[i] > un_prev_data)
				{
						f_temp = aun_red_buffer[i] - un_prev_data;
						f_temp /= (un_max - un_min);
						f_temp *= MAX_BRIGHTNESS;
						f_temp = un_brightness - f_temp;
						if(f_temp < 0)
								un_brightness = 0;
						else
								un_brightness = (int)f_temp;
				}
				else
				{
						f_temp = un_prev_data - aun_red_buffer[i];
						f_temp /= (un_max - un_min);
						f_temp *= MAX_BRIGHTNESS;
						un_brightness += (int)f_temp;
						if(un_brightness > MAX_BRIGHTNESS)
								un_brightness = MAX_BRIGHTNESS;
				}
		}
		maxim_heart_rate_and_oxygen_saturation(aun_ir_buffer, n_ir_buffer_length, aun_red_buffer, &n_spo2, &ch_spo2_valid, &n_heart_rate, &ch_hr_valid);
		if(COUNT++ > 8)
		{
					COUNT = 0;
					temperature = DS18B20_Get_Temp();//读取温度
					if ((ch_hr_valid == 1) && (n_heart_rate < 150) && (n_heart_rate > 40))
					{
							hrTimeout = 0;
							// Throw out up to 1 out of every 5 valid samples if wacky
							if (hrValidCnt == 4)
							{
									hrThrowOutSamp = 1;
									hrValidCnt = 0;
									for (i = 12; i < 16; i++)
									{
											if (n_heart_rate < hr_buf[i] + 10)
											{
													hrThrowOutSamp = 0;
													hrValidCnt   = 4;
											}
									}
							}
							else
							{
									hrValidCnt = hrValidCnt + 1;
							}

							if (hrThrowOutSamp == 0)
							{

									// Shift New Sample into buffer
									for(i = 0; i < 15; i++)
									{
											hr_buf[i] = hr_buf[i + 1];
									}
									hr_buf[15] = n_heart_rate;

									// Update buffer fill value
									if (hrBuffFilled < 16)
									{
											hrBuffFilled = hrBuffFilled + 1;
									}

									// Take moving average
									hrSum = 0;
									if (hrBuffFilled < 2)
									{
											hrAvg = 0;
									}
									else if (hrBuffFilled < 4)
									{
											for(i = 14; i < 16; i++)
											{
													hrSum = hrSum + hr_buf[i];
											}
											hrAvg = hrSum >> 1;
									}
									else if (hrBuffFilled < 8)
									{
											for(i = 12; i < 16; i++)
											{
													hrSum = hrSum + hr_buf[i];
											}
											hrAvg = hrSum >> 2;
									}
									else if (hrBuffFilled < 16)
									{
											for(i = 8; i < 16; i++)
											{
													hrSum = hrSum + hr_buf[i];
											}
											hrAvg = hrSum >> 3;
									}
									else
									{
											for(i = 0; i < 16; i++)
											{
													hrSum = hrSum + hr_buf[i];
											}
											hrAvg = hrSum >> 4;
									}
							}
							hrThrowOutSamp = 0;
					}
					else
					{
							hrValidCnt = 0;
							if (hrTimeout == 4)
							{
									hrAvg = 0;
									hrBuffFilled = 0;
							}
							else
							{
									hrTimeout++;
							}
					}

					if ((ch_spo2_valid == 1) && (n_spo2 > 75))
					{
							spo2Timeout = 0;

							// Throw out up to 1 out of every 5 valid samples if wacky
							if (spo2ValidCnt == 4)
							{
									spo2ThrowOutSamp = 1;
									spo2ValidCnt = 0;
									for (i = 12; i < 16; i++)
									{
											if (n_spo2 > spo2_buf[i] - 10)
											{
													spo2ThrowOutSamp = 0;
													spo2ValidCnt   = 4;
											}
									}
							}
							else
							{
									spo2ValidCnt = spo2ValidCnt + 1;
							}

							if (spo2ThrowOutSamp == 0)
							{

									// Shift New Sample into buffer
									for(i = 0; i < 15; i++)
									{
											spo2_buf[i] = spo2_buf[i + 1];
									}
									spo2_buf[15] = n_spo2;

									// Update buffer fill value
									if (spo2BuffFilled < 16)
									{
											spo2BuffFilled = spo2BuffFilled + 1;
									}

									// Take moving average
									spo2Sum = 0;
									if (spo2BuffFilled < 2)
									{
											spo2Avg = 0;
									}
									else if (spo2BuffFilled < 4)
									{
											for(i = 14; i < 16; i++)
											{
													spo2Sum = spo2Sum + spo2_buf[i];
											}
											spo2Avg = spo2Sum >> 1;
									}
									else if (spo2BuffFilled < 8)
									{
											for(i = 12; i < 16; i++)
											{
													spo2Sum = spo2Sum + spo2_buf[i];
											}
											spo2Avg = spo2Sum >> 2;
									}
									else if (spo2BuffFilled < 16)
									{
											for(i = 8; i < 16; i++)
									 		{
													spo2Sum = spo2Sum + spo2_buf[i];
											}
											spo2Avg = spo2Sum >> 3;
									}
									else
									{
											for(i = 0; i < 16; i++)
											{
													spo2Sum = spo2Sum + spo2_buf[i];
											}
											spo2Avg = spo2Sum >> 4;
									}
							}
							spo2ThrowOutSamp = 0;
					}
					else
					{
							spo2ValidCnt = 0;
							if (spo2Timeout == 4)
							{
									spo2Avg = 0;
									spo2BuffFilled = 0;
							}
							else
							{
									spo2Timeout++;
							}
					}
		}
}

void DisplayHeartRateSPO2(void)//显示心率血氧函数
{
		if((hrAvg!=0)&&(hrAvg<=hrMin||hrAvg>=hrMax)&&(Twinkle==1))//心率超标，液晶闪烁显示
		{
				OLED_ShowChar(0,2,' ',2,0);
				OLED_ShowChar(8,2,' ',2,0);
				OLED_ShowChar(16,2,' ',2,0);
		}
		else
		{
				//显示相关的信息
				OLED_ShowChar(0,2,hrAvg%1000/100+'0',2,0);
				OLED_ShowChar(8,2,hrAvg%100/10+'0',2,0);
				OLED_ShowChar(16,2,hrAvg%10+'0',2,0);
		}

		if((spo2Avg!=0)&&(spo2Avg<=spoMin)&&(Twinkle==1))//血氧不在范围，液晶闪烁显示
		{
				OLED_ShowChar(48,2,' ',2,0);
				OLED_ShowChar(56,2,' ',2,0);
				OLED_ShowChar(64,2,' ',2,0);
		}
		else
		{
				OLED_ShowChar(48,2,spo2Avg%1000/100+'0',2,0);
				OLED_ShowChar(56,2,spo2Avg%100/10+'0',2,0);
				OLED_ShowChar(64,2,spo2Avg%10+'0',2,0);
		}
}

#define GSM_ATCMD_MAX_RETRY 3//AT指令最多重试次数，避免无限阻塞
u8 gsm_atcmd_send(char *at)//GSM AT指令发送函数，超过GSM_ATCMD_MAX_RETRY次仍未收到OK则放弃
{
    unsigned short waittry;//延时变量
    u8 attempt;//重试次数计数器
    for(attempt = 0; attempt < GSM_ATCMD_MAX_RETRY; attempt++)
    {
        gsm_rev_start = 0;//接收开始标志清零
        gsm_rev_okflag = 0;//接收完成标志清零
        waittry = 0;//延时变量清零
        uart_send(at,0xFF);//串口发送内容
        while(waittry ++ < 3000)//进入while延时
        {
            if (gsm_rev_okflag == 1)//等待GSM返回OK
            {
                return 1;//收到OK，返回成功
            }
            DelayMs(1);
        }
    }
    return 0;//重试次数用尽仍未收到OK，返回失败
}

u8 gsm_init(void)//gsm初始化，返回是否全部AT指令都收到OK
{
    u8 ok = 1;
    ok &= gsm_atcmd_send("AT\r\n");//测试用的
    DelayMs(1000);
    ok &= gsm_atcmd_send("AT+CSCS=\"UCS2\"\r\n");//设置为unicode编码
    DelayMs(1000);
    ok &= gsm_atcmd_send("AT+CMGF=1\r\n");//设置为文本模式
    DelayMs(1000);
    ok &= gsm_atcmd_send("AT+CNMI=2,1\r\n");//来短信时提示，并存储到模块内存
	  DelayMs(1000);
	  ok &= gsm_atcmd_send("AT+CMGD=1,4\r\n");//清除短信
	  DelayMs(1000);
	  ok &= gsm_atcmd_send("AT+CSMP=17,0,2,25\r\n");//设置短信保留为5分钟，发送中文
	  DelayMs(1000);
    return ok;
}

/*
*number 为对方手机号
*/
void gsm_send_msg(const char*number,char * content)
{
    u8 len;
    unsigned char  gsm_at_txbuf[60];//GSM AT命令缓存区
	
    memset(gsm_at_txbuf, 0, 60);//缓存清零
    strncpy((char *)gsm_at_txbuf,"AT+CMGS=\"",9);//将AT+CMGS=\"，复制到gsm_at_txbuf
    memcpy(gsm_at_txbuf + 9, number, 44);//将手机号码复制到AT+CMGS=\"之后
    len = strlen((char *)gsm_at_txbuf);//获取gsm_at_txbuf字符串长度
    gsm_at_txbuf[len] = '"'; // AT+CMGS=\"12345678901\"
    gsm_at_txbuf[len + 1] = '\r';
    gsm_at_txbuf[len + 2] = '\n';//gsm_at_txbuf最终的格式"AT+CMGS=\"手机号码\"\r\n"

    uart_send(gsm_at_txbuf,0xFF);//发送需要接受短信的手机号码
    DelayMs(1000);

    uart_send(content,0xFF);  //发短信内容
    DelayMs(100);

    printf("%c",0x1a);     //发送结束符号
    DelayMs(10);
}

void PhoneNumTranscoding(void)//手机号转码
{
	  u8 i=0;
		for(i=0;i<11;i++)//发送中文短信手机号必须转码，前面需要加上003
		{
				ConversionNum[i*4+0] = '0';
			  ConversionNum[i*4+1] = '0';
			  ConversionNum[i*4+2] = '3';
			  ConversionNum[i*4+3] = PhoneNumber[i];
		}
}

void AddressTranscoding(char *str1,char *str2)//经纬度坐标转码
{
	  u8 i=0,len;
	  char *buf = str1;
	  len = strlen(buf);//获取字符串长度
	
		for(i=0; i < 3; i++)//小数点前3位
		{
				if(buf[i] != ' ')
				{    
            *str2++ = '0';
					  *str2++ = '0';
					  *str2++ = '3';
					  *str2++ = buf[i];
				}
		}
		
		*str2++ = '0';*str2++ = '0';//小数点
		*str2++ = '2';*str2++ = 'E';

		i++;
		
		for(;i < len-1; i++)//小数点后6位
		{
				*str2++ = '0';
				*str2++ = '0';
				*str2++ = '3';
				*str2++ = buf[i];
		}
		*str2 = '\0';
}

void DisplayTemperature(void)//显示温度函数
{
	  temperature=DS18B20_Get_Temp();
	  if((temperature<=teMin||temperature>=teMax)&&(Twinkle==1))
		{
			  OLED_ShowChar(88,2,' ',2,0);
				OLED_ShowChar(96,2,' ',2,0);
				OLED_ShowChar(104,2,' ',2,0);
				OLED_ShowChar(112,2,' ',2,0);
				OLED_ShowChar(120,2,' ',2,0);
		}
		else
		{
				OLED_ShowChar(88,2,temperature/100+'0',2,0);
				OLED_ShowChar(96,2,temperature%100/10+'0',2,0);
				OLED_ShowChar(104,2,'.',2,0);
				OLED_ShowChar(112,2,temperature%10+'0',2,0);
				OLED_ShowChar(120,2,'C',2,0);
		}
}

void DisplayLongitudeAndLatitude(void)//显示经纬度
{
	  char display[12];

	  snprintf(display, sizeof(display),"%10.6f ",GPS.longitude_Degree);
	  OLED_ShowStr(40, 4, (u8*)display, 2);//显示经度

    snprintf(display, sizeof(display),"%10.6f ",GPS.latitude_Degree);
	  OLED_ShowStr(40, 6, (u8*)display, 2);//显示纬度
}

void FallDetection(void)//摔倒检测
{
	  char i;
	  adxl345_read_average(&adx,&ady,&adz,10);//获取数据
		acc=adx;
		if(acc<0)acc=-acc;
    
	
	  if(((u16)acc)>200)
		{
			if(FallFlag==0)
			{
					FallFlag=1;
				  OLED_CLS();//清屏
				
				  OLED_ShowChar(48,2,'F',2,0);//摔倒
					OLED_ShowChar(56,2,'A',2,0);
			    OLED_ShowChar(64,2,'L',2,0);
			    OLED_ShowChar(72,2,'L',2,0);
				
				  OLED_ShowCN(96,2,16,0);
				  DelayMs(1000); 
				  DelayMs(1000); 
				  FallTime=10;
				  InitFlag = 1;
			}
		}
	  if(((u16)acc)<40)
		{
				if(FallFlag==1)
				{
						FallFlag=0;
					  OLED_CLS();//清屏
					
					  OLED_ShowChar(48,2,'S',2,0);//站起来了
					  OLED_ShowChar(56,2,'T',2,0);
			      OLED_ShowChar(64,2,'A',2,0);
			      OLED_ShowChar(72,2,'N',2,0);
			      OLED_ShowChar(80,2,'D',2,0);
					  DelayMs(1000); 
					  if(CancelAlarm==0)
						{
								gsm_send_msg(ConversionNum,"005300740061006E00640020007500700020006E006F0077");//发送短信，老人站起来了
						}
						DelayMs(1000); 
						InitFlag = 1;
				}
		}
}

void DisplaySetValue(void) //显示设置值
{
	  u8 x,i;
		if(setn==1||setn==2)
		{
				OLED_ShowChar(48,4,hrMin/100+'0',2,setn+1-1);//显示
				OLED_ShowChar(56,4,hrMin%100/10+'0',2,setn+1-1);//显示
				OLED_ShowChar(64,4,hrMin%10+'0',2,setn+1-1);//显示
				OLED_ShowChar(48,6,hrMax/100+'0',2,setn+1-2);//显示
				OLED_ShowChar(56,6,hrMax%100/10+'0',2,setn+1-2);//显示
				OLED_ShowChar(64,6,hrMax%10+'0',2,setn+1-2);//显示
		}
		else if(setn==3)
		{
				OLED_ShowChar(48,4,spoMin/100+'0',2,setn+1-3);//显示
				OLED_ShowChar(56,4,spoMin%100/10+'0',2,setn+1-3);//显示
				OLED_ShowChar(64,4,spoMin%10+'0',2,setn+1-3);//显示
		}
		else if(setn==4||setn==5)
		{
				OLED_ShowChar(48,4,teMin/100+'0',2,setn+1-4);//显示
				OLED_ShowChar(56,4,teMin%100/10+'0',2,setn+1-4);//显示
			  OLED_ShowChar(64,4,'.',2,setn+1-4);
				OLED_ShowChar(72,4,teMin%10+'0',2,setn+1-4);//显示
			  OLED_ShowChar(80,4,'C',2,0);

				OLED_ShowChar(48,6,teMax/100+'0',2,setn+1-5);//显示
				OLED_ShowChar(56,6,teMax%100/10+'0',2,setn+1-5);//显示
			  OLED_ShowChar(64,6,'.',2,setn+1-5);
				OLED_ShowChar(72,6,teMax%10+'0',2,setn+1-5);//显示
			  OLED_ShowChar(80,6,'C',2,0);
		}
		else
		{
				x=2;
			  for(i=0;i<11;i++)
				{
						OLED_ShowChar((x++)*8,4,PhoneNumber[i],2,(setn+1)-(6+i));//显示手机号码
				}
		}
}

static void SavePhoneNumber(const char *number)
{
    u16 packed[6] = {0};
    memcpy(packed, number, sizeof(PhoneNumber));
    STMFLASH_Write(FLASH_SAVE_ADDR + 0x40, packed, 6);
}

void KeySettings(void)//按键设置函数
{
	  unsigned char keynum = 0;
	  char i;
	
	  keynum = KEY_Scan(1);//获取按键值
		if(keynum==1)//设置
		{
				setn++;
				if(setn > 16)
				{
					SavePhoneNumber(PhoneNumber);//退出设置前，先把手机号存储一遍
					PhoneNumTranscoding();
					setn=0;
					InitFlag=1;
				}
			  if(setn==1)
				{
					  OLED_CLS();//清屏
					
					  OLED_ShowChar(24,0,'S',2,0);//显示设置
			      OLED_ShowChar(32,0,'E',2,0);
			      OLED_ShowChar(40,0,'T',2,0);
					
					  OLED_ShowChar(56,0,'H',2,0);//心率
			      OLED_ShowChar(64,0,'E',2,0);
			      OLED_ShowChar(72,0,'A',2,0);
			      OLED_ShowChar(80,0,'R',2,0);
			  
					
					  OLED_ShowChar(16,6,'H',2,0); //上限
			      OLED_ShowChar(16,4,'L',2,0); //下限
		
					  OLED_ShowChar(34,4,':',2,0);
						OLED_ShowChar(34,6,':',2,0);
					 
					  
				}
				if(setn==3)
				{
					  OLED_ShowChar(56,0,'S',2,0);//心率
			      OLED_ShowChar(64,0,'P',2,0);
			      OLED_ShowChar(72,0,'O',2,0);
			      OLED_ShowChar(80,0,'2',2,0);

					  for(i=0;i<16;i++)OLED_ShowChar(i*8,6,' ',2,0);
					  
				}
				if(setn==4)
				{
				
					  OLED_ShowChar(56,0,'T',2,0);//体温
			      OLED_ShowChar(64,0,'E',2,0);
			      OLED_ShowChar(72,0,'M',2,0);
			      OLED_ShowChar(80,0,'P',2,0);
					
					  OLED_ShowChar(16,6,'H',2,0); //上限
					  OLED_ShowChar(34,6,':',2,0);
					
				}
				if(setn==6)
				{
					  OLED_CLS();//清屏
					
					  OLED_ShowChar(24,0,'S',2,0);//显示设置
			      OLED_ShowChar(32,0,'E',2,0);
			      OLED_ShowChar(40,0,'T',2,0);
					
					  OLED_ShowChar(56,0,'P',2,0);//手机号
					  OLED_ShowChar(64,0,'H',2,0);
			      OLED_ShowChar(72,0,'O',2,0);
			      OLED_ShowChar(80,0,'N',2,0);
			      OLED_ShowChar(88,0,'E',2,0);
					
					
				}
				DisplaySetValue();
		}
		if(keynum==2)//加
		{
        if((setn==1)&&(hrMax-hrMin>1))hrMin++;
				if((setn==2)&&(hrMax<200))hrMax++; 
			  if((setn==3)&&(spoMin<100))spoMin++;
			  if((setn==4)&&(teMax-teMin>1))teMin++;
				if((setn==5)&&(teMax<999))teMax++; 
			  if(setn>5)
				{
						PhoneNumber[setn-6]++;
					  if(PhoneNumber[setn-6]>'9')PhoneNumber[setn-6]='0';
				}
				DisplaySetValue();
		}
		if(keynum==3)//减
		{
				if((setn==1)&&(hrMin>0))hrMin--;
				if((setn==2)&&(hrMax-hrMin>1))hrMax--; 
			  if((setn==3)&&(spoMin>0))spoMin--;
			  if((setn==4)&&(teMin>0))teMin--;
				if((setn==5)&&(teMax-teMin>1))teMax--; 
			  if(setn>5)
				{
						PhoneNumber[setn-6]--;
					  if(PhoneNumber[setn-6]<'0')PhoneNumber[setn-6]='9';
				}
				DisplaySetValue();
		}
		if(keynum==4)//一键SOS报警键
		{
			 SOS_Flag=1;
		}
		if(keynum==5)//取消报警
		{
			 CancelAlarm = 1;
			 BEEP = 0;
			 alarmFlag &= 0xF7;    //一键SOS报警标志位清除
			 if(FallFlag==1)    //suppress the pending fall alarm/SMS for the current fall event only
			 {
						alarmFlag |= 0x10;
			 }
		}
}

void ShowHomePage(void)//显示主页面
{
		char i;
	  if(InitFlag==1)
		{
				InitFlag = 0;
			  OLED_CLS();//清屏
			  OLED_ShowChar(90,0,'T',2,0);//体温
			  OLED_ShowChar(98,0,'E',2,0);
			  OLED_ShowChar(106,0,'M',2,0);
			  OLED_ShowChar(114,0,'P',2,0);
		
			  OLED_ShowChar(48,0,'S',2,0);//血氧
			  OLED_ShowChar(56,0,'P',2,0);
			  OLED_ShowChar(64,0,'O',2,0);
			  OLED_ShowChar(72,0,'2',2,0);
			
			  OLED_ShowChar(0,0,'H',2,0);//心率
			  OLED_ShowChar(8,0,'E',2,0);
			  OLED_ShowChar(16,0,'A',2,0);
			  OLED_ShowChar(24,0,'R',2,0);
			  OLED_ShowChar(32,0,'T',2,0);
			
			  OLED_ShowChar(0,4,'L',2,0);//显示经度
			  OLED_ShowChar(8,4,'N',2,0);
			  OLED_ShowChar(16,4,'G',2,0);
			  OLED_ShowChar(0,6,'L',2,0);//显示纬度
			  OLED_ShowChar(8,6,'A',2,0);
			  OLED_ShowChar(16,6,'T',2,0);

			  OLED_ShowChar(32,4,':',2,0);
				OLED_ShowChar(32,6,':',2,0);
		
		}
}

void CheckNewMcu(void)  // 检查是否是新的单片机，是的话清空存储区，否则保留
{
	  u16 comper_str[3];
    u16 phone_data[6];
    u16 magic[3];
		
	  STMFLASH_Read(FLASH_SAVE_ADDR + 0x10,comper_str,3); //从0X08010000这个地址读出数据 
	  ((char *)comper_str)[5] = '\0';
	  if(strstr((char *)comper_str,"FDYDZ") == NULL)  //新的单片机
		{
			 memcpy(magic, "FDYDZ", sizeof(magic));
             STMFLASH_Write(FLASH_SAVE_ADDR + 0x10,magic,3); //写入“FDYDZ”，方便下次校验
			 DelayMs(50);
			 SavePhoneNumber("12345678910");//存入初始手机号
			 DelayMs(50);
	  }
		STMFLASH_Read(FLASH_SAVE_ADDR + 0x40,phone_data,6);
        memcpy(PhoneNumber, phone_data, sizeof(PhoneNumber)); //读出手机号
		PhoneNumTranscoding();
		DelayMs(100);
}

void ContentHandle(void)//短信内容处理，发送中文短信必须把内容转化为Unicode码
{
		char TXbuf[400],databuf[50];             //发送数据缓冲区
	  char tempbuf[12]; 
	
		memset(TXbuf,0, 400);   			//清空缓冲区
		memset(databuf,0,50);         //清空缓冲区
	
	  switch(SendFlag)
		{
				case(1):	
								strncpy(TXbuf,"00480065006100720074002100210021",32);break;//心率不在正常范围！
				case(2):	
								strncpy(TXbuf,"00530070006F0032002100210021",28);    break;//血氧不在正常范围！
				case(3):	
								strncpy(TXbuf,"00540065006D0070002100210021",28);    break;//温度不在正常范围！
				case(4):
								strncpy(TXbuf,"00480045004C0050002100210021",28);    break;//老人需要帮助！
				case(5):
								strncpy(TXbuf,"00460061006C006C002100210021",28);    break;//请注意，老人跌倒！
				default:
								break;
		}
	
		strcat(TXbuf,"002000480045004100520054003A");	//当前心率:
		sprintf(databuf,"003%d003%d003%d",hrAvg/100,hrAvg%100/10,hrAvg%10); 
		strcat(TXbuf,databuf);																												//拷贝心率值到TXbuf
	
		strcat(TXbuf,"FF0C00530050004F0032003A");																							//，血氧:
		memset(databuf,0,50);      //清空缓冲区
		sprintf(databuf,"003%d003%d003%d",spo2Avg/100,spo2Avg%100/10,spo2Avg%10);
		strcat(TXbuf,databuf);																												//拷贝血氧值到TXbuf
	
		strcat(TXbuf,"FF0C00540045004D0050003A");																							//，温度:
		memset(databuf,0,50);      //清空缓冲区
		sprintf(databuf,"003%d003%d002E003%d0043",temperature/100,temperature%100/10,temperature%10);
		strcat(TXbuf,databuf);																												//拷贝温度值到TXbuf
	  
		if(GpsInitOkFlag==1)//获取到定位
		{
				strcat(TXbuf,"002E0050006C006100630065003A");			
		}
		else//未获取到定位
		{
				strcat(TXbuf,"002E004C00610073007400200070006C006100630065003A");
		}
		
		strcat(TXbuf,"004C004E0047");																							//经度
		memset(databuf,0,50);      //清空缓冲区
		memset(tempbuf,0,sizeof(tempbuf));      //清空缓冲区
		snprintf(tempbuf, sizeof(tempbuf),"%10.6f ",GPS.longitude_Degree);
		AddressTranscoding(tempbuf,databuf);                                         //将经度转码
		strcat(TXbuf,databuf);	
		
		strcat(TXbuf,"FF0C004C00410054");																							//，纬度
		memset(databuf,0,50);      //清空缓冲区
		memset(tempbuf,0,sizeof(tempbuf));      //清空缓冲区
		snprintf(tempbuf, sizeof(tempbuf),"%10.6f ",GPS.latitude_Degree);
		AddressTranscoding(tempbuf,databuf);                                         //将经度转码
		strcat(TXbuf,databuf);
		
		gsm_send_msg(ConversionNum,TXbuf);//发送短信
		
		SendFlag=0;
}



void AlarmAndSendSMS(void)//蜂鸣器报警及其短信发送
{
		if((hrAvg!=0)&&(hrAvg<=hrMin||hrAvg>=hrMax)&&(!(alarmFlag&0x01)))//心率不在正常范围，蜂鸣器报警发送短信
		{
			  alarmFlag |= 1 << 0;
			  BEEP = 1; //蜂鸣器报警
			  CancelAlarm = 0;
			  SendFlag = 1;
			  ContentHandle();
		}
		else
		{
			  if((hrAvg>hrMin&&hrAvg<hrMax)||hrAvg==0)
				{
						alarmFlag &= 0xFE;
						if((alarmFlag&0x1F)==0)BEEP = 0;
				}
		}
		
		if((spo2Avg!=0)&&(spo2Avg<=spoMin)&&(!(alarmFlag&0x02)))//血氧不在正常范围，蜂鸣器报警发送短信
		{
			  alarmFlag |= 1 << 1;
			  BEEP = 1; //蜂鸣器报警
			  CancelAlarm = 0;
			  SendFlag = 2;
			  ContentHandle();
		}
		else
		{
			  if((spo2Avg>spoMin)||spo2Avg==0)
				{
						alarmFlag &= 0xFD;
						if((alarmFlag&0x1F)==0)BEEP = 0;
				}
		}
		
		if((temperature<=teMin||temperature>=teMax)&&(!(alarmFlag&0x04)))//温度不在正常范围，蜂鸣器报警发送短信
		{
			  alarmFlag |= 1 << 2;
			  BEEP = 1; //蜂鸣器报警
			  CancelAlarm = 0;
			  SendFlag = 3;
			  ContentHandle();
		}
		else
		{
			  if(temperature>teMin&&temperature<teMax)
				{
						alarmFlag &= 0xFB;
						if((alarmFlag&0x1F)==0)BEEP = 0;
				}
		}
		
		if(SOS_Flag==1&&(!(alarmFlag&0x08)))//SOS报警发短信
		{
				SOS_Flag = 0;
			  alarmFlag |= 1 << 3;
			  BEEP = 1; //蜂鸣器报警
			  CancelAlarm = 0;
			  SendFlag = 4;
			  ContentHandle();
		}
		
		if(FallFlag==1&&(!(alarmFlag&0x10))&&FallTime==0)//检测到跌倒已经持续5秒钟，蜂鸣器报警发送短信
		{
				alarmFlag |= 1 << 4;
			  BEEP = 1; //蜂鸣器报警
			  CancelAlarm = 0;
			  SendFlag = 5;
			  ContentHandle();
		}
		else
		{
				if(FallFlag==0)
				{
					  alarmFlag &= 0xEF;
						if((alarmFlag&0x1F)==0)BEEP = 0;
				}
		}
		
		if(getData==1)          //接收到获取数据指令，发短信
		{
				getData=0;
			  ContentHandle();
		}
		
		if(SetPhoneNumFlag==1)
		{
				SetPhoneNumFlag = 0;
			  gsm_send_msg(ConversionNum,"00500068006F006E00650020006E0075006D00620065007200200073006500740020007300750063006300650073007300660075006C006C00790021");//发送短信，手机号码设置成功！
		}
		if(SetPhoneNumFlag==2)
		{
				SetPhoneNumFlag = 0;
			  gsm_send_msg(ConversionNum,"00500068006F006E00650020006E0075006D0062006500720020007300650074007500700020006600610069006C00650064002E00200050006C006500610073006500200063006800650063006B00200074006800650020006E0075006D00620065007200200061006E0064002000740072007900200061006700610069006E002E");//发送短信，手机号码设置失败！
		}
}

void SMS_Receive(void)//短信接收
{
	  u8 len,i=0,k;
	  char  *presult1=0,*presult2=0;
	  char  *str1=0,*str2=0;
	  char  tempbuf[100],tempNum[11];
	  char  gsm_at_txbuf1[20];
	  char  SmsNum[3];
    static char rxbuf[STM32_RX1BUFF_SIZE];
    u32 saved_primask;

    saved_primask = __get_PRIMASK();
    __disable_irq();
    memcpy(rxbuf, STM32_RX1_BUF, sizeof(rxbuf));
    __set_PRIMASK(saved_primask);
    rxbuf[sizeof(rxbuf) - 1] = '\0';

  	if(strstr(rxbuf,"83B753D66570636E")!=NULL)//接收到获取数据命令
		{
			  if(CancelAlarm==1 || alarmFlag==0x00)//在取消报警的状态下，提示滴声
				{
						BEEP = 1;
						DelayMs(200);
						BEEP = 0;
				}
			
			  memset(STM32_RX1_BUF, 0, STM32_RX1BUFF_SIZE);//清除缓存
				STM32_Rx1Counter = 0;
                rxbuf[0] = '\0';
			
        getData=1;
		}
		
		if(strstr(rxbuf,"8BBE7F6E624B673A53F77801")!=NULL)//接收到设置手机号码命令
		{
			  if(CancelAlarm==1 || alarmFlag==0x00)//在取消报警的状态下，提示滴声
				{
						BEEP = 1;
						DelayMs(200);
						BEEP = 0;
				}
				str1 = strstr(rxbuf,"8BBE7F6E624B673A53F77801");
				DelayMs(20);
				str2 = str1 + 24;           //把”设置手机号码“这几个字符截去掉
          
				while(str2 < rxbuf + sizeof(rxbuf) - 1 && *str2 != '\0' && *str2 != '\r')        //判断有没有接收到回车符号，如果接收到说明号码已经接收完全
				{
						tempbuf[i] = *str2;
					  i++;str2++;
					  if(i>44)break;            //超出手机号长度范围，直接退出while循环
				}
        tempbuf[i] = '\0';            //加上结尾符
				
				if(strlen(tempbuf) != 44 || *str2 != '\r')     //转码的手机号码长度必须是44,不然都是设置失败
				{
						SetPhoneNumFlag=2;        //设置失败标志
				}
				else
				{
					  memset(tempNum,0,11);     //清除缓存
						for(i=0; i < 11; i++)
						{
							  if((tempbuf[i*4]=='0')&&(tempbuf[i*4+1]=='0')&&(tempbuf[i*4+2]=='3'))
								{
										tempNum[i] = tempbuf[i*4+3];   //提取出11位手机号码
								}
								else {
									  SetPhoneNumFlag=2;//设置失败标志
										break;
								}
						}
						if(i==11 && SetPhoneNumFlag!=2)
						{
								for(k=0; k < 11; k++)PhoneNumber[k] = tempNum[k];           //设置新的手机号
							  SavePhoneNumber(PhoneNumber);//把手机号存储一遍
								PhoneNumTranscoding();
							  SetPhoneNumFlag=1;//设置成功标志
						}
				}
			  memset(STM32_RX1_BUF, 0, STM32_RX1BUFF_SIZE);//清除缓存
				STM32_Rx1Counter = 0;
                rxbuf[0] = '\0';
		}
		
	  if(strstr(rxbuf,"+CMTI:")!=NULL)        //接收到短信
		{
			  presult1 = strstr(rxbuf,"+CMTI:");
			  if(strstr(presult1,"\"SM\",") != NULL &&
                   strlen(strstr(presult1,"\"SM\",") + 5) >= 2) 
				{				
					  presult2 = strstr(presult1,"\"SM\",");	// +CMTI: "SM",1
					  DelayMs(50);	
					  memset(gsm_at_txbuf1, 0, 20);//清空发送缓存区
					  memset(SmsNum, 0, 3);//清空缓存区
						strncpy(gsm_at_txbuf1,"AT+CMGR=",8);//将AT+CMGR="，复制到gsm_at_txbuf
					  memcpy(SmsNum,presult2 + 5,2);
						memcpy(gsm_at_txbuf1 + 8, SmsNum, 2);
						len = strlen(gsm_at_txbuf1);//获取gsm_at_txbuf字符串长度
						gsm_at_txbuf1[len] = '\r';
						gsm_at_txbuf1[len + 1] = '\n';//gsm_at_txbuf最终的格式"AT+CMGR=XXX\r\n"
						uart_send(gsm_at_txbuf1,0xFF);
				
					  memset(STM32_RX1_BUF, 0, STM32_RX1BUFF_SIZE);//清除缓存
						STM32_Rx1Counter = 0;
                rxbuf[0] = '\0';
				}
		}
}


int main(void)
{
	char i, error_num = 0;
	extern const unsigned char BMP1[];
	u8 shanshuo=0,count=0;
	u8 count2=0,count3=0;
	
	DelayInit();
	NVIC_PriorityGroupConfig(NVIC_PriorityGroup_2);	//设置NVIC中断分组2:2位抢占优先级，2位响应优先级
	I2C_Configuration(); //IIC初始化
	CheckNewMcu();//检测是否为新的单片机
	OLED_Init(); //OLED初始化
	KEY_Init(); //按键初始化
	GPS_rx_flag = 0;
	Usart1_Init(9600);
	USART3_Init(9600);
	DelayMs(200);
  OLED_CLS();//清屏
	DS18B20_Init();
	OLED_DrawBMP(40,0,88,6,(unsigned char *)BMP1);//测试BMP位图显示
	gsm_init();//gsm初始化
	IIC_init();//IIC初始化
	adxl345_init();//ADXL345初始化
	Init_MAX30102();//MAX30102初始化
	memset(STM32_RX1_BUF, 0, STM32_RX1BUFF_SIZE);//清除缓存
	STM32_Rx1Counter = 0;
	GPS_rx_flag = 1;
 
	while(1)
	{
		  SMS_Receive();//短信接收
		  KeySettings();
		  ShowHomePage();
		  if(setn == 0)//不在设置状态下，读取相关数据
			{
				  if (rev_stop == 1 && count3++>=5)   //如果接收完一行
					{
							if (GPS_RMC_Parse(STM32_RX3_BUF, &GPS)) //解析GPRMC
							{
									DisplayLongitudeAndLatitude();	  //显示经纬度信息
									error_num = 0;
									gps_flag = 0;
									rev_stop  = 0;
									GpsInitOkFlag=1;
							}
							else
							{
									if (error_num++ >= 30) //如果数据无效超过30次
									{
											error_num = 30;
											if(GpsInitOkFlag==1)
											{
													GpsInitOkFlag = 0;
													OLED_ShowStr(40, 4, "           ", 2);
													OLED_ShowStr(40, 6, "           ", 2);
											}
									}
									gps_flag = 0;
									rev_stop  = 0;
							}
							count3=0;
					}
					if(GpsInitOkFlag==0&&count++>=5)//无GPS信号，显示搜索信号
					{
							count = 0;
							shanshuo = !shanshuo;
							if(shanshuo==1)
                {
									OLED_ShowStr(40, 4, "    ...    ", 2);
								  OLED_ShowStr(40, 6, "    ...    ", 2);
								}
							else           {        OLED_ShowStr(40, 4, "           ", 2);OLED_ShowStr(40, 6, "           ", 2);}
					}
					DisplayTemperature();     //显示温度
					FallDetection();          //跌倒检测
					GetHeartRateSpO2();       //获取心率血氧
					DisplayHeartRateSPO2();   //显示心率血氧
			}
			AlarmAndSendSMS();           //蜂鸣器报警及其发送短信
			if(count2++>2)
			{
					Twinkle=!Twinkle;
				  if(FallFlag==1)
					{
							if(FallTime>0)FallTime--; //当时间减到0，说明跌倒时间持续了5秒（这里只是大概5秒）
					}
				  count2 = 0;
			}
	}
}
