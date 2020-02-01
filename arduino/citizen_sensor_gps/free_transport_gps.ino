/* Arduino settings */
/* Set board to: "Adafruit Feather M0" */

/* PINS IN USE
  - #9, A7 for battery
  - A1, for low battery indicator light
  - #4,7,8 for SD card
*/

/*-----( Import needed libraries )-----*/
#include <SPI.h>
#include <SD.h>
#include <Adafruit_GPS.h>

/*-----( Declare Constants and Pin Numbers )-----*/
//#define DEBUG
//#define BUTTONS_DEBUG
//#define GPS_DEBUG
#define BUTTONS // enable/disable buttons
#define VBATPIN A7
#define LOWBATPIN A1
#define GPSSerial Serial1
#define VOLTAGE_WARNING_LIMIT 3.3
// file name (withou extension) must be 8 characters or less
#define DATA_FILE "commute.txt"
#define EVENT_FILE "events.txt"

const int chipSelect = 4;
const int button_pin_menu  = 13;
const int button_pin_plus  = 12;
const int button_pin_minus = 11;
const int button_pin_misc  = 10;

/*-----( Declare objects )-----*/
/*-----( Declare Variables )-----*/
int pstate = 0;
//  1: booting, normal
// -1: can't write to sd card
// -2: low battery

// for GPS
uint32_t timer = millis();

// for battery
float battery_voltage = 0;

// For buttons
int button_menu_state;
int button_plus_state;
int button_minus_state;
int button_misc_state;
int last_button_menu_state = LOW;
int last_button_plus_state = LOW;
int last_button_minus_state = LOW;
int last_button_misc_state = LOW;
unsigned long last_debounce_time = 0;  // the last time the output pin was toggled
unsigned long debounce_delay = 30;    // the debounce time; increase if the output flickers
int click_counter = 0;

// Connect to the GPS on the hardware port
Adafruit_GPS GPS(&GPSSerial);

/* ################## Setup ################ */
void setup() {

#ifdef DEBUG
  // Open serial communications and wait for port to open:
  Serial.begin(115200);

  while (!Serial) {
    ; // wait for serial port to connect. Needed for native USB port only
  }

  Serial.print("Initializing SD card...");
#endif

  // see if the card is present and can be initialized:
  if (!SD.begin(chipSelect)) {
    // Need to add code to turn on a ligth or something to indicate SD card problem

#ifdef DEBUG
    Serial.println("Card failed, or not present");
#endif

    // don't do anything more:
    while (1);
    // probably want to sleep for a second and check again rather than infinite loop
  }

#ifdef DEBUG
  Serial.println("card initialized.");
#endif

  // turn off feather M0 board led to save power
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

#ifdef BUTTONS
  // initialize buttons
  // initialize the pushbutton pin as an input:
  pinMode(button_pin_menu, INPUT_PULLDOWN);
  pinMode(button_pin_plus, INPUT_PULLDOWN);
  pinMode(button_pin_minus, INPUT_PULLDOWN);
  pinMode(button_pin_misc, INPUT_PULLDOWN);
#endif

  // GPS
  // 9600 baud is the default rate for the Ultimate GPS
  GPSSerial.begin(9600);

  // comment this line to turn off RMC (recommended minimum) and GGA (fix data) including altitude
  GPS.sendCommand(PMTK_SET_NMEA_OUTPUT_RMCGGA);
  // uncomment this line to turn on only the "minimum recommended" data
  //GPS.sendCommand(PMTK_SET_NMEA_OUTPUT_RMCONLY);

  GPS.sendCommand(PMTK_SET_NMEA_UPDATE_1HZ); // 1 Hz update rate

  // Request updates on antenna status, comment out to keep quiet
  GPS.sendCommand(PGCMD_ANTENNA);

  delay(1000); // because Adafruit does it

  // Ask for firmware version
  GPSSerial.println(PMTK_Q_RELEASE);

}


/* ################## Main Loop ################ */
void loop() {

  // check for button presses
  check_buttons();

  // build GPS data, and check if ready for processing
  // return if complete message retrieved but parsing failed
  if ( !read_gps_device_data() ) {
    return;
  }

  // if millis() or timer wraps around, we'll just reset it
  if (timer > millis()) {
    timer = millis();
  }

  // log the current data every 2 seconds (or so)
  if (millis() - timer > 2000) {
    timer = millis(); // reset the timer

    // update battery voltage measure
    measure_battery_voltage();

    // log GPS data to SD card
    log_gps_data();
  }
}

/* ################## Utility functions (that do the actual work) ################ */

void log_event() {
  // Log the data
    File eventFile = SD.open(EVENT_FILE, FILE_WRITE);
    // if the file is available, write to it:
    if (!eventFile) {
      pstate = -1;

#ifdef DEBUG
      Serial.print("Wasn't able to open event file for writing.");
#endif

      return;
    }

#ifdef DEBUG
    Serial.print("Event file opened successfully.");
#endif

    // log date
    eventFile.print(click_counter); eventFile.print(',');
    // log date
    eventFile.print(GPS.year, DEC);  eventFile.print('/');
    eventFile.print(GPS.month, DEC); eventFile.print('/');
    eventFile.print(GPS.day, DEC);   eventFile.print(',');

    // log time
    if (GPS.hour < 10) {
      eventFile.print("0");
    }
    eventFile.print(GPS.hour, DEC); eventFile.print(':');
    if (GPS.minute < 10) {
      eventFile.print("0");
    }
    eventFile.print(GPS.minute, DEC); eventFile.print(':');
    if (GPS.seconds < 10) {
      eventFile.print("0");
    }
    eventFile.print(GPS.seconds, DEC); //eventFile.print(',');
    eventFile.print("\n");

    eventFile.close();
}

