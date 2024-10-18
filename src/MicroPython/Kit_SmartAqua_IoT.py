# ******************************************************************************************
# FileName     : Kit_SmartAqua_IoT.py
# Description  : 이티보드 스마트 어항 코딩 키트(IoT)
# Author       : 손철수
# Created Date : 2024.09.19 : PEJ 
# Reference    :
# ******************************************************************************************
board_firmware_verion = 'smartAqu_0.91';


#===========================================================================================
# 기본 모듈 사용하기
#===========================================================================================
import time
from machine import Pin, ADC
from ETboard.lib.pin_define import *                     # ETboard 핀 관련 모듈
from ETboard.lib.servo import Servo                      # 서보 모터 제어 라이브러리

#===========================================================================================
# IoT 프로그램 사용하기
#===========================================================================================
from ET_IoT_App import ET_IoT_App, setup, loop
app = ET_IoT_App()


#===========================================================================================
# oled 표시 장치 사용하기
#===========================================================================================
from ETboard.lib.OLED_U8G2 import *
oled = oled_u8g2()


#===========================================================================================
# 수온 센서 사용하기
#===========================================================================================
from ds18x20 import DS18X20
from onewire import OneWire
ds_pin = Pin(A3)                                         # 수온 센서 핀 : A3
ds_sensor = DS18X20(OneWire(ds_pin))                     # 수온 센서 통신 설정


#===========================================================================================
# 전역 변수 선언
#===========================================================================================
mode_button = Pin(D7)                                    # 모드 변경 버튼 : 파랑
motor_button = Pin(D9)                                   # 서보 모터 작동 버튼 : 노랑

tds_pin = ADC(Pin(A4))                                   # 수질 센서 핀 : A4
level_pin = Pin(D5)                                      # 수위 센서 핀 : D5
servo_pin = Servo(Pin(D8))                               # 서보 모터 핀 : D8

operation_mode_led = Pin(D2)                             # 작동 모드 LED : 빨강

roms = 0                                                 # 수온 센서 주소 값

temp = 0                                                 # 온도
tds = 0                                                  # 수질
level = 'shortage'                                       # 수위
motor_state = 'off'                                      # 모터 상태

timer = 1 * 60  * 120                                    # 먹이 공급 타이머의 시간
now = 0                                                  # 현재 시간
last_feeding = 0                                         # 마지막 먹이 공급 시간
time_remaining = ''                                      # 남은 타이머 시간

step = 'step 0'                                          # 스텝


#===========================================================================================
def et_setup():                                          #  사용자 맞춤형 설정
#===========================================================================================
    global roms

    mode_button.init(Pin.IN)                             # 모드 변경 버튼 : 입력 모드
    motor_button.init(Pin.IN)                            # 모터 제어 버튼 : 입력 모드

    roms = ds_sensor.scan()                              # 수온 센서 스캔
    print('Found DS devices: ', roms)                    # 수온 센서 출력

    tds_pin.atten(ADC.ATTN_11DB)                         # 수질 센서 : 입력 모드

    level_pin.init(Pin.IN, Pin.PULL_UP)                  # 수위 센서 : 입력 모드

    servo_pin.write_angle(90)                            # 서보모터 작동 확인

    app.operation_mode = 'automatic';                    # 작동 모드: 자동
    app.send_data('motor', 'state', motor_state);        # 모터 작동 상태 응답
    app.send_data('operation_mode', 'mode', app.operation_mode);   # 작동 모드    

    recv_message()                                       # 메시지 수신


#===========================================================================================
def et_loop():                                           # 사용자 반복 처리
#===========================================================================================
    do_sensing_proces()                                  # 센싱 처리
    do_automatic_process()                               # 자동화 처리


#===========================================================================================
def do_sensing_proces():                                 # 센싱 처리
#===========================================================================================
    mode_set()                                           # 모드 설정
    temp_get()                                           # 수온 측정
    tds_get()                                            # 수질 측정
    level_get()                                          # 수위 측정

    if motor_button.value() == LOW:                      # 먹이 공급 버튼이 눌렸다면
        food_supply()                                    # 먹이 공급


