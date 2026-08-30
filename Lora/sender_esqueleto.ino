/* Heltec Automation send communication test example
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

#include "LoRaWan_APP.h"
#include "Arduino.h"




 /*
 NOTA DE SANTI:
 este codigo es el "esqueleto" de lo que usamos el año pasado. Agarre el codigo que incluia en este codigo todo el procesamiento y toma de datos. deberia investigar si esta implementacion es ideal. segun lei con el chat
 usa, digamos, "lo que viene incluido" en la placa para usar el lora, y no usa librerias externas para esta tarea como hacian los ejemplos que me tiro claude. voy a intentar hacer una copia de este archivo (voy a dejar 
 este esqueleto suelto por las dudas) con el bmp280 implementado. IMPORANTE, VER SI ESTA IMPLEMENTACION ES LA MAS EFICIENTE. tambien deberia de ver de hacer anotacioens en este documento para tener explicacion de lo que
 hace cada cosa

 notar que tambien hay comentarios que hizo claude
 */



 // ==========================================================
// ACA VAN LOS INCLUDES Y OBJETOS DE TUS SENSORES
// Ejemplo:
// #include <DHT.h>
// #define DHTPIN 2
// #define DHTTYPE DHT11
// DHT dht(DHTPIN, DHTTYPE);
// ==========================================================


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
#define BUFFER_SIZE                                 60

char txpacket[BUFFER_SIZE];
char rxpacket[BUFFER_SIZE];

double txNumber;

bool lora_idle = true;

static RadioEvents_t RadioEvents;
void OnTxDone(void);
void OnTxTimeout(void);

void setup() {
    Serial.begin(115200);
    Mcu.begin(HELTEC_BOARD, SLOW_CLK_TPYE);

    txNumber = 0;

    RadioEvents.TxDone = OnTxDone;
    RadioEvents.TxTimeout = OnTxTimeout;

    Radio.Init(&RadioEvents);
    Radio.SetChannel(RF_FREQUENCY);
    Radio.SetTxConfig(MODEM_LORA, TX_OUTPUT_POWER, 0, LORA_BANDWIDTH,
                       LORA_SPREADING_FACTOR, LORA_CODINGRATE,
                       LORA_PREAMBLE_LENGTH, LORA_FIX_LENGTH_PAYLOAD_ON,
                       true, 0, 0, LORA_IQ_INVERSION_ON, 3000);

    // ==========================================================
    // ACA VA LA INICIALIZACION DE TUS SENSORES
    // Ejemplo:
    // dht.begin();
    //
    // if (pressure.begin()) {
    //   Serial.println("BMP180 init success");
    // } else {
    //   Serial.println("BMP180 init fail");
    //   while (1);
    // }
    // ==========================================================
}


void loop()
{
  // Esperamos entre medidas
  delay(5000);

  // ==========================================================
  // ACA VAN TUS LECTURAS DE SENSORES
  // Ejemplo:
  // float h = dht.readHumidity();
  // float t = dht.readTemperature();
  // int raw_adc = analogRead(MQ_PIN);
  // ==========================================================

  if (lora_idle == true)
  {
    delay(1000);
    txNumber += 0.01;

    // ==========================================================
    // ACA ARMAS EL PAQUETE CON TUS DATOS
    // Ejemplo:
    // sprintf(txpacket, "Temperatura: %.2f C, Humedad: %.2f%%", t, h);
    //
    // Por ahora manda un contador de prueba:
    sprintf(txpacket, "Paquete de prueba #%.2f", txNumber);
    // ==========================================================

    Serial.printf("\r\nsending packet \"%s\" , length %d\r\n", txpacket, strlen(txpacket));

    Radio.Send((uint8_t *)txpacket, strlen(txpacket)); // send the package out
    lora_idle = false;
  }
  Radio.IrqProcess();
}

void OnTxDone(void)
{
    Serial.println("TX done......");
    lora_idle = true;
}

void OnTxTimeout(void)
{
    Radio.Sleep();
    Serial.println("TX Timeout......");
    lora_idle = true;
}
