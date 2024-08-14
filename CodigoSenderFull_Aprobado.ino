#include "heltec.h"
#include <Arduino.h>
#include <Wire.h>
#include <dht11.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#define BAND    915E6  
// ----------------------------------- //
// Configuracion del ADC para ESP32 y Arduino UNO. //
#ifdef ESP32
#define ADC_MAX_VOLTAGE 3.3  // 3.3V para ESP32
#define ADC_MAX 4096.0       // 2^12 bits
#else
#define ADC_MAX_VOLTAGE 5.0  // 5V para Arduino UNO
#define ADC_MAX 1024.0       // 2^10 bits
#endif
// Macro para convertir lectura del ADC en voltios.
// Mas información acerca de macros:
// https://gcc.gnu.org/onlinedocs/cpp/Macro-Arguments.html#Macro-Arguments-1
#define TENSION(valor) (valor * (ADC_MAX_VOLTAGE / ADC_MAX))
// ----------------------------------- //
// Parametros de configuracion MQ7.    //
// ppm(Rs/R0) = A0 * Rs/R0 ^ (A1)      //
// ----------------------------------- //
#define MQ7_CALIBRATION_SECONDS 15
#define MQ7_LOAD_RES 10.0
#define MQ7_COEF_A0 100.0
#define MQ7_COEF_A1 -1.513
#define MQ7_CALIBRATION_CONSTANT 5.0  // aprox 10ppm la relacion Rs / R0 = 5.0
float mq7_R0 = 0.0;                   // variable para almacenar el valor de R0
// ----------------------------------- //
// Parametros de configuracion         //
// Del sensor de polvo SharpGP2Y10.    //
// ----------------------------------- //
#define SHARP_SAMPLINGTIME 280
#define SHARP_DELTATIME 40
#define SHARP_SLEEPINGTIME 9680
// ----------------------------------- //
// Definiciones de pines y constantes. //
// ----------------------------------- //
#define SDA1 4
#define SCL1 15
#define RESET_OLED 16  // Pin de reset del OLED.
#define DHT11PIN 23
#define MQ7_PIN 36  // Pin del sensor de gas.
#define SHARP_LED_PIN 22
#define SHARP_VO_PIN 38
#define PIN_VBAT 13
//#define PIN_VEXT_EN 21
#define PIN_BUZZER 12

// ----------------------------------- //
unsigned long tiempo_inicio_caida = 0;

// ----------------------------------- //
// Parametros para la deteccion de caida
// ----------------------------------- //
#define ACEL_GRAVEDAD 10                   //m/s2
#define MARGEN_ACEL 4                      //m/s2
#define TIEMPO_DETECCION_CAIDA 3000        //5 segundos
#define TIEMPO_DETECCION_EN_EL_PISO 10000  //10 segundos


/**
 * @brief Estructura de datos para almace
 * nar los datos que enviamos por LoRa.
 */
struct data_frame {
  int counter;
  bool co2_calibrado;  //Byte para almacenar 1 si se hizo la calibracion del MQ7, 0 si no.
  bool paracaidas_desplegado;
  bool impacto_detectado;
  float co2;   //Variable para almacenar el valor de CO2 en ppm.
  float pm25;  //Variable para almacenar el valor de PM2.5 en ug/m3.
  float dht_temp;
  float dht_hum;
  float bmp_temp;
  float bmp_pres;
  float altitud;
  float acel;
  float vbat;
} data;
#define data_size sizeof(struct data_frame)
dht11 DHT11;
Adafruit_MPU6050 mpu;
/**
 * @brief Estructura de datos para almacenar los timers que usamos con millis().
 * Pueden agregarse tantos timers como se necesiten.
 * Para mas información acerca de millis() y timers:
 * https://www.arduino.cc/reference/en/language/functions/time/millis/
 * https://www.arduino.cc/en/Tutorial/BuiltInExamples/BlinkWithoutDelay
 */
struct my_timers {
  unsigned int muestra_1segundo;
  unsigned int lectura_sharp;
  unsigned int calibracion_mq7;
} timers;

