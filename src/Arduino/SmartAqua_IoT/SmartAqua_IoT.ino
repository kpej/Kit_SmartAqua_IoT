/******************************************************************************************
 * FileName     : SmartAqua_IoT.ino
 * Description  : 이티보드 스마트 어항 코딩 키트(IoT)
 * Author       : PEJ
 * Created Date : 2022.09.30
 * Reference    : 
******************************************************************************************/
const char* board_firmware_verion = "smartAqu_0.91";


//==========================================================================================
// IoT 프로그램 사용하기
//==========================================================================================
#include "ET_IoT_App.h"
ET_IoT_App app;


//==========================================================================================
// 수온 센서 사용하기
//==========================================================================================
#include <OneWire.h>
#include <DallasTemperature.h>
const int ds_pin  = A3;                                  // 수온 센서 핀 : A3

OneWire oneWire(ds_pin);                                 // OneWire 객체 생성
DallasTemperature ds_sensor(&oneWire);


//==========================================================================================
// 서보 모터 사용하기
//==========================================================================================.
#include <Servo.h>
Servo servo;                                             // 서보 모터 객체 생성
const int servo_pin = D8;                                // 서보 모터 핀 : D8


//==========================================================================================
// 전역 변수 선언
//==========================================================================================
const int mode_button = D7;                              // 모드 변경 버튼 : D7(파랑)
const int motor_button = D9;                             // 먹이 공급 버튼 : D9(노랑)

const int tds_pin  = A4;                                 // 수질 센서 핀 : A3
const int level_pin = D5;                                // 수위 센서 핀 : D5

int operation_mode_led = D2;                             // 작동 모드 LED 핀: D2(빨강)

DeviceAddress roms;                                      // 수온 센서 주소 값

float temp = 0;                                          // 온도
float tds = 0;                                           // 수질
String level = "shortage";                               // 수위
String motor_state = "off";                              // 모터 상태

unsigned long timer = 1 * 60  * 120  * 1000UL;           // 먹이 공급 타이머의 시간
unsigned long now = 0;                                   // 현재 시간
unsigned long last_feeding = 0;                          // 마지막 먹이 공급 시간
String time_remaining = "00:00:00";                      // 남은 타이머 시간

String step = "step 0";                                  // 스텝


//==========================================================================================
void et_setup()                                          // 사용자 맞춤형 설정
//==========================================================================================
{
  pinMode(mode_button, INPUT);                           // 모드 변경 버튼: 입력 모드
  pinMode(motor_button, INPUT);                          // 모터 제어 버튼: 입력 모드

  pinMode(level_pin, INPUT_PULLUP);                      // 수위 센서: 입력 풀업 모드

  ds_sensor.begin();                                     // 온도 센서 초기화

  servo.attach(servo_pin);                               // 서보모터 핀 지정
  servo.write(90);                                       // 서보모터 작동 감지

  app.operation_mode = "automatic";                      // 작동 모드: 자동
  app.send_data("motor", "state", motor_state);          // 모터 상태 응답
  app.send_data("operation_mode", "mode", app.operation_mode);   // 작동 모드
}


//==========================================================================================
void et_loop()                                           // 사용자 반복 처리
//==========================================================================================
{
  do_sensing_process();                                  // 센싱 처리

  do_automatic_process();                                // 자동화 처리
}


//==========================================================================================
void do_sensing_process()                                // 센싱 처리
//==========================================================================================
{
  mode_set();                                            // 모드 설정
  temp_get();                                            // 수온 측정
  tds_get();                                             // 수질 측정
  level_get();                                           // 수위 측정

  if (digitalRead(motor_button) == LOW) {                // 먹이 공급 버튼이 눌렸다면
    food_supply();                                       // 먹이 공급
  }
}


