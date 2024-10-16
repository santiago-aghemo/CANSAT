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
  Serial.print(raw_adc);
  Serial.print("    Tension: ");
  Serial.println(value_adc);

  delay(MQ_DELAY);
}
