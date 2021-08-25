#include <AFMotor.h>
#if defined(ARDUINO) && ARDUINO >= 100
#include "Arduino.h"
#else
#include "WProgram.h"
#endif

#include "EMGFilters.h"

#define TIMING_DEBUG 1

#define SensorInputPin A5 
AF_DCMotor motor(1);

EMGFilters myFilter;
int sampleRate = SAMPLE_FREQ_1000HZ;

int humFreq = NOTCH_FREQ_50HZ;


static int Threshold = 400;

unsigned long timeStamp;
unsigned long timeBudget;

void setup() {
   
   
    myFilter.init(sampleRate, humFreq, true, true, true);

   
    Serial.begin(115200);

    
    timeBudget = 1e6 / sampleRate;
    
}

void loop() {
    
    timeStamp = micros();

    int Value = analogRead(SensorInputPin);

       int DataAfterFilter = myFilter.update(Value);

    int envlope = sq(DataAfterFilter);
    
    envlope = (envlope > Threshold) ? envlope : 0;
    if (sq(DataAfterFilter) > 9000)
    {motor.setSpeed(220);
    motor.run(FORWARD);
    delay(100);
    }
    else
    {motor.setSpeed(150);
    motor.run(BACKWARD);
    delay(100);}
    
    timeStamp = micros() - timeStamp;
    if (TIMING_DEBUG) {
        
        
        Serial.println(envlope);
        Serial.println(timeStamp);
    }


    
}

  

  
