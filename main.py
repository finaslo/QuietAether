from tkinter import *
import tkinter.font as tkFont
import paho.mqtt.client as mqtt
import pyglet
import math
import threading
import wave
from piper import PiperVoice
import playsound3
import sys
import logging
import json

#Класс полноэкранного окна, для удобства
class FullscreenWindow:
    #Инициализация окна
    def __init__(self):
        self.tk = Tk()
        self.tk.title = "Quiet Aether"
        self.tk.attributes("-fullscreen", True)
        self.tk.bind("<Escape>", self.die)
        self.width = self.tk.winfo_screenwidth()
        self.height = self.tk.winfo_screenheight()

    #Функция для закрытия окна
    def die(self, event):
        self.tk.destroy()

#Параллельный процесс синтезации речи
def startVoiceSynthesisThread(text : str, voice : PiperVoice):

    #Вывод сообщения о идущем процессе синтезации
    labelSynthInProgress.config(text="Синтез в процессе...")

    #Запуск синтезации
    with wave.open("synthLastOutput.wav", "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)

    #По окончании синтезации
    labelSynthInProgress.config(text="")
    playsound3.playsound("synthLastOutput.wav")

#Функция подписки на топик при подключении к брокеру
def on_connect(client, userdata, flags, reason_code, properties):
    logging.info(f"Подключился к MQTT брокеру с кодом {reason_code}")
    logging.info(f"Подписываюсь на MQTT топик {config["MQTTSubscriptionPrefix"]}/{machinistID}")
    client.subscribe(f"{config["MQTTSubscriptionPrefix"]}/{machinistID}")

#Обработка полученного сообщения MQTT
def on_message(client, userdata, msg):

    #Вывод текста сообщения и логирование
    labelMain.config(text=msg.payload.decode('utf-8'))
    logging.info(f"Получено сообщение от {msg.topic}: \"{msg.payload.decode('utf-8')}\"")

    #Запуск процесса синтезации
    t = threading.Thread(target=startVoiceSynthesisThread, args=(msg.payload.decode('utf-8'), voice))
    t.daemon = True
    t.start()

#Загрузка файла конфигурации
with open("config.json", 'r') as configFile:
    config = json.load(configFile)

#Инициализация окна
window = FullscreenWindow()

#Инициализация логирования
logging.basicConfig(
    filename='messages.log',         
    filemode='a',              
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

'''
Запуск параллельного процесса проигрывания звука запуска 
Необходимо по причине того, что Raspberry Pi обрезает первые полсекунды аудио после запуска. 
Поэтому, что бы не обрезать сообщение, был введен звук запуска. 
При нежелании слышать звуки, можно в файле конфигурации указать пустой аудио-файл
'''
playSoundWhileLoading = threading.Thread(target=playsound3.playsound, args=(config["StartUpSound"],))
playSoundWhileLoading.daemon = True
playSoundWhileLoading.start()

#Загрузка ИИ TTS
voice = PiperVoice.load(config["Synth"])

#Загрузка пользовательского шрифта
if config["Font"] != "":
    pyglet.font.add_file(config["Font"])

#Инициализация блоков текста
labelMain = Label(window.tk, text="Привет, машинист!", font=(config["FontName"], math.ceil(window.height/17)), wraplength=window.width)
labelMain.pack(expand=True, anchor='center')
labelSynthInProgress = Label(window.tk, text="", font=(config["FontName"], math.ceil(window.height/17)))
labelSynthInProgress.pack(anchor='se')

#ID машиниста
machinistID = config["machinistID"]

#Подключение к MQTT
mqttClient = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttClient.on_connect = on_connect
mqttClient.on_message = on_message
mqttClient.connect_async(config["MQTTBroker"], config["MQTTPort"], 60)

#Повторное расширение окна до полного экрана, из-за странного поведения Raspberry Pi
window.tk.after(1000, window.tk.wm_attributes, '-fullscreen', 'true')
logging.info("Программа запущена")

#Основной цикл
mqttClient.loop_start()

window.tk.mainloop()
    
mqttClient.loop_stop()