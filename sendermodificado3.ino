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



#include <MQ135.h>
#include "DHT.h"

// Uncomment whatever type you're using!
#define DHTTYPE DHT11   // DHT 11
//#define DHTTYPE DHT22   // DHT 22  (AM2302), AM2321
//#define DHTTYPE DHT21   // DHT 21 (AM2301)
const int DHTPin = 23;     // what digital pin we're connected to
DHT dht(DHTPin, DHTTYPE);

#define PIN_MQ135 37 // Change to the correct pin if needed
MQ135 mq135_sensor(PIN_MQ135);





#include "LoRaWan_APP.h"
#include "Arduino.h"


#define RF_FREQUENCY                                915000000 // Hz

#define TX_OUTPUT_POWER                             5        // dBm

#define LORA_BANDWIDTH                              0         // [0: 125 kHz,
                                                              //  1: 250 kHz,
                                                              //  2: 500 kHz,
                                                              //  3: Reserved]
#define LORA_SPREADING_FACTOR                       7         // [SF7..SF12]
#define LORA_CODINGRATE                             1         // [1: 4/5,
                                                              //  2: 4/6,
                                                              //  3: 4/7,
                                                              //  4: 4/8]
#define LORA_PREAMBLE_LENGTH                        8         // Same for Tx and Rx
#define LORA_SYMBOL_TIMEOUT                         0         // Symbols
#define LORA_FIX_LENGTH_PAYLOAD_ON                  false
#define LORA_IQ_INVERSION_ON                        false


#define RX_TIMEOUT_VALUE                            1000
#define BUFFER_SIZE                                 30 // Define the payload size here

char txpacket[BUFFER_SIZE];
char rxpacket[BUFFER_SIZE];

double txNumber;

bool lora_idle=true;

static RadioEvents_t RadioEvents;
void OnTxDone( void );
void OnTxTimeout( void );

void setup() {
    Serial.begin(115200);
    Mcu.begin(HELTEC_BOARD,SLOW_CLK_TPYE);
	
    txNumber=0;

    RadioEvents.TxDone = OnTxDone;
    RadioEvents.TxTimeout = OnTxTimeout;
    
    Radio.Init( &RadioEvents );
    Radio.SetChannel( RF_FREQUENCY );
    Radio.SetTxConfig( MODEM_LORA, TX_OUTPUT_POWER, 0, LORA_BANDWIDTH,
                                   LORA_SPREADING_FACTOR, LORA_CODINGRATE,
                                   LORA_PREAMBLE_LENGTH, LORA_FIX_LENGTH_PAYLOAD_ON,
                                   true, 0, 0, LORA_IQ_INVERSION_ON, 3000 ); 
   
   dht.begin();
   }