//==========================================================================================
void mode_set()                                          // 모드 설정
//==========================================================================================
{
  step = "step 1";
  display_information();

  now = millis();                                        // 현재 시간 저장

  if (digitalRead(mode_button) != LOW) {                 // 모드 변경 버튼이 눌리지 않았다면
    return;
  }

  if (app.operation_mode == "automatic") {               // 모드가 자동 모드라면
    app.operation_mode = "manual";                       // 수동 모드로 변경
  } else {
    app.operation_mode = "automatic";                    // 자동 모드로 변경
  }

  app.send_data("operation_mode", "mode", app.operation_mode);   // 작동 모드 응답
}


//==========================================================================================
void temp_get()                                          // 수온 측정
//==========================================================================================
{
  step = "step 2";
  display_information();

  if (!ds_sensor.getAddress(roms, 0)) {                  // 수온 센서 예외 처리
    temp = -1;
    Serial.println("수온 감지 센서 오류");
    return;
  }

  ds_sensor.requestTemperatures();                       // 수온 측정
  delay(5);

  temp = ds_sensor.getTempC(roms);                       // 수온 저장
}


//==========================================================================================
void tds_get()                                           // 수온 측정
//==========================================================================================
{
  step = "step 3";
  display_information();

  int tds_value = analogRead(tds_pin);                   // 수질 측정
  if (tds_value < 0) {                                   // 수질 센서 예외 처리
    tds = -1;
    Serial.println("수질 감지 센서 오류");
    return;
  }

  float voltage = tds_value * 5.0 / 1023.0;
  float compensationVoltage = voltage * (1.0 + 0.02 * (temp - 25.0));
  tds = (133.42 / compensationVoltage * compensationVoltage * compensationVoltage - 255.86
        * compensationVoltage * compensationVoltage + 857.39 * compensationVoltage) * 0.5;
}


//==========================================================================================
void level_get()                                         // 수위 측정
//==========================================================================================
{
  step = "step 4";
  display_information();

  if (digitalRead(level_pin) == HIGH) {                  // 수위 센서의 값이 HIGH라면
    level = "enough";                                    // 수위: enough
  } else {                                               // 수위 센서의 값이 LOW라면
    level = "shortage";                                  // 수위: shortage
  }
}


//==========================================================================================
void food_supply()                                       // 먹이 공급
//==========================================================================================
{
  step = "step 5";
  display_information();

  motor_control();                                       // 모터 제어

  last_feeding = now;                                    // 마지막 먹이 공급 시간 업데이트
}


//==========================================================================================
void motor_control()                                     // 모터 제어
//==========================================================================================
{
  motor_on();                                            // 모터 작동
  delay(1000);

  motor_off();                                           // 모터 중지
}


//==========================================================================================
void motor_on()                                          // 모터 작동
//==========================================================================================
{
  step = "step 5-1";

  motor_state = "on";                                    // 모터 상태 변경
  display_information();                                 // OLED 표시
  app.send_data("motor", "state", motor_state);          // 모터 상태 응답

  servo.write(180);                                      // 모터 작동
}


//==========================================================================================
void motor_off()                                         // 모터 중지
//==========================================================================================
{
  step = "step 5-2";

  motor_state = "off";                                   // 모터 상태 변경
  display_information();                                 // OLED 표시
  app.send_data("motor", "state", motor_state);          // 모터 상태 응답

  servo.write(90);                                       // 모터 중지
}


//==========================================================================================
void do_automatic_process()                              // 자동화 처리
//==========================================================================================
{
  if(app.operation_mode != "automatic")                  // 작동 모드가 automatic 일 경우만
    return;

  if(now - last_feeding < timer) {                       // 타이머가 완료되지 않았다면
    return;
  }

  food_supply();                                         // 먹이 공급
}


//==========================================================================================
void et_short_periodic_process()                         // 사용자 주기적 처리 (예 : 1초마다)
//==========================================================================================
{
  display_information();                                 // 표시 처리
}