// Handle buttons presses
void check_buttons() {
#ifdef BUTTONS
  // Read button values
  int button_menu_value = digitalRead(button_pin_menu);
  int button_plus_value = digitalRead(button_pin_plus);
  int button_minus_value = digitalRead(button_pin_minus);
  int button_misc_value = digitalRead(button_pin_misc);

  // If the switch changed, due to noise or pressing:
  if ( button_menu_value != last_button_menu_state ) {
    last_debounce_time = millis();
  }

  if ( ( millis() - last_debounce_time ) > debounce_delay ) {
    // we wait until the button has stabilized to get a reading

    if ( button_menu_value != button_menu_state ) {
      // new value, so this won't be called again during this press
      button_menu_state = button_menu_value;

#ifdef BUTTONS_DEBUG
      Serial.print("After debounce_delay: ");
      Serial.println(last_button_menu_state);
#endif

      if (button_menu_state == HIGH) {
        log_event();
        click_counter += 1;

#ifdef BUTTONS_DEBUG
        Serial.println("Button depressed, HIGH value");
        Serial.println(click_counter);
#endif
        
      }
    }

    last_debounce_time = 0;
  }
  last_button_menu_state = button_menu_value;
#endif
}

void log_gps_data() {

#ifdef GPS_DEBUG
  Serial.print("\nTime: ");
  if (GPS.hour < 10) {
    Serial.print('0');
  }
  Serial.print(GPS.hour, DEC); Serial.print(':');
  if (GPS.minute < 10) {
    Serial.print('0');
  }
  Serial.print(GPS.minute, DEC); Serial.print(':');
  if (GPS.seconds < 10) {
    Serial.print('0');
  }
  Serial.print(GPS.seconds, DEC); Serial.print('.');

  Serial.print("Date: ");
  Serial.print(GPS.day, DEC); Serial.print('/');
  Serial.print(GPS.month, DEC); Serial.print("/20");
  Serial.println(GPS.year, DEC);
  Serial.print("Fix: "); Serial.print((int)GPS.fix);
  Serial.print(" quality: "); Serial.println((int)GPS.fixquality);

  Serial.print("Fix: "); Serial.print((int)GPS.fix);
  Serial.print(" quality: "); Serial.println((int)GPS.fixquality);
#endif

  if (GPS.fix) {
#ifdef GPS_DEBUG
    Serial.print("Location: ");
    Serial.print(GPS.latitudeDegrees, 4); Serial.print(GPS.lat);
    Serial.print(", ");
    Serial.print(GPS.longitudeDegrees, 4); Serial.println(GPS.lon);
    Serial.print("Speed (knots): "); Serial.println(GPS.speed);
    Serial.print("Angle: "); Serial.println(GPS.angle);
    Serial.print("Altitude: "); Serial.println(GPS.altitude);
    Serial.print("Satellites: "); Serial.println((int)GPS.satellites);
    Serial.println("");
#endif

#ifdef GPS_DEBUG
    Serial.print("Volatage: ");
    Serial.println(get_battery_voltage());
#endif

    // Log the data
    File dataFile = SD.open(DATA_FILE, FILE_WRITE);
    // if the file is available, write to it:
    if (!dataFile) {
      pstate = -1;

#ifdef DEBUG
      Serial.print("Wasn't able to open data file for writing.");
#endif

      return;
    }

#ifdef DEBUG
    Serial.print("Data file opened successfully.");
#endif

    // log date
    dataFile.print(GPS.year, DEC); dataFile.print('/');
    dataFile.print(GPS.month, DEC); dataFile.print('/');
    dataFile.print(GPS.day, DEC); dataFile.print(',');

    // log time
    if (GPS.hour < 10) {
      dataFile.print("0");
    }
    dataFile.print(GPS.hour, DEC); dataFile.print(':');
    if (GPS.minute < 10) {
      dataFile.print("0");
    }
    dataFile.print(GPS.minute, DEC); dataFile.print(':');
    if (GPS.seconds < 10) {
      dataFile.print("0");
    }
    dataFile.print(GPS.seconds, DEC); dataFile.print(',');

    // log sat data
    dataFile.print(GPS.satellites, DEC); dataFile.print(',');
    dataFile.print(GPS.altitude, DEC); dataFile.print(',');
    dataFile.print(GPS.speed, DEC); dataFile.print(',');
    dataFile.print(GPS.latitudeDegrees, 5); dataFile.print(',');
    dataFile.print(GPS.longitudeDegrees, 5); dataFile.print(',');

    // log miscellaneous
    dataFile.print(battery_voltage, 3);

    dataFile.print("\n");
    dataFile.close();
  }
}

bool read_gps_device_data() {
  // Always read data from the GPS
  char c = GPS.read();
  // if a full message is ready, raise flag
  if (GPS.newNMEAreceived()) {
    // Call GPS.lastNMEA() sets the GPS.newNMEAreceived() flag to false
    if (!GPS.parse(GPS.lastNMEA())) {
      // failed to parse, restart loop
      return false;
    }
  }
  return true;
}

// Retrieve the battery voltage
void measure_battery_voltage() {

  float measuredvbat = analogRead(VBATPIN);
  measuredvbat *= 2;    // we divided by 2, so multiply back
  measuredvbat *= 3.3;  // Multiply by 3.3V, our reference voltage
  measuredvbat /= 1024; // convert to voltage
  battery_voltage = measuredvbat;

  if (battery_voltage < VOLTAGE_WARNING_LIMIT) {
    // low battery set program state
    pstate = -2;
  }
}
