/*
      PC sends: 'R' 
      Arduino replies: LUX:<lux_value>,SQM:<sqm_value>

    Example reply:
      LUX:XXXX,SQM:XXXX

  NOTE:
  - SQM formula is approximate and should be calibrated
    against a real SQM if you need accurate values.
  - Alternatively use lux at absolute darkness = 0 to set the zero point in code 

  Wiring (Arduino Nano):
    5V  -> VIN
    GND -> GND
    A4  -> SDA
    A5  -> SCL
*/

#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_TSL2591.h>
#include <math.h>

// Create a TSL2591 sensor object with ID = 2591
Adafruit_TSL2591 tsl = Adafruit_TSL2591(2591);

// Function declarations
void configureSensor();
float readLux();
float luxToSQM(float lux);

void setup() {
  // Start serial
  Serial.begin(115200);
  delay(500);      // Give time for Serial ( Needed because serial... asks politely on datasheet )

  // Start I2C ( Specific serial datastream from sensor )
  Wire.begin();

  // Initialize the sensor
  if (!tsl.begin()) {
    // sensor error
    Serial.println("ERROR: TSL2591 not found.");
    while (true) {
      // Halt!
      delay(1000);
    }
  }

  // gain and integration time
  configureSensor();
}

void loop() {
  // Wait for commands over serial
  if (Serial.available() > 0) {
    char cmd = Serial.read();

    // when R comes, do some reading and math
    if (cmd == 'R') {
      float lux = readLux();

      if (lux <= 0.0f) {
        // If lux < 0 ==> Lux = 0 since calibration error, still shown in rawline 
        Serial.println("LUX:0.00000,SQM:NaN");
      } else {
        float sqm = luxToSQM(lux);

        // Reply as a single line
        Serial.print("LUX:");
        Serial.print(lux, 5);   // 5 decimal places for lux
        Serial.print(",SQM:");
        Serial.println(sqm, 2); // 2 decimal places for mag/arcsec
      }
    }
  }
}

/*
  configureSensor()

  Set gain and integration time for the TSL2591.
  You can tweak these numbers based on how bright your environment is
  Will be added in GUI when I have more time
*/
void configureSensor() {
  // Gain options: TSL2591_GAIN_LOW, _MED, _HIGH, _MAX
  tsl.setGain(TSL2591_GAIN_MED);

  // Integration time options:
  //  TSL2591_INTEGRATIONTIME_100MS, _200MS, _300MS, _400MS, _500MS, _600MS
  tsl.setTiming(TSL2591_INTEGRATIONTIME_200MS);
}

/*
  readLux()
  Measures full-spectrum & IR channels, then converts to lux
*/
float readLux() {
  // Read 32-bit full luminosity (IR in upper 16 bits (2 bytes), full in lower 16 bits (2 bytes))
  // This is cobbled from the datasheet and some examples
  uint32_t lum = tsl.getFullLuminosity();
  uint16_t ir = lum >> 16;
  uint16_t full = lum & 0xFFFF;

  // Convert to lux
  float lux = tsl.calculateLux(full, ir);

  return lux;
}

/*
  lux to mag/arcsec

  Approximate conversion from lux to sky brightness in mag/arcsec^2.
  Roughly
    mag/arcsec^2 = 12.6 - 2.5 * log10(cd/m^2)

  This is only an approximation, but a decent one nonetheless.
*/
float luxToSQM(float lux) {
  const float pi = 3.1415926f;

  if (lux <= 0.0f) {
    return NAN;
  }

  float cd_per_m2 = pi * lux;
  float sqm = 12.6f - 2.5f * log10(cd_per_m2);

  return sqm;
}