//==========================================================================================
void time_remaining_calculate()                          // 남은 시간 계산
//==========================================================================================
{
  unsigned long time_cal = now - last_feeding;
  unsigned long timer_cal = timer - time_cal;

  int hour = timer_cal / (60 * 60 * 1000);
  timer_cal = timer_cal % (60 * 60 * 1000);

  int minute = timer_cal / (60 * 1000);
  timer_cal = timer_cal % (60 * 1000);

  int second = timer_cal / 1000;

  time_remaining = String(hour) + ":" + String(minute) + ":" + String(second);
}


//==========================================================================================
void display_information()                               // OLED 표시
//==========================================================================================
{
  String string_temp = String(temp);                     // 수온 값을 문자열로 변환
  String string_tds = String(tds);                       // 수질 값을 문자열로 변환

  app.oled.setLine(1, board_firmware_verion);            // 1번째 줄에 펌웨어 버전
  app.oled.setLine(2, step);                             // 2번째 줄에 스텝
  app.oled.setLine(3, "mode: " + app.operation_mode);    // 3번째 줄에 모드
  app.oled.setLine(4, "temp: " + string_temp);           // 4번째 줄에 수온
  app.oled.setLine(5, "tds : " + string_tds);            // 5번째 줄에 수질
  app.oled.setLine(6, "level : " + level);               // 6번째 줄에 수위
  app.oled.setLine(7, "motor : " + motor_state);         // 7번째 줄에 모터 상태

  if (app.operation_mode == "automatic") {
    time_remaining_calculate();
    app.oled.setLine(8, "timer : " + time_remaining);    // 8번째 줄에 모터 상태
  }
  app.oled.display(8);                                   // OLED에 표시
}


//==========================================================================================
void et_long_periodic_process()                          // 사용자 주기적 처리 (예 : 5초마다)
//==========================================================================================
{
  send_message();                                        // 메시지 송신
}


//==========================================================================================
void send_message()                                      // 메시지 송신
//==========================================================================================
{
  app.add_sensor_data("temp", temp);                     // 센서 데이터 추가
  app.add_sensor_data("tds", tds);                       // 센서 데이터 추가
  app.add_sensor_data("level", level);                   // 센서 데이터 추가
  app.send_sensor_data();                                // 센서 데이터 송신

  if (app.operation_mode == "automatic") {               // 자동 모드라면
    time_remaining_calculate();
    app.send_data("timer", "time_remaining", time_remaining);  // 타이머 남은 시간 송신
  }
}


//==========================================================================================
void recv_message()                                      // 메시지 수신
//==========================================================================================
{
  // "operation_mode" 메시지를 받으면 process_operation_mode() 실행
  app.setup_recv_message("operation_mode", process_operation_mode);

  // "feeder" 메시지를 받으면 process_feeder_control() 실행
  app.setup_recv_message("feeder", process_feeder_control);
}


//==========================================================================================
void process_operation_mode(const String &msg)           // 작동 모드 처리
//==========================================================================================
{
  pinMode(operation_mode_led, OUTPUT);                   // 작동 모드 LED: 출력 모드

  if (msg == "automatic") {                              // 작동 모드: 자동
    app.operation_mode = "automatic";
    digitalWrite(operation_mode_led, HIGH);
    Serial.println("작동 모드: automatic, 초록 LED on");
  } else {                                               // 작동 모드: 수동
    app.operation_mode = "manual";
    digitalWrite(operation_mode_led, LOW);
    Serial.println("작동 모드: manual, 초록 LED off");
  }
}


//==========================================================================================
void process_feeder_control(const String &msg)            // 모터 제어 처리
//==========================================================================================
{
  // 자동 모드인 경우에는 모터를 원격에서 제어를 할 수 없음
  if (app.operation_mode == "automatic")
    return;

  // 수동 모드인 경우이면서
  if (msg == "action") {                                      // 메시지가 'on'이라면
    food_supply();                                            // 먹이 공급
  }
}


//==========================================================================================
//
// (주)한국공학기술연구원 http://et.ketri.re.kr
//
//==========================================================================================