void loop()
{
  
  //Trabajo conjunto DHT11-MQ135
  float temperature_MQ135 = dht.readTemperature(); // Assume current temperature
  float humidity_MQ135 = dht.readHumidity();    // Assume current humidity



  //Lectura y refinamiento de datos MQ135
  float rzero = mq135_sensor.getRZero();
  float correctedRZero = mq135_sensor.getCorrectedRZero(temperature_MQ135, humidity_MQ135); // Corrected syntax
  float resistance = mq135_sensor.getResistance();
  float ppm = mq135_sensor.getPPM();
  float correctedPPM = mq135_sensor.getCorrectedPPM(temperature_MQ135, humidity_MQ135);



  
  //Lectura y refinamiento de datos MQ3
  long long adc_MQ = analogRead(38); //Lemos la salida analógica  del MQ3
  long double voltaje = adc_MQ * (5.0 / 1023.0); //Convertimos la lectura en un valor de voltaje
  long double Rs=1000*((5-voltaje)/voltaje);  //Calculamos Rs con un RL de 1k
  double alcohol=0.4091*pow(Rs/5463, -1.497); // calculamos la concentración  de alcohol con la ecuación obtenida.


  //Lectura y refinamiento de datos DHT11
  int h = dht.readHumidity();
  float t = dht.readTemperature();
  // Reading temperature or humidity takes about 250 milliseconds!
  


	if(lora_idle == true)
	{
    delay(1000);
		txNumber += 0.01;


		//sprintf(txpacket,"%.2f,%.2f,%.2f,%.2f ppm, %.2f cppm, %d, %.2f, Rs: %.2f, %.2f mg/L,%d%%, %.2f *C", rzero, correctedRZero, resistance, ppm, correctedPPM,adc_MQ,voltaje,Rs,alcohol,h,t);  //start a package
    // // Primer valor
    //
    //
    //
    //
    //
    //
    Serial.printf("\r\n----------ENVIANDO PAQUETE----------\n");
    Serial.printf("\r\nDHT11: \n");
    Serial.printf("Humidity: %d%% \n", h);
    Serial.printf("Temperature: %.2f *C \n", t);
    Serial.printf("\r\nMQ135: \n");
    Serial.printf("RZero: %.2f \n", rzero);
    Serial.printf("Corrected RZero: %.2f \n", correctedRZero);
    Serial.printf("Resistance: %.2f \n", resistance);
    Serial.printf("PPM: %.2f ppm \n", ppm);
    Serial.printf("Corrected PPM: %.2f ppm \n", correctedPPM);
    Serial.printf("\r\nMQ3: \n");
    Serial.printf("Adc: %d \n", adc_MQ);
    Serial.printf("Voltaje: %.2f \n", voltaje);
    Serial.printf("Rs: %.2f \n", Rs);
    Serial.printf("Alcohol: %.2f mg/L \n", alcohol);
    Serial.printf("----------FIN DEL PAQUETE-----------\n");



    //humedad
    sprintf(txpacket, "Humidity: %d%%, ", h);
    
		//Serial.printf("\r\nsending packet \"%s\" , length %d\r\n",txpacket, strlen(txpacket));

    //send the package out
		Radio.Send( (uint8_t *)txpacket, strlen(txpacket) );

    //temperatura
    sprintf(txpacket, "Temperature: %.2f *C", t);
    
    //Serial.printf("\r\nsending packet \"%s\" , length %d\r\n",txpacket, strlen(txpacket));

    //send the package out
		Radio.Send( (uint8_t *)txpacket, strlen(txpacket) );


    //ppm con correccion de dht
    sprintf(txpacket, "Corrected PPM: %.2f ppm, ", correctedPPM);

    //Serial.printf("\r\nsending packet \"%s\" , length %d\r\n",txpacket, strlen(txpacket));

    //send the package out
		Radio.Send( (uint8_t *)txpacket, strlen(txpacket) );


    //alcohol
    sprintf(txpacket, "alcohol: %.2f mg/L, ", alcohol);

    //Serial.printf("\r\nsending packet \"%s\" , length %d\r\n",txpacket, strlen(txpacket));

    //send the package out
		Radio.Send( (uint8_t *)txpacket, strlen(txpacket) );

    //rzero
    sprintf(txpacket, "MQ135 RZero: %.2f, ", rzero);

    //Serial.printf("\r\nsending packet \"%s\" , length %d\r\n",txpacket, strlen(txpacket));

    //send the package out
		Radio.Send( (uint8_t *)txpacket, strlen(txpacket) );

    //correctedrzero
    sprintf(txpacket, "Corrected RZero: %.2f, ", correctedRZero);

    //Serial.printf("\r\nsending packet \"%s\" , length %d\r\n",txpacket, strlen(txpacket));

    //send the package out
		Radio.Send( (uint8_t *)txpacket, strlen(txpacket) );

    //resistance
    sprintf(txpacket, "Resistance: %.2f, ", resistance);

    //Serial.printf("\r\nsending packet \"%s\" , length %d\r\n",txpacket, strlen(txpacket));

    //send the package out
		Radio.Send( (uint8_t *)txpacket, strlen(txpacket) );

    //ppm
    sprintf(txpacket, "PPM: %.2f ppm, ", ppm);

    //Serial.printf("\r\nsending packet \"%s\" , length %d\r\n",txpacket, strlen(txpacket));

    //send the package out
		Radio.Send( (uint8_t *)txpacket, strlen(txpacket) );

    //adc
    sprintf(txpacket, "adc: %d, ", adc_MQ);

    //Serial.printf("\r\nsending packet \"%s\" , length %d\r\n",txpacket, strlen(txpacket));

    //send the package out
		Radio.Send( (uint8_t *)txpacket, strlen(txpacket) );

    //voltaje
    sprintf(txpacket, "voltaje: %.2f, ", voltaje);

    //Serial.printf("\r\nsending packet \"%s\" , length %d\r\n",txpacket, strlen(txpacket));

    //send the package out
		Radio.Send( (uint8_t *)txpacket, strlen(txpacket) );

    //rs
    sprintf(txpacket, "Rs: %.2f, ", Rs);

    //Serial.printf("\r\nsending packet \"%s\" , length %d\r\n",txpacket, strlen(txpacket));

    //send the package out
		Radio.Send( (uint8_t *)txpacket, strlen(txpacket) );
     	
    lora_idle = false;
	}
  Radio.IrqProcess( );

  delay(100);
}

void OnTxDone( void )
{
	Serial.println("TX done......");
	lora_idle = true;
}

void OnTxTimeout( void )
{
    Radio.Sleep( );
    Serial.println("TX Timeout......");
    lora_idle = true;
}