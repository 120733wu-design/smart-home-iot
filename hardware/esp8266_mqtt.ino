/*
 * Smart Home ESP8266 Firmware
 * Hardware: ESP8266 + DHT11 + BH1750 + OLED + Relay + Buzzer
 *
 * MQTT Topic 规范 (四段式):
 *   上报传感器: device/<DEVICE_KEY>/sensor/temperature
 *               device/<DEVICE_KEY>/sensor/humidity
 *               device/<DEVICE_KEY>/sensor/light
 *   心跳状态:   device/<DEVICE_KEY>/status
 *   告警:       device/<DEVICE_KEY>/alert
 *   控制应答:   device/<DEVICE_KEY>/control/ack
 *
 * MQTT Broker:
 *   阿里云公网: 182.92.86.89:1883 (ESP/硬件使用)
 *   本地开发:   127.0.0.1:1883   (本地Flask后端)
 */
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <BH1750.h>
const char *WIFI_SSID = "yiwu";
const char *WIFI_PASS = "1207yiwu";
// MQTT Broker: ESP硬件连阿里云公网EMQX 182.92.86.89
// Flask后端在宝塔上应连同一个Broker；本地开发可改为127.0.0.1
const char *MQTT_HOST = "182.92.86.89";
const int MQTT_PORT = 1883;
// 设备唯一标识，用于MQTT Topic: device/<DEVICE_KEY>/...
const char *DEVICE_KEY = "esp8266-001";
#define DHT_PIN 5 #define DHT_TYPE DHT11
#define BUZZER_PIN 4 #define RELAY1_PIN 16 #define RELAY2_PIN 3
WiFiClient espClient; PubSubClient mqttClient(espClient);
DHT dht(DHT_PIN, DHT_TYPE); BH1750 lightMeter;
float temp=0, humi=0; uint16_t lux=0; bool r1State=false, r2State=false;
unsigned long lastRead=0, lastHB=0, lastDisp=0;
const unsigned long READ_INT=10000, HB_INT=60000, DISP_INT=5000;
void setup() {
    Serial.begin(115200); pinMode(BUZZER_PIN,OUTPUT); pinMode(RELAY1_PIN,OUTPUT); pinMode(RELAY2_PIN,OUTPUT);
    digitalWrite(RELAY1_PIN,LOW); digitalWrite(RELAY2_PIN,LOW);
    Wire.begin(4,5); dht.begin(); lightMeter.begin(); setupWiFi();
    mqttClient.setServer(MQTT_HOST,MQTT_PORT); mqttClient.setCallback(callback);
    mqttClient.setBufferSize(512);
}
void loop() {
    if(!mqttClient.connected()) reconnectMQTT(); mqttClient.loop();
    unsigned long now=millis();
    if(now-lastRead>=READ_INT){lastRead=now;readSensors();publishData();checkAlerts();}
    if(now-lastHB>=HB_INT){lastHB=now;publishHeartbeat();}
    yield();
}
void setupWiFi(){
    WiFi.begin(WIFI_SSID,WIFI_PASS);
    int a=0; while(WiFi.status()!=WL_CONNECTED&&a<40){delay(500);a++;}
}
void reconnectMQTT(){
    while(!mqttClient.connected()){
        String cid=String("ESP-")+DEVICE_KEY+"-"+String(random(0xffff),HEX);
        if(mqttClient.connect(cid.c_str(),"","",(String("device/")+DEVICE_KEY+"/status").c_str(),1,true,"{\"status\":\"offline\"}")){
            mqttClient.subscribe((String("device/")+DEVICE_KEY+"/control").c_str(),1);publishHeartbeat();break;
        } delay(5000);
    }
}
void callback(char* topic, byte* payload, unsigned int length){
    String msg; for(unsigned int i=0;i<length;i++) msg+=(char)payload[i];
    DynamicJsonDocument doc(256);
    if(deserializeJson(doc,msg)) return;
    String cmd=doc["command"]|"";
    int cmdId=doc["command_id"]|0;
    bool ok=false; String ack;
    if(cmd=="relay1_on"){digitalWrite(RELAY1_PIN,HIGH);r1State=true;ok=true;ack="Relay1 ON";}
    if(cmd=="relay1_off"){digitalWrite(RELAY1_PIN,LOW);r1State=false;ok=true;ack="Relay1 OFF";}
    if(cmd=="relay2_on"){digitalWrite(RELAY2_PIN,HIGH);r2State=true;ok=true;ack="Relay2 ON";}
    if(cmd=="relay2_off"){digitalWrite(RELAY2_PIN,LOW);r2State=false;ok=true;ack="Relay2 OFF";}
    DynamicJsonDocument a(256); a["command_id"]=cmdId; a["command"]=cmd; a["status"]=ok?"acknowledged":"failed"; a["message"]=ack;
    String out; serializeJson(a,out); mqttClient.publish((String("device/")+DEVICE_KEY+"/control/ack").c_str(),out.c_str(),true);
}
void readSensors(){
    float h=dht.readHumidity(); float t=dht.readTemperature();
    if(!isnan(h)&&!isnan(t)){humi=h; temp=t;}
    lux=lightMeter.readLightLevel();
}
void publishData(){
    mqttClient.publish((String("device/")+DEVICE_KEY+"/sensor/temperature").c_str(),String(temp).c_str(),true);
    mqttClient.publish((String("device/")+DEVICE_KEY+"/sensor/humidity").c_str(),String(humi).c_str(),true);
    mqttClient.publish((String("device/")+DEVICE_KEY+"/sensor/light").c_str(),String(lux).c_str(),true);
}
void checkAlerts(){
    if(temp>35.0||temp<5.0){
        digitalWrite(BUZZER_PIN,HIGH);
        DynamicJsonDocument d(256); d["type"]="threshold"; d["severity"]=temp>35.0?"critical":"warning"; d["message"]=String("Temp: ")+temp+"C"; d["device_key"]=DEVICE_KEY;
        String out; serializeJson(d,out); mqttClient.publish((String("device/")+DEVICE_KEY+"/alert").c_str(),out.c_str(),true);
    } else digitalWrite(BUZZER_PIN,LOW);
}
void publishHeartbeat(){
    DynamicJsonDocument d(256); d["status"]="online"; d["device_key"]=DEVICE_KEY; d["ip"]=WiFi.localIP().toString(); d["rssi"]=WiFi.RSSI();
    String out; serializeJson(d,out); mqttClient.publish((String("device/")+DEVICE_KEY+"/status").c_str(),out.c_str(),true);
}