#===========================================================================================
def mode_set():                                          # 모드 설정
#===========================================================================================
    global now, step

    step = 'step 1'
    display_information()

    now = int(round(time.time()))                        # 현재 시간 저장

    if mode_button.value() != LOW:                       # 모드 변경 버튼이 눌리지 않았다면
        return

    if app.operation_mode == 'automatic':                # 모드가 자동 모드라면
        app.operation_mode = 'manual'                    # 수동 모드로 변경
    else:
        app.operation_mode = 'automatic'                 # 자동 모드로 변경

    app.send_data('operation_mode', 'mode', app.operation_mode);   # 작동 모드 


#===========================================================================================
def temp_get():                                          # 수온 측정
#===========================================================================================
    global roms, temp, step

    step = 'step 2'
    display_information()

    if len(roms) <= 0:                                   # 수온 센서 예외 처리
        temp = -1
        print('수온 감지 센서 오류')
        return

    ds_sensor.convert_temp()                             # 수온 측정
    time.sleep_ms(5)

    temp = ds_sensor.read_temp(roms[0])                  # 수온 저장


#===========================================================================================
def tds_get():                                           # 수질 측정
#===========================================================================================
    global tds, step

    step = 'step 3'
    display_information()

    tds_value = tds_pin.read()                           # 수질 측정
    if tds_value <= 0:                                   # 수질 센서 예외 처리
        tds = -1
        print('수질 감지 센서 오류')
        return

    voltage = tds_value * 5 / 4096.0
    compensationVolatge = voltage * (1.0 + 0.02 * (temp - 25.0))
    tds = (133.42/compensationVolatge * compensationVolatge * compensationVolatge - 255.86 \
           * compensationVolatge * compensationVolatge + 857.39 * compensationVolatge) * 0.5


#===========================================================================================
def level_get():                                         # 수위 측정
#===========================================================================================
    global level, step

    step = 'step 4'
    display_information()

    if level_pin.value() == HIGH:                        # 수위 센서의 값이 HIGH라면
        level = 'enough'                                 # 수위: enough
    else:                                                # 수위 센서의 값이 LOW라면
        level = 'shortage'                               # 수위: shortage


#===========================================================================================
def food_supply():                                       # 먹이 공급
#===========================================================================================
    global last_feeding, now, step

    step = 'step 5'
    display_information()

    motor_control()                                      # 모터 제어

    last_feeding = now                                   # 마지막 먹이 공급 시간 업데이트


#===========================================================================================
def motor_control():                                     # 모터 제어
#===========================================================================================
    motor_on()                                           # 모터 작동
    time.sleep(1)

    motor_off()                                          # 모터 중지


#===========================================================================================
def motor_on():                                          # 모터 작동
#===========================================================================================
    global motor_state, step

    step = 'step 5-1'

    motor_state = 'on'                                   # 모터 상태 변경
    display_information()                                # oled 표시
    app.send_data('motor', 'state', motor_state);        # 모터 작동 상태 응답

    servo_pin.write_angle(180)                           # 먹이 공급


#===========================================================================================
def motor_off():                                         # 모터 중지
#===========================================================================================
    global motor_state, step

    step = 'step 5-2'

    motor_state = 'off'                                  # 모터 상태 변경
    display_information()                                # oled 표시
    app.send_data('motor', 'state', motor_state);        # 모터 작동 상태 응답
    servo_pin.write_angle(90)                            # 모터 중지


#===========================================================================================
def do_automatic_process():                              # 자동화 처리
#===========================================================================================
    if (app.operation_mode != 'automatic'):              # 작동 모드가 automatic일 경우만
        return

    global timer, now, last_feeding
    if now - last_feeding < timer:                       # 타이머가 완료되지 않았다면
        return

    food_supply()                                        # 먹이 공급


#===========================================================================================
def et_short_periodic_process():                         # 사용자 주기적 처리 (예 : 1초마다)
#===========================================================================================
    display_information()                                # 표시 처리


