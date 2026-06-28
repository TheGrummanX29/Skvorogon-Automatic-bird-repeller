// Motor driver
#define rightm_pin 7
#define leftm_pin 8
#define leftm_control_fir 22
#define leftm_control_sec 24
#define rightm_control_fir 30
#define rightm_control_sec 26
#define buzzer 9
// Variables
int LeftUpCurrentDegrees;
int LeftHORCurrentDegrees;
int RightUpCurrentDegrees;
int RightHorCurrentDegrees;
int ROT_CAM;
int joy_left;
int joy_right;
int cowmaxunsafedeg = 50;
int cowminunsafedeg = 30;
int lastendup;
// Libraries *_*

#include <Servo.h>
#include <Wire.h>
#include <IBusBM.h>
#define SERVOMAX 270


#define SERVOMID 90
#define LaserR 40


// Channels
#define joy_leftUpCh 2
#define joy_rightCh 1
#define joy_leftHorCh 3
#define joy_righHorCh 0
#define laserCh 7
#define onMoveCh 6
#define buzzCh 5
#define cowCh 8
#define autCh 9

int counter = 0;      // replacement for i
int servotimer = 0;   // timer variable


int minangle = 10;
int angle = minangle;


// DO NOT TOUCH!!! Library setup.
IBusBM ibusRc;
HardwareSerial& ibusRcSerial = Serial1;
HardwareSerial& debugSerial = Serial;
// DO NOT TOUCH!!! Library setup.

Servo righthor, rightup, lfthr, lftup; // Declare servos
bool cow, aut, onMove, LaserOn, jsaut = false;




// Autonomous operation function
void autonom(){
  controlLaser();
  // Moving forward! To the great and glorious goal! 
  digitalWrite(rightm_control_fir,HIGH);
  digitalWrite(rightm_control_sec,HIGH);
  analogWrite(rightm_pin, 255);
  analogWrite(leftm_pin, 255);
  digitalWrite(leftm_control_fir,HIGH);
  digitalWrite(leftm_control_sec,HIGH);
  for(int i=0; i<=270; i++){
  RightUpCurrentDegrees = i;
  RightHorCurrentDegrees = abs(i-270);
  rightup.write(RightUpCurrentDegrees);
  righthor.write(RightHorCurrentDegrees);
  delay(10);
  if ((cow) and (RightUpCurrentDegrees > cowminunsafedeg) and (RightUpCurrentDegrees < cowmaxunsafedeg)) {
  digitalWrite(LaserR, LOW); 
  }
  }
  for(int i=270; i>=0; i--){
  RightUpCurrentDegrees = i;
  RightHorCurrentDegrees = abs(i-270);
  rightup.write(RightUpCurrentDegrees);
  righthor.write(RightHorCurrentDegrees);
  delay(10);
  if ((cow) and (RightUpCurrentDegrees > cowminunsafedeg) and (RightUpCurrentDegrees < cowmaxunsafedeg)) {
    digitalWrite(LaserR, LOW); 
  }
  }
}

// Laser control function

void controlLaser() {
  Serial.println("controlLaser function started"); 
  LaserOn = readSwitch(laserCh, 1); 
  if(LaserOn) {
    digitalWrite(LaserR, LOW);
  }
  else {
    digitalWrite(LaserR, HIGH);
  }
    // Check for cows and related dangers. Turning off lasers in the danger zone.
  if ((cow) and (RightUpCurrentDegrees > cowminunsafedeg) and (RightUpCurrentDegrees < cowmaxunsafedeg)) {
    digitalWrite(LaserR, LOW); 
  }

}

// Track control function

void controlTracks() {
  Serial.println("controlTracks function started");
  joy_left = readChannel(joy_leftUpCh, -255, 255, 0);
  joy_right = readChannel(joy_rightCh, -255, 255, 0);
  Serial.println(joy_right);
  // Left track control
  if ((joy_left)>20) { 
    // Left track forward
    analogWrite(leftm_pin,abs(joy_left));
    digitalWrite(leftm_control_fir,HIGH);
    digitalWrite(leftm_control_sec,LOW);
  }
  else if ((joy_left)<-20) {
    // Left track reverse
    analogWrite(leftm_pin,abs(joy_left));
    digitalWrite(leftm_control_fir,LOW);
    digitalWrite(leftm_control_sec,HIGH);
  }

  // Right track control
  if ((joy_right)>20) {
    
    // Right track forward
        digitalWrite(rightm_control_fir,LOW);
    digitalWrite(rightm_control_sec,HIGH);
    analogWrite(rightm_pin,abs(joy_right));
  }
  else if ((joy_right)<-20) {
    
    // Right track reverse
    analogWrite(rightm_pin,abs(joy_right));
    digitalWrite(rightm_control_fir,HIGH);
    digitalWrite(rightm_control_sec,LOW);
  }

  if ((joy_left<=20) and(joy_left>=-20)) {
    
    // Left brake 
    digitalWrite(leftm_control_fir,HIGH);
    digitalWrite(leftm_control_sec,HIGH);
    analogWrite(leftm_pin,255);
  }
  if ((joy_right<=20) and(joy_right>=-20)) {
    
    // Right brake
    digitalWrite(rightm_control_fir,HIGH);
    digitalWrite(rightm_control_sec,HIGH);
    analogWrite(rightm_pin,255);
  }


}

