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


#define RX_TIMEOUT_VALUE                            0      // ->TIEMPO DE TIMEOUT, si no se recibe nada durante el tiempo dado, se considera que la recepcion fallo o termino
#define BUFFER_SIZE                                 160        // -> TAMAÑO DEL BUFFER IMPORTANTE; ACA SE DEFINE EL TAMAÑO DEL PAQUETE QUE ENVIAMOS!! Corregir en funcion de que tanto terminemos mandando
                                                              // Hablando con Claude, estimo que para lo que vamos a mandar alrededor de 160 (inlcluyo un margen de seguridad) deberia bastar.

char rxpacket[BUFFER_SIZE];

bool lora_idle = true;

static RadioEvents_t RadioEvents;
void OnRxDone(uint8_t *payload, uint16_t size, int16_t rssi, int8_t snr);
void OnRxTimeout(void);
void OnRxError(void);


void setup() {
    Serial.begin(115200);
    Mcu.begin(HELTEC_BOARD, SLOW_CLK_TPYE);


    //Aca es donde lo definimos si es transmisor o receptor, en este caso es receptor:


    RadioEvents.RxDone = OnRxDone;
    RadioEvents.RxTimeout = OnRxTimeout;
    RadioEvents.RxError = OnRxError;

    Radio.Init(&RadioEvents);
    Radio.SetChannel(RF_FREQUENCY);
    Radio.SetRxConfig(MODEM_LORA, LORA_BANDWIDTH, LORA_SPREADING_FACTOR,
                       LORA_CODINGRATE, 0, LORA_PREAMBLE_LENGTH,
                       LORA_SYMBOL_TIMEOUT, LORA_FIX_LENGTH_PAYLOAD_ON,
                       0, true, 0, 0, LORA_IQ_INVERSION_ON, true);
}


void loop()
{
  if(lora_idle){
    Radio.Rx(0); //indica el timeout. 0=escucha para siempre.
    lora_idle = false;
  }
  Radio.IrqProcess();
}


//rssi= fuerza de señal; snr= signal to noise ratio, cuanto mas alto, mejor
void OnRxDone(uint8_t *payload, uint16_t size, int16_t rssi, int8_t snr)
{
    Radio.Sleep();
    memcpy(rxpacket, payload, size);//copiamos el payload recibido en el buffer rxpacket, ya que payload es un puntero a memoria que se borra al salir de la funcion
    rxpacket[size] = '\0'; // importante para tratarlo como string. C necesita un caracter nulo al final de los strings para saber donde termina el string. si no lo ponemos, puede que el string se "desborde" y lea basura de memoria.

    Serial.printf("\r\nreceived packet \"%s\" with rssi %d , length %d\r\n", rxpacket, rssi, size);

    lora_idle = true;
}

void OnRxTimeout(void) //se llama en caso de timeout
{
    Serial.println("RX Timeout......");
    lora_idle = true;
}

void OnRxError(void) //se llama en caso de error
{
    Serial.println("RX Error......");
    lora_idle = true;
}