void detectar_caida() {
  static float altitud_anterior = 0.0;         // Variable para almacenar la altitud anterior.
  static unsigned long tiempo_paracaidas = 0;  // Variable para medir el tiempo de paracaídas desplegado.
  //chatgpt sugirio usar static para que no se borren los valores entre llamados de la funcion.}

  unsigned long tiempo_actual = millis();

  if (!data.paracaidas_desplegado) {
    if (data.acel < MARGEN_ACEL && data.altitud < altitud_anterior) {
      if (tiempo_paracaidas == 0) {
        tiempo_paracaidas = tiempo_actual;                                       // Iniciar el contador de tiempo de paracaídas desplegado
      } else if (tiempo_actual - tiempo_paracaidas >= TIEMPO_DETECCION_CAIDA) {  // Esperar al menos 5 segundos
        data.paracaidas_desplegado = true;
        tiempo_inicio_caida = tiempo_actual;
      }
    } else {
      tiempo_paracaidas = 0;  // Reiniciar el contador de tiempo si la condición no se cumple
    }
  } else if (!data.impacto_detectado) {
    if (tiempo_actual - tiempo_inicio_caida >= TIEMPO_DETECCION_EN_EL_PISO && abs(data.acel - ACEL_GRAVEDAD) < MARGEN_ACEL) {
      data.impacto_detectado = true;
      digitalWrite(PIN_BUZZER, HIGH);  // Encender el buzzer en el pin Y con tono 500Hz.
    }
  }

  altitud_anterior = data.altitud;
}

void setup() {
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(RESET_OLED, OUTPUT);
  //pinMode(PIN_VEXT_EN, OUTPUT);
  //pinMode(PIN_VBAT, INPUT);
  digitalWrite(PIN_BUZZER, LOW);
  //digitalWrite(PIN_VEXT_EN, LOW);  //Habilitamos VEXT para habilitar medir la tension de la bateria en el pin 13.
  digitalWrite(RESET_OLED, HIGH);
  delay(1000);
  digitalWrite(RESET_OLED, LOW);

  Heltec.begin(false /*DisplayEnable Enable*/, true /*Heltec.LoRa Disable*/, true /*Serial Enable*/, true /*PABOOST Enable*/, BAND /*long BAND*/);
  LoRa.setTxPower(14, RF_PACONFIG_PASELECT_PABOOST);
  LoRa.setSpreadingFactor(10);  //disminuir tiempo de transmision!
  Wire.begin(4, 15);
  bmp180_setup();
  pinMode(SHARP_LED_PIN, OUTPUT);     //Establecer el pin del LED interno del sensor SHARP como salida
  digitalWrite(SHARP_LED_PIN, HIGH);  // Apagar el LED interno del sensor de polvo
  if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050 chip");
  }

  mpu.setAccelerometerRange(MPU6050_RANGE_16_G);
  mpu.setGyroRange(MPU6050_RANGE_250_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  data = { 0 };    // Inicializamos todos los datos a 0.
  timers = { 0 };  // Inicializamos todos los timers a 0.

  timers.calibracion_mq7 = millis();  // Iniciar timer de calibracion
}

void loop() {

  // timer 1 cada 1 segundo
  unsigned int currentMillis = millis();
  if (currentMillis - timers.muestra_1segundo >= 1000) {
    timers.muestra_1segundo = currentMillis;  // resetear timer
    digitalWrite(25, LOW);                    // Apagar LED conectado al pin 25
    data.counter++;                           // Incrementar el contador en 1
    data.co2 = leer_mq7();                    // Leer el valor del sensor de gas
    int chk = DHT11.read(DHT11PIN);
    data.dht_temp = DHT11.temperature;
    data.dht_hum = DHT11.humidity;
    data.bmp_temp = leer_temp_bmp180();
    data.bmp_pres = leer_presion_bmp180();
    data.altitud = leer_altura_abs_bmp180();
    data.vbat = leerVoltajeBateria();
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);
    data.acel = sqrt(a.acceleration.x * a.acceleration.x + a.acceleration.y * a.acceleration.y + a.acceleration.z * a.acceleration.z);
    detectar_caida();
    enviar_datos();   // Enviar los datos por LoRa
    mostrar_datos();  // Mostrar los datos por Serial
  }

  // timer 2 cada 10 segundos
  if (currentMillis - timers.lectura_sharp >= 5000) {
    timers.lectura_sharp = currentMillis;  // resetear timer
    data.pm25 = leer_pm25();               // Leer el valor del sensor de polvo
                                           // Este sensor SI O SI requiere un periodo de muestreo de 10 segundos
  }

  // timer 3 se ejecuta una sola vez pasados los 15 segundos
  if (currentMillis - timers.calibracion_mq7 >= 15000 && data.co2_calibrado == 0) {
    timers.calibracion_mq7 = currentMillis;  // resetear timer
    mq7_R0 = MQ7_leerRS() / 5.0;             // Calibrar el sensor MQ7
    data.co2_calibrado = 1;                  // Indicar que la calibracion ya se realizo
  }
}

/**
 * @brief Leer el valor de Rs del sensor MQ7.
 * @return Rs del sensor MQ7.
 */
