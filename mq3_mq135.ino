const int MQ_PIN = A0;
const int MQ_DELAY = 2000;

void setup()
{
  Serial.begin(9600);
  //aca agregar un delay determinado segun el tiempo que se quiera dejar precalentar
}

void loop() 
{
  int raw_adc = analogRead(MQ_PIN);
  float value_adc = raw_adc * (5.0 / 1023.0);

  Serial.print("PPM:  ");
  Serial.print(raw_adc, DEC);
  Serial.print("    Tension: ");//poder ver la tension esta bueno porque con eso podemos ver si esta calentando el sensor o no. (Si lo acabamos de prender se empezara a calentar con una tension de  5V y lentamente va bajando hasta llegar al destado de reposo con una  tension  >1V) 
  Serial.println(value_adc);

  delay(MQ_DELAY);
}
