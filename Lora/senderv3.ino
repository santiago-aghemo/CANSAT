/* Heltec Automation send communication test example
 *
 * senderv3: igual que senderv2 pero
 *  - recibe por UART (Serial1, pin GPIO19) el GPS que manda la Raspberry Pi y lo agrega al paquete LoRa
 *  - SIN impresiones en el monitor serie (no se usa Serial / USB para nada)
 *
 * Function:
 * 1. Send data from a esp32 device over hardware
 *
 * Description:
 *
 * HelTec AutoMation, Chengdu, China
 * 成都惠利特自动化科技有限公司
 * www.heltec.org
 *
 * this project also realess in GitHub:
 * https://github.com/Heltec-Aaron-Lee/WiFi_Kit_series
 * */

//librerias para lora
#include "LoRaWan_APP.h"
#include "Arduino.h"


//definimos las dependencias y puertos del bmp280

#include <Wire.h>
#include <SPI.h>
#include <Adafruit_BMP280.h>

#define MQ4_PIN 5
#define MQ7_PIN 6

#define SDA_PIN 48
#define SCL_PIN 47

Adafruit_BMP280 bmp; 


// ---------- ENLACE CON LA RASPBERRY PI (GPS) ----------
// La Pi manda por UART (cable directo, 3.3 V) una trama por segundo con este formato:
//   $PIG,<seq>,<fix>,<lat>,<lon>,<sats>*<CS>\n      (CS = XOR de todo lo que hay entre $ y *, en hexa)
// Las lineas que no empiecen con '$' o con checksum malo se descartan.
// Se usa double para lat/lon: con float se pierde ~1 m de resolucion.

#define PI_GPS_TIMEOUT_MS 3000   // si pasan mas de 3 s sin trama valida, el dato se considera viejo

// Cableado: Pi GPIO17 (pin fisico 11, TX por software) -> ESP32 GPIO19 (RX). GND con GND. La Pi no recibe nada.
// GPIO19 se eligio para no gastar pines ADC1 (2, 4, 7) que se necesitan para los MQ-136 / MQ-137.
#define PI_RX_PIN   19
#define PI_BAUD     9600

struct PiGps {
  bool valid;
  uint8_t fix;
  uint8_t sats;            // se recibe pero NO se transmite por LoRa
  double lat;
  double lon;
  uint32_t seq;
  uint32_t lastMs;
};
PiGps piGps = {false, 0, 0, 0.0, 0.0, 0, 0};

char piRxBuf[96];
uint8_t piRxLen = 0;

bool parsePiLine(char* line) {
  if (line[0] != '$') return false;
  char* star = strrchr(line, '*');
  if (!star) return false;

  // verificamos el checksum
  uint8_t calc = 0;
  for (char* p = line + 1; p < star; p++) calc ^= (uint8_t)*p;
  if (calc != (uint8_t)strtol(star + 1, NULL, 16)) return false;
  *star = 0;

  unsigned long seq;
  int fix, sats;
  double lat, lon;
  if (sscanf(line + 1, "PIG,%lu,%d,%lf,%lf,%d", &seq, &fix, &lat, &lon, &sats) != 5) return false;

  piGps.valid  = (fix > 0);
  piGps.fix    = (uint8_t)fix;
  piGps.sats   = (uint8_t)sats;
  piGps.lat    = lat;
  piGps.lon    = lon;
  piGps.seq    = (uint32_t)seq;
  piGps.lastMs = millis();
  return true;
}

// Lee lo que haya en el UART de la Pi sin bloquear. Llamar seguido.
void pollPi() {
  while (Serial1.available()) {
    char c = Serial1.read();
    if (c == '\n') {
      piRxBuf[piRxLen] = 0;
      parsePiLine(piRxBuf);
      piRxLen = 0;
    } else if (c != '\r') {
      if (piRxLen < sizeof(piRxBuf) - 1) piRxBuf[piRxLen++] = c;
      else piRxLen = 0;   // linea demasiado larga: basura, se descarta
    }
  }
}

bool piGpsFresh() {
  return piGps.valid && (millis() - piGps.lastMs) < PI_GPS_TIMEOUT_MS;
}



#define RF_FREQUENCY                                915000000 // Hz -> FRECUENCIA, en estacion terrena y cansat deben estar igual

#define TX_OUTPUT_POWER                             5        // dBm -> POTENCIA, directamente proporcional al consumo

#define LORA_BANDWIDTH                              0         // [0: 125 kHz, -> ANCHO DE BANDA, cuanto mas ancho de banda, mas rapido se transmite, pero suele empeorar la sensibilidad
                                                              //  1: 250 kHz,
                                                              //  2: 500 kHz,
                                                              //  3: Reserved]
#define LORA_SPREADING_FACTOR                       7         // [SF7..SF12] -> FACTOR DE SPREADING, cuanto mas alto, mas distancia cubre, pero tarda mas en enviar
#define LORA_CODINGRATE                             1         // [1: 4/5, -> CORRECION DE ERRORES, mas correcion equivale a mas robustez ante ruido, pero es menos eficiente
                                                              //  2: 4/6,
                                                              //  3: 4/7,
                                                              //  4: 4/8]
#define LORA_PREAMBLE_LENGTH                        8         // Same for Tx and Rx -> LARGO DEL PREAMBULO, el preambulo es una "señal de aviso", para que el detector detecte que llega un paquete
                                                              //                       que esta llegando, 8 simbolos suele ser el estandar.
