
import json
import socket
import time
import pyaudio
from logger import setup_logging

from device.session import Session
from device.status import Status
from config.load import load_config
from ota import OTA
from protocol.mqtt_protocol import MqttProtocol
from snowboy import snowboydecoder


def main():
    config = load_config()
    logger = setup_logging(config['logger'])
    print("Starting...")
    session = Session()
    session.set_state(state=Status.Starting)
    audio = pyaudio.PyAudio()
    stream_out = audio.open(
        format=audio.get_format_from_width(2),
        channels=1,
        rate=24000,
        input=False,
        output=True)
    stream_out.start_stream()

    def udp_audio_callback(pcm):
        stream_out.write(pcm)

    def hello_handler(client, msg):
        session.id = msg['session_id']

        session.udp_server = msg['udp']['server']
        session.udp_port = msg['udp']['port']
        session.udp_encryption = msg['udp']['encryption']
        session.udp_key = msg['udp']['key']
        session.udp_nonce = msg['udp']['nonce']
        
        session.server_audio_params_sample_rate = msg['audio_params']['sample_rate']
        session.server_audio_params_format = msg['audio_params']['format']
        session.server_audio_params_channels = msg['audio_params']['channels']
        session.server_audio_params_frame_duration = msg['audio_params']['frame_duration']
        
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.connect((session.udp_server, session.udp_port))
        session.udp = client_socket
        session.set_upd_receive_task(udp_audio_callback)
        mqtt.send_iot_descriptors(session_id=session.id)

    def goodbye_handler(client, msg):
        if msg['session_id'] is not None:
            mqtt.send_goodbye(session_id=msg['session_id'])
        if session.id == msg['session_id']:
            session.terminate()
        detector.restart()

    def tts_handler(client, msg):
        if msg['state'] == 'start':
            if session.state == Status.Idle or session.state == Status.Listening:
                session.set_state(state=Status.Speaking)
        if msg['state'] == 'stop':
            if session.state == Status.Speaking:
                mqtt.send_start_auto_listening(session_id=session.id)
                time.sleep(1)
                session.set_state(state=Status.Listening)
        if msg['state'] == 'sentence_start':
            m = msg['text']
            session.display.show_text(f'助手说:{m}')

    def default_handler(client, msg):
        logger.debug("default_handler: %s", msg)

    def stt_handler(client, msg):
        m = msg['text']
        session.display.show_text(f'我说:{m}')

    dispatch_dict = {
        'hello': hello_handler,
        'goodbye': goodbye_handler,
        'tts': tts_handler,
        'stt': stt_handler,
        'llm': default_handler,
        'iot': default_handler,
    }

    def on_message(client, userdata, msg):
        # topic = msg.topic
        m_decode = str(msg.payload.decode("utf-8", "ignore"))
        msg = json.loads(m_decode)
        logger.debug("on_message: %s", msg)
        handler_function = dispatch_dict.get(msg['type'], default_handler)
        handler_function(client, msg)
    
    ota = OTA(config['ota'])
    server_config = ota.init_server_config()

    mqtt = MqttProtocol(server_config['mqtt'])
    mqtt.on_message(on_message)
    detector = snowboydecoder.HotwordDetector(
        decoder_model=config['snowboy']['detector_model'],
        sensitivity=config['snowboy']['sensitivity']
        )
    
    def detected_callback(data):
        if session.state == Status.Idle:
            mqtt.send_hello()
            while session.udp is None:
                time.sleep(0.01)
            session.upd_send_8(data)
            mqtt.send_wake_word_detected(
                session_id=session.id,
                wake_word=config['snowboy']['wake_word']
                )
            session.set_state(state=Status.Listening)
            mqtt.send_iot_states(session_id=session.id)

    session.set_state(state=Status.Idle)

    def audio_callback(data):
        if session.state == Status.Listening:
            session.upd_send_8(data)

    detector.start(detected_callback=detected_callback,
                  sleep_time=0.03,
                  audio_callback=audio_callback
                  )

    detector.terminate()


if __name__ == '__main__':
    main()