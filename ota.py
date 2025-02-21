import logging
import requests

logger = logging.getLogger(__name__)

class OTA:
    def __init__(self, ota: dict):
        self.url = ota['url']
        self.device_id = ota['device_id']
        self.data = ota['data']

    def init_server_config(self):
        headers = {
            'Device-Id': self.device_id,
            'Content-Type': 'application/json'
        }
        self.data['mac_address'] = self.device_id
        self.data['board']['mac'] = self.device_id
        try:
            response = requests.post(self.url, headers=headers, json=self.data)
            if response.status_code == 200:
                json_data = response.json()
                logger.debug(f"OTA 请求成功: {json_data}")
                return json_data
            else:
                logger.warning(f"OTA 请求失败，状态码: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"OTA 请求出错:", e)
        return None