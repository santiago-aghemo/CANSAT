#include <Wire.h>
#include <BMP180I2C.h>

// Correccion de la presion segun la altitud real del pueblo
// El pueblo esta ubicado a 823 msnm, el gps nos indica 815 msmn
// El promedio de los datos confiables es 819 msnm
// El sensor nos entregaba una altura de 698 msnm y una presion de 932.16 mbar
// Hay que aplicar una diferencia de +121 msnm
// Ecuacion de corrección:
// P_a_medir = P_o * sqrt(1-819m/44330, 1/5.255)
// La presion que deberiamos medir es de 918.667 mbar
// La diferencia la cargamos a la variable de correccion de presion

#define CORRECCION_PRESION 2 // milibares

float bmp_pres_ref; // presion del punto inicial para h=0;
float bmp_pres_sea = 1013.25;
// create an BMP180 object using the I2C interface
#define BMP_180_I2C_ADDRESS 0x77 // del BMP180
BMP180I2C bmp180(BMP_180_I2C_ADDRESS);

/**
 * @brief Inicializa el sensor BMP180
 */
void bmp180_setup()
{
    // begin() initializes the interface, checks the sensor ID and reads the calibration parameters.
    if (!bmp180.begin())
    {
        Serial.println("Error al iniciar el BMP180");
        while (1)
            ;
    }

    // reset sensor to default parameters.
    bmp180.resetToDefaults();

    // enable ultra high resolution mode for pressure measurements
    bmp180.setSamplingMode(BMP180MI::MODE_UHR);

    // medimos temperatura primero para que nos habilite el sensor a medir presión
    // do 3 full measurement cycles (temperature and pressure) to initialize the sensor
    for (int i = 0; i < 3; i++)
    {
        leer_temp_bmp180();
        leer_presion_bmp180();
    }
    leer_temp_bmp180();
    bmp_pres_ref = leer_presion_bmp180(); // Presion del punto inicial para h=0
}

/**
 * @brief Lee la presion del sensor BMP180 y la devuelve en milibares
 * 
 * @return float  Presion en milibares
 */
float leer_presion_bmp180()
{
    // start a pressure measurement. pressure measurements depend on temperature measurement, you should only start a pressure
    // measurement immediately after a temperature measurement.
    if (!bmp180.measurePressure())
    {
        Serial.println("could not start perssure measurement, is a measurement already running?");
        return -1;
    }

    // wait for the measurement to finish. proceed as soon as hasValue() returned true.
    do
    {
        delay(100);
    } while (!bmp180.hasValue());

    return (bmp180.getPressure() / 100 + CORRECCION_PRESION) ; // devuelve la presion en milibares
}

/**
 * @brief Lee la temperatura del sensor BMP180 y la devuelve en grados centigrados
 * 
 * @return float Temperatura en grados centigrados
 */
float leer_temp_bmp180()
{
    // start a temperature measurement
    if (!bmp180.measureTemperature())
    {
        Serial.println("could not start temperature measurement, is a measurement already running?");
        return -500;
    }

    // wait for the measurement to finish. proceed as soon as hasValue() returned true.
    do
    {
        delay(100);
    } while (!bmp180.hasValue());

    return bmp180.getTemperature();
}

/**
 * @brief Lee la altura absoluta a partir de la presion
 * 
 * @param presion Presion en milibares
 * @return float Altitud en metros
 */
float leer_altura_abs_bmp180()
{
    return calcular_altitud(data.bmp_pres, bmp_pres_sea);
}

/**
 * @brief Lee la altura relativa a la altura de referencia
 * 
 * @param presion Presion en milibares
 * @return float Altitud en metros
 */
float leer_altura_rel_bmp180(float presion)
{
    return calcular_altitud(presion, bmp_pres_ref);
}

/**
 * @brief Calcula la altitud en metros a partir de la presion y la presion de referencia
 * 
 * @param P Presion en milibares
 * @param P0 Presion de referencia en milibares
 * @return float Altitud en metros
 */
float calcular_altitud(float P, float P0)
{
    // if P equals -1, sensor threw an error
    if (P == -1)
    {
        return -1;
    }

    // Ecuacion:
    // h = 44330 * (1 - (P / P0) ^ (1 / 5.255))
    // Given a pressure measurement P (mb) and the pressure at a baseline P0 (mb),
    // return altitude (meters) above baseline.
    return (44330.0 * (1 - pow(P / P0, 1 / 5.255)));
}