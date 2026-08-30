#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <SSD1306.h>
 
//Deixe esta linha descomentada para compilar o Master
//Comente ou remova para compilar o Slave
// #define MASTER
 
#define SCK 5   // GPIO5  SCK
#define MISO 19 // GPIO19 MISO
#define MOSI 27 // GPIO27 MOSI
#define SS 18   // GPIO18 CS
#define RST 14  // GPIO14 RESET
#define DI00 26 // GPIO26 IRQ(Interrupt Request)
 
#define BAND 433E6 //Frequência do radio - exemplo : 433E6, 868E6, 915E6
 
//Constante para informar ao Slave que queremos os dados
const String GETDATA = "getdata";
//Constante que o Slave retorna junto com os dados para o Master
const String SETDATA = "setdata=";
 
//Variável para controlar o display
SSD1306 display(0x3c, 4, 15);

LoRaSendReceive.ino - setupDisplay

In this first setup, we will deal with the configuration of the display.

void setupDisplay(){
  //O estado do GPIO16 é utilizado para controlar o display OLED
  pinMode(16, OUTPUT);
  //Reseta as configurações do display OLED
  digitalWrite(16, LOW);
  //Para o OLED permanecer ligado, o GPIO16 deve permanecer HIGH
  //Deve estar em HIGH antes de chamar o display.init() e fazer as demais configurações,
  //não inverta a ordem
  digitalWrite(16, HIGH);
 
  //Configurações do display
  display.init();
  display.flipScreenVertically();
  display.setFont(ArialMT_Plain_10);
  display.setTextAlignment(TEXT_ALIGN_LEFT);
}