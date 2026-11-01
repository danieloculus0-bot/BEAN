// BEAN Nano motion bridge v1: Jetson USB serial to PCA9685 at 50 Hz.
// Requires Adafruit PWM Servo Driver Library.
// ACK means the PWM target was written, NOT that the joint reached target.
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <stdlib.h>
#include <string.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);
char frame[64];
uint8_t used = 0;

bool parseNumber(const char* text, unsigned long* out) {
  if (!text || !*text) return false;
  for (const char* p = text; *p; ++p) if (*p < '0' || *p > '9') return false;
  char* end = NULL;
  unsigned long n = strtoul(text, &end, 10);
  if (!end || *end) return false;
  *out = n;
  return true;
}

void error(unsigned long sequence, const char* code) {
  Serial.print(F("ERR,"));
  Serial.print(sequence);
  Serial.print(',');
  Serial.println(code);
}

void process(char* input) {
  if (strcmp(input, "HELLO") == 0) {
    Serial.println(F("READY 1"));
    return;
  }
  char* save = NULL;
  char* kind = strtok_r(input, ",", &save);
  char* seqStr = strtok_r(NULL, ",", &save);
  char* chStr = strtok_r(NULL, ",", &save);
  char* pulseStr = strtok_r(NULL, ",", &save);
  char* extra = strtok_r(NULL, ",", &save);
  unsigned long seq = 0, ch = 0, pulse = 0;
  if (!kind || strcmp(kind, "M") != 0 || !parseNumber(seqStr, &seq) ||
      !parseNumber(chStr, &ch) || !parseNumber(pulseStr, &pulse) || extra) {
    error(seq, "FORMAT");
    return;
  }
  if (ch > 15 || pulse < 500 || pulse > 2500) {
    error(seq, "RANGE");
    return;
  }
  // 50 Hz = 20,000 us per 4096 ticks; use 32-bit arithmetic.
  uint16_t ticks = (uint32_t(pulse) * 4096UL + 10000UL) / 20000UL;
  pwm.setPWM(uint8_t(ch), 0, ticks);
  Serial.print(F("ACK,"));
  Serial.println(seq);
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  pwm.begin();
  pwm.setPWMFreq(50);
  Serial.println(F("READY 1"));
}

void loop() {
  while (Serial.available()) {
    char c = char(Serial.read());
    if (c == '\n') {
      frame[used] = '\0';
      if (used) process(frame);
      used = 0;
    } else if (c != '\r') {
      if (used + 1 >= sizeof(frame)) {
        used = 0;
        error(0, "FRAME_TOO_LONG");
      } else {
        frame[used++] = c;
      }
    }
  }
}