#===========================================================================================
def time_remaining_calculate():                          # 남은 타이머 시간 계산
#===========================================================================================
    global last_feeding, now, time_remaining

    cal_time = now - last_feeding
    minute, sec = divmod(timer - cal_time, 60)
    hour, minute = divmod(minute, 60)

    time_remaining = '{:0>2}'.format(hour) + ':' + '{:0>2}'.format(minute) + ':' + \
                     '{:0>2}'.format(sec)


#===========================================================================================
def display_information():                               # oled 표시
#===========================================================================================
    global board_firmware_verion, temp, tds, level, motor_state, time_remaining, step
    string_temp = '%3d' % temp                           # 수온 문자열 변환
    string_tds = '%3d' % tds                             # 수질 문자열 변환

    oled.clear()                                         # oled 초기화
    oled.setLine(1, board_firmware_verion)               # 1번째 줄에 펌웨어 버전
    oled.setLine(2, step)                                # 2번째 줄에 스텝
    oled.setLine(3, 'mode: ' + app.operation_mode)       # 3번째 줄에 모드
    oled.setLine(4, 'temp: ' + string_temp)              # 4번째 줄에 수온
    oled.setLine(5, 'tds: ' + string_tds)                # 5번쩨 줄에 수질
    oled.setLine(6, 'level: ' + level)                   # 6번쩨 줄에 수위
    oled.setLine(7, 'motor: ' + motor_state)             # 7번쩨 줄에 모터 상태

    if app.operation_mode == 'automatic':                # 자동 모드라면
        time_remaining_calculate()
        oled.setLine(8, 'timer: ' + time_remaining)      # 8번쩨 줄에 타이머

    oled.display()
    

#===========================================================================================
def et_long_periodic_process():                          # 사용자 주기적 처리 (예 : 5초마다)
#===========================================================================================
    send_message()                                       # 메시지 송신


#===========================================================================================
def send_message():                                      # 메시지 송신
#===========================================================================================
    global temp, tds, level, time_remaining
    app.add_sensor_data('temp', temp);                   # 센서 데이터 추가
    app.add_sensor_data('tds', tds);                     # 센서 데이터 추가
    app.add_sensor_data('level', level);                 # 센서 데이터 추가
    app.send_sensor_data();                              # 센서 데이터 송신

    if app.operation_mode == 'automatic':                # 자동 모드라면
        time_remaining_calculate()
        app.send_data('timer', 'time_remaining', time_remaining)  # 타이머 남은 시간 송신


#===========================================================================================
def recv_message():                                      # 메시지 수신
#===========================================================================================
    # 'operation_mode' 메시지를 받으면 process_operation_mode() 실행
    app.setup_recv_message('operation_mode', process_operation_mode)

    # 'feeder' 메시지를 받으면 process_feeder_control() 실행
    app.setup_recv_message('feeder', process_feeder_control)


#===========================================================================================
def process_operation_mode(topic, msg):                  # 작동 모드 처리
#===========================================================================================
    operation_mode_led.init(Pin.OUT)                     # 작동 모드 LED: 출력 모드

    if msg == 'automatic':                               # 작동 모드: 자동으로
        app.operation_mode = 'automatic'
        operation_mode_led.value(1)                      # LED 켜기
        print('작동모드: automatic, 빨강 LED on')
    else:                                                # 작동 모드: 수동으로
        app.operation_mode = 'manual'
        operation_mode_led.value(0)                      # LED 끄기
        print('작동모드: manual, 빨강 LED off')


#===========================================================================================
def process_feeder_control(topic, msg):                  # 모터 제어 처리
#===========================================================================================
    # 자동 모드인 경우에는 모터를 원격에서 제어를 할 수 없음
    if (app.operation_mode == 'automatic'):
        app.send_data('operation_mode', 'mode', app.operation_mode);   # 작동 모드
        return

    global motor_state, timer, now, last_feeding
    if msg == 'action':                                  # 메시지가 'on'이라면
        food_supply()                                    # 먹이 공급


#===========================================================================================
# 시작 지점                     
#===========================================================================================
if __name__ == '__main__':
    setup(app, et_setup)
    while True:
        loop(app, et_loop, et_short_periodic_process, et_long_periodic_process)


#===========================================================================================
#                                                    
# (주)한국공학기술연구원 http://et.ketri.re.kr       
#
#===========================================================================================