#define LORA_SYMBOL_TIMEOUT                         0         // Symbols -> SYMBOL TIMEOUT, define cuanto tiempo se espera para detectar simbolos LoRa
#define LORA_FIX_LENGTH_PAYLOAD_ON                  false     // -> LONGITUD FIJA O VARIABLE DEL PAYLOAD. F=variable, T=fija.
#define LORA_IQ_INVERSION_ON                        false     // ->INVERSION DE IQ, controla si la radio usa inversion de fase IQ


#define RX_TIMEOUT_VALUE                            1000      // ->TIEMPO DE TIMEOUT, si no se recibe nada durante el tiempo dado, se considera que la recepcion fallo o termino
#define BUFFER_SIZE                                 160        // -> TAMAÑO DEL BUFFER IMPORTANTE; ACA SE DEFINE EL TAMAÑO DEL PAQUETE QUE ENVIAMOS!! Corregir en funcion de que tanto terminemos mandando
                                                              // Hablando con Claude, estimo que para lo que vamos a mandar alrededor de 160 (inlcluyo un margen de seguridad) deberia bastar.

char txpacket[BUFFER_SIZE];
char rxpacket[BUFFER_SIZE];

double txNumber;

bool lora_idle = true;

static RadioEvents_t RadioEvents;
void OnTxDone(void);
void OnTxTimeout(void);

void setup() {
    Serial1.begin(PI_BAUD, SERIAL_8N1, PI_RX_PIN, -1);   // solo RX, sin pin de TX
    Mcu.begin(HELTEC_BOARD, SLOW_CLK_TPYE);


    //Aca es donde lo definimos si es transmisor o receptor, en este caso es transmisor:

    txNumber = 0;

    RadioEvents.TxDone = OnTxDone;
    RadioEvents.TxTimeout = OnTxTimeout;

    Radio.Init(&RadioEvents);
    Radio.SetChannel(RF_FREQUENCY);
    Radio.SetTxConfig(MODEM_LORA, TX_OUTPUT_POWER, 0, LORA_BANDWIDTH,
                       LORA_SPREADING_FACTOR, LORA_CODINGRATE,
                       LORA_PREAMBLE_LENGTH, LORA_FIX_LENGTH_PAYLOAD_ON,
                       true, 0, 0, LORA_IQ_INVERSION_ON, 3000);

    //INICIALIZACION DEL BMP280
    Wire.begin(SDA_PIN,SCL_PIN);
    unsigned status;
    status = bmp.begin(0x76);
    if (!status) {
        // BMP280 no encontrado (revisar cableado o direccion 0x76/0x77). Sin monitor serie, solo se queda frenado.
        while (1) delay(10);
    }
    bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,     /* Operating Mode. */
                  Adafruit_BMP280::SAMPLING_X2,     /* Temp. oversampling */
                  Adafruit_BMP280::SAMPLING_X16,    /* Pressure oversampling */
                  Adafruit_BMP280::FILTER_X16,      /* Filtering. */
                  Adafruit_BMP280::STANDBY_MS_500); /* Standby time. */
    
    //inicializacion de los mq
    analogReadResolution(12);                   
  
    analogSetPinAttenuation(MQ4_PIN, ADC_11db); // Rango hasta ~3.3V para MQ-4
    pinMode(MQ4_PIN, INPUT);

    analogSetPinAttenuation(MQ7_PIN, ADC_11db); // Rango hasta ~3.3V para MQ-7
    pinMode(MQ7_PIN, INPUT);
}


void loop()
{
  // Esperamos entre medidas (500 ms), leyendo mientras tanto lo que mande la Pi
  uint32_t tWait = millis();
  while (millis() - tWait < 500) {
    pollPi();
    delay(5);
  }

  //LECTURAS DEL BMP280
  float t = bmp.readTemperature();
  float p = bmp.readPressure();
  float alt = bmp.readAltitude(1011.9);//->IMPORTANTE, AJUSTAR EN FUNCION DE NUESTAS CONDICIONES, presion al nivel del mar

  //pasamos la presion a hpa
  p = p / 100.0F;


  // --- LECTURAS DEL MQ-4 (Metano) ---
  int adc_mq4 = analogRead(MQ4_PIN);
  float volt_mq4 = (adc_mq4 * 3.3) / 4095.0;

  // --- LECTURAS DEL MQ-7 (Monóxido de Carbono) ---
  int adc_mq7 = analogRead(MQ7_PIN);
  float volt_mq7 = (adc_mq7 * 3.3) / 4095.0;

  if (lora_idle == true)
  {
    txNumber += 0.01;

    //Mandamos los datos del bmp280
    // Los campos de GPS van al final para no romper el parseo del dashboard (que busca T/P/A con regex).
    // Si no hay dato fresco de la Pi se manda LAT: NA, LON: NA.
    if (piGpsFresh()) {
      snprintf(txpacket, BUFFER_SIZE, "T: %.2f C, P: %.2f hPa, A: %.2f m, MQ4: %d, MQ7: %d, LAT: %.6f, LON: %.6f",
               t, p, alt, adc_mq4, adc_mq7, piGps.lat, piGps.lon);
    } else {
      snprintf(txpacket, BUFFER_SIZE, "T: %.2f C, P: %.2f hPa, A: %.2f m, MQ4: %d, MQ7: %d, LAT: NA, LON: NA",
               t, p, alt, adc_mq4, adc_mq7);
    }

    Radio.Send((uint8_t *)txpacket, strlen(txpacket)); // send the package out
    lora_idle = false;
  }
  Radio.IrqProcess();
}

void OnTxDone(void)
{
    lora_idle = true;
}

void OnTxTimeout(void)
{
    Radio.Sleep();
    lora_idle = true;
}