// Servo control function

void controlServos() {
  Serial.println("controlServos function started");

  // Get acceleration values
  int joy_rightUp = readChannel(joy_rightCh, -10, 10, 0);
  int joy_righHor = readChannel(joy_righHorCh, -10, 10, 0);

  // Add acceleration to servo degrees
  RightUpCurrentDegrees += joy_rightUp;
  RightHorCurrentDegrees += joy_righHor;

  // Value filtering / constraints
  if (LeftUpCurrentDegrees > SERVOMAX) {LeftUpCurrentDegrees = SERVOMAX;}
  if (LeftUpCurrentDegrees < 0) {LeftUpCurrentDegrees = 0;}
  if (LeftHORCurrentDegrees > SERVOMAX) {LeftHORCurrentDegrees = SERVOMAX;}
  if (LeftHORCurrentDegrees < 0) {LeftHORCurrentDegrees = 0;}
  if (RightUpCurrentDegrees > SERVOMAX) {RightUpCurrentDegrees = SERVOMAX;}
  if (RightUpCurrentDegrees < 0) {RightUpCurrentDegrees = 0;}
  if (RightHorCurrentDegrees > SERVOMAX) {RightHorCurrentDegrees = SERVOMAX;}
  if (RightHorCurrentDegrees < 0) {RightHorCurrentDegrees = 0;}

  // Update servo positions
  rightup.write(RightUpCurrentDegrees);
  righthor.write(RightHorCurrentDegrees);
}


void setup() {
  pinMode(buzzer, INPUT);
  // Safety initialization
  digitalWrite(LaserR, LOW);
  // Servo setup
  righthor.attach(5);
  rightup.attach(3);

  // DO NOT TOUCH!!! Library setup.
  debugSerial.begin(74880);
  ibusRc.begin(ibusRcSerial);
  // DO NOT TOUCH!!! Library setup.

  Serial.begin(9600);
  cowmaxunsafedeg = 180;
  cowminunsafedeg = 50;
  // Pin modes setup
  pinMode(leftm_pin,OUTPUT);
  pinMode(leftm_control_fir,OUTPUT);
  pinMode(leftm_control_sec,OUTPUT);
  pinMode(LaserR,OUTPUT);

  // Reset servos to middle positions
  RightUpCurrentDegrees = SERVOMID;
  RightHorCurrentDegrees = SERVOMID;

  // DO NOT TOUCH!!! Library setup.

}

int readChannel(byte channelInput, int minLimit, int maxLimit, int defaultValue){
  uint16_t ch = ibusRc.readChannel(channelInput);
  if (ch < 100) return defaultValue;
  return map(ch, 1000, 2000, minLimit, maxLimit);
}

// Read the channel and return a boolean value
bool readSwitch(byte channelInput, bool defaultValue){
  int intDefaultValue = (defaultValue)? 100: 0;
  int ch = readChannel(channelInput, 0, 100, intDefaultValue);
  return (ch > 50);
}

// DO NOT TOUCH!!! 

void loop() {
// Buzzer control
if (readChannel(buzzCh, 0, 1000, 0) > 500){ pinMode(buzzer, OUTPUT); tone(buzzer, 500);}
else{noTone(buzzer); pinMode(buzzer, INPUT); } // Temporary workaround for buzzer control.


// Compare cow and aut states with Blink and RC transmitter inputs.
cow = readSwitch(cowCh, 0);
if (analogRead(A0)<300){
  aut=true;
}
else{
  aut=false;
}
Serial.println(analogRead(A0));
// Read operation mode: tracks or servos. OnMove true - track control mode. OnMove false - servo mode.
onMove = readSwitch(onMoveCh, 0);

if (aut){ // Check for autonomous mode. No - manual control. Yes - automatic control.
  autonom();
}
else{
  servotimer = millis();
  // Manual control
  // Laser control
  controlLaser();
  if(onMove) {
    // Track control mode
    controlTracks();
  }
  else {
    // Servo control mode
    controlServos();
  }
}
}
