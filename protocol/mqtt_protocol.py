import json
import logging
import paho.mqtt.client as paho
from paho.mqtt.enums import CallbackAPIVersion

logger = logging.getLogger(__name__)

def _on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.debug("成功连接到 MQTT Broker!")
    else:
        logger.debug("连接失败，返回码=" + str(rc))

def _on_disconnect(client, userdata, flags, rc, properties=None):
    logger.debug("与 Broker 断开连接，返回码=" + str(rc))

class MqttProtocol:
    def __init__(self, mqtt: dict):
        self.mqtt = mqtt
        self.client = paho.Client(
            callback_api_version = CallbackAPIVersion.VERSION2,
            client_id=mqtt['client_id'],
            reconnect_on_failure=True,
            protocol=paho.MQTTv5)
        self.client.username_pw_set(mqtt['username'], mqtt['password'])
        self.client.connect(mqtt['endpoint'], 1883)
        self.client.loop_start()
        self.client.on_connect = _on_connect
        self.client.on_disconnect = _on_disconnect
        # self.client.on_message = _on_message

    def send_hello(self):
        message = {
            "type": "hello",
            "version": 3,
            "transport": "udp",
            "audio_params": {
                "format": "opus",
                "sample_rate":16000,
                "channels":1,
                "frame_duration": 60
            }
        }
        self.send_mqtt_message(message)

    def send_wake_word_detected(self, session_id, wake_word):
        message = {
            "session_id": session_id,
            "type": "listen",
            "state": "detect",
            "text": wake_word
        }
        self.send_mqtt_message(message)

    def send_start_auto_listening(self, session_id):
        message = {
            "session_id": session_id,
            "type": "listen",
            "state": "start",
            "mode": "auto",
        }
        self.send_mqtt_message(message)

    def send_iot_descriptors(self, session_id):
        message = {
            "session_id": session_id,
            "type": "iot",
            "descriptors": [
                {
                    "name": "Speaker",
                    "description": "当前 AI 机器人的扬声器",
                    "properties": {
                        "volume": {
                        "description": "当前音量值",
                        "type": "number"
                        }
                    },
                    "methods": {
                        "SetVolume": {
                            "description": "设置音量",
                            "parameters": {
                                "volume": {
                                "description": "0到100之间的整数",
                                "type": "number"
                                }
                            }
                        }
                    }
                },
                {
                    "name": "Lamp",
                    "description": "一个测试用的灯",
                    "properties": {
                        "power": {
                        "description": "灯是否打开",
                        "type": "boolean"
                        }
                    },
                    "methods": {
                        "TurnOn": {
                        "description": "打开灯",
                        "parameters": {}
                        },
                        "TurnOff": {
                        "description": "关闭灯",
                        "parameters": {}
                        }
                    }
                }
         ]
        }
        self.send_mqtt_message(message)

    def send_iot_states(self, session_id):
        message = {
            "session_id": session_id,
            "type": "iot",
            "states": [
                {
                    "name": "Speaker",
                    "state": {
                        "volume": 0
                    }
                },
                {
                    "name": "Lamp",
                    "state": {
                        "power": False
                    }
                }
            ]
        }
        self.send_mqtt_message(message)

    def send_goodbye(self, session_id):
        message = {
            "session_id": session_id,
            "type": "goodbye"
        }
        self.send_mqtt_message(message)

    def send_mqtt_message(self, message):
        publish_topic = self.mqtt['publish_topic']
        res = self.client.publish(publish_topic, payload=json.dumps(message))
        logger.info("publish_topic %s, send_mqtt_message, %s %s", publish_topic, res, json.dumps(message))

    def on_message(self, callback):
        self.client.on_message = callback

    def open_audio_channel(self):
        self.send_hello()
