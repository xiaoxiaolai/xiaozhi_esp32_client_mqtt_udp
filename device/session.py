import struct
import threading
from .display import Display 
from .status import Status
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import opuslib
import socket
import logging

logger = logging.getLogger(__name__)

application = opuslib.APPLICATION_VOIP
encoder = opuslib.Encoder(16000, 1, application)
encoder.complexity = 5

decoder = opuslib.Decoder(24000, 1)


class Session:
    def __init__(self):
        self.state = Status.Unknown
        self.display = Display()
        self.id = None

        self.udp_server = None
        self.udp_port = None
        self.udp_encryption = None
        self.udp_key = None
        self.udp_nonce = None
        self.udp = None
        self.receive_thread = None
        self.receive_running = False

        self.server_audio_params_sample_rate = None
        self.server_audio_params_format = None
        self.server_audio_params_channels = None
        self.server_audio_params_frame_duration = None

        self.local_sequence = 0

    def set_state(self, state):
        self.state = state
        self.display.show_text(self.state)

    def terminate(self):
        self.id = None
        self.udp_server = None
        self.udp_port = None
        self.udp_encryption = None
        self.udp_key = None
        self.udp_nonce = None
        self.local_sequence = 0
        
        self.receive_running = False
        if self.udp is not None:
            try:
                self.udp.shutdown(socket.SHUT_RD)
            except OSError as e:
                logger.warn("\nServer shutting down...", e)
                pass
            if self.receive_thread:
                self.receive_thread.join()  # 等待线程结束
                self.receive_thread = None
            self.udp.close()
            self.udp = None

        self.server_audio_params_sample_rate = None
        self.server_audio_params_format = None
        self.server_audio_params_channels = None
        self.server_audio_params_frame_duration = None

        self.set_state(Status.Idle)
            
    def upd_send_8(self, data):
        if self.udp is None or self.udp_key is None or self.udp_nonce is None:
            return
        while len(data) >= 1920:
            opus_frame = encoder.encode(data[:1920], 960)
            data = data[1920:]

            aes_key = bytes.fromhex(self.udp_key)
            aes_nonce = bytearray.fromhex(self.udp_nonce)
            self.local_sequence += 1
            struct.pack_into("!H", aes_nonce, 2, len(opus_frame))
            struct.pack_into("!I", aes_nonce, 12, self.local_sequence)

            encrypted_payload = bytearray(aes_nonce)
            encrypted_payload.extend(opus_frame)

            cipher = Cipher(algorithms.AES(aes_key), modes.CTR(bytes(aes_nonce[:16])), backend=default_backend())
            encryptor = cipher.encryptor()
            ciphertext_data = encryptor.update(opus_frame) + encryptor.finalize()

            encrypted_payload[len(aes_nonce):] = ciphertext_data
            self.udp.send(encrypted_payload)
            
    def set_upd_receive_task(self, callback):
        self.receive_running = True
        def udp_receive_thread_function(self, callback):
            try:
                while self.receive_running:
                    data, address = self.udp.recvfrom(1500)
                    if len(data) < 16:
                        continue
                    # remote_sequence = struct.unpack('>I', data[12:16])
                    # opus_frame_Len = struct.unpack('!H', data[2:4])

                    cipher = Cipher(algorithms.AES(bytes.fromhex(self.udp_key)), modes.CTR(bytes(data[:16])), backend=default_backend())
                    encryptor = cipher.decryptor()
                    ciphertext_data = encryptor.update(data[16:]) + encryptor.finalize()
                    pcm_data = decoder.decode(ciphertext_data, 24 * 60)
                    if self.state == Status.Speaking:
                        callback(pcm_data)
            except Exception as e:
                logger.warn("\nServer err...", e)

        self.receive_thread = threading.Thread(target=udp_receive_thread_function, args=(self, callback), daemon=True)
        self.receive_thread.start()