float MQ7_leerRS()  // Leer el valor de Rs del sensor MQ7
{
  float tension_mq7 = TENSION(analogRead(MQ7_PIN));  // Leer el valor del sensor de gas
  float RsRl = (ADC_MAX_VOLTAGE - tension_mq7) / tension_mq7;
  return MQ7_LOAD_RES * RsRl;
}


float leerVoltajeBateria() {
  float tension_lectura = TENSION(analogRead(PIN_VBAT));
  //R1: 220K, R2: 100K
  //tension_lectura = vbat * R2 / (R1 + R2)
  //vbat = tension_lectura * (R1 + R2) / R2
  return tension_lectura * 3.2;
}

/**
 * @brief Leer el valor PPM de co2 del sensor MQ7
 */
float leer_mq7() {
  if (data.co2_calibrado == 0)  // Si no se calibro el sensor, devolver 0
    return 0.0;
  return (float)MQ7_COEF_A0 * pow(MQ7_leerRS() / mq7_R0, MQ7_COEF_A1);
}

/**
 * @brief Leer el sensor PM25 Sharp GP2Y10
 * 
 */
float leer_pm25() {
  digitalWrite(SHARP_LED_PIN, LOW);  // Encender el LED interno del sensor de polvo
  delayMicroseconds(SHARP_SAMPLINGTIME);

  int voMeasured = analogRead(SHARP_VO_PIN);  // read the dust value

  delayMicroseconds(SHARP_DELTATIME);
  digitalWrite(SHARP_LED_PIN, HIGH);  // Apagar el LED interno del sensor de polvo

  // linear eqaution taken from http://www.howmuchsnow.com/arduino/airquality/
  // Chris Nafis (c) 2012
  float dustDensity = 170 * TENSION(voMeasured) - 0.1;

  if (dustDensity < 0) {
    dustDensity = 0.00;
  }

  return dustDensity;
}

/**
 * @brief Mostrar los datos por Serial.
 */
void mostrar_datos() {
  Serial.print("Counter: ");
  Serial.print(data.counter);  // Imprimir el valor del contador.
  Serial.print(", MQ7 Calibrado: ");
  Serial.print((int)data.co2_calibrado);  // Imprimir si el sensor MQ7 esta calibrado.
  Serial.print(", CO: ");
  Serial.print(data.co2, 2);  // Imprimir el valor del sensor de gas.
  Serial.print("ppm, PM25: ");
  Serial.print(data.pm25, 2);  // Imprimir el valor del sensor de polvo.
  Serial.print("ppm, hum:");   // Imprimir ppm (partes por millon).
  Serial.print(data.dht_hum, 2);
  Serial.print(",temp:");
  Serial.print(data.dht_temp, 2);
  Serial.print(",temp:");
  Serial.print(data.bmp_temp, 2);
  Serial.print(",presion:");
  Serial.print(data.bmp_pres, 2);
  Serial.print(",altitud:");
  Serial.print(data.altitud);
  Serial.print(",acel:");
  Serial.print(data.acel);
  Serial.print(",vbat:");
  Serial.print(data.vbat, 2);  // Imprimir con 2 decimales
  Serial.print(",t:");
  Serial.print(millis());
  Serial.println();  // Imprimir una linea en blanco.
}

/**
 * @brief Enviar los datos por LoRa.
 * Usamos una estructura de datos para almacenar los datos que enviamos.
 * La estructura de datos se llama data_frame y tiene un tamaño de data_size bytes
 */
void enviar_datos() {


  LoRa.beginPacket();
  LoRa.print(data.counter);  // Imprimir el valor del contador.
  LoRa.print(",");
  LoRa.print((int)data.co2_calibrado);  // Imprimir si el sensor MQ7 esta calibrado.
  LoRa.print(",");
  LoRa.print(data.co2, 2);  // Imprimir el valor del sensor de gas.
  LoRa.print(",");
  LoRa.print(data.pm25, 2);  // Imprimir el valor del sensor de polvo.
  LoRa.print(",");           // Imprimir ppm (partes por millon).
  LoRa.print(data.dht_hum, 2);
  LoRa.print(",");
  LoRa.print(data.dht_temp, 2);
  LoRa.print(",");
  LoRa.print(data.bmp_temp);
  LoRa.print(",");
  LoRa.print(data.bmp_pres);  // Imprimir una linea en blanco.
  LoRa.print(",");
  LoRa.print(data.altitud);
  LoRa.print(",");
  LoRa.print(data.acel);
  LoRa.print(",");
  LoRa.print(data.vbat);
  LoRa.print(",");
  LoRa.print(data.paracaidas_desplegado);
  LoRa.print(",");
  LoRa.print(data.impacto_detectado);
  LoRa.print(",");
  LoRa.println(millis());
  LoRa.endPacket();
}
