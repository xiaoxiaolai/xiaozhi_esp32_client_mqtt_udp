import json
import logging
import requests
import asyncio
import aiohttp

from device_fingerprint import DeviceFingerprint

logger = logging.getLogger(__name__)

class OTA:
    def __init__(self, ota: dict):
        self.url = ota['url']
        self.data = ota['data']
        self.deviceFingerprint = DeviceFingerprint.get_instance()

    def init_server_config(self):
        headers = {
            'Device-Id': self.deviceFingerprint.get_mac_address_from_efuse(),
            'Client-Id': self.deviceFingerprint.get_client_id_from_efuse(),
            'Content-Type': 'application/json',
            "Activation-Version": "2.0.0",
            "Accept-Language": "zh-CN",
        }
        self.data['application']['elf_sha256'] = self.deviceFingerprint.get_hmac_key()
        try:
            response = requests.post(self.url, headers=headers, json=self.data)
            if response.status_code == 200:
                json_data = response.json()
                logger.debug(f"OTA 请求成功: {json_data}")
                if 'activation' in json_data:
                    asyncio.run(self.activate(json_data['activation']['challenge'], json_data['activation']['code']))
                return json_data
            else:
                logger.warning(f"OTA 请求失败，状态码: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"OTA 请求出错:", e)
        return None

    async def activate(self, challenge: str, code: str = None) -> bool:
        try:
            # 检查序列号
            serial_number = self.deviceFingerprint.get_serial_number()
            if not serial_number:
                logger.error("设备没有序列号，无法完成HMAC验证步骤")
                return False

            # 计算HMAC签名
            hmac_signature = self.deviceFingerprint.generate_hmac(challenge)
            if not hmac_signature:
                logger.error("无法生成HMAC签名，激活失败")
                return False

            # 包装一层外部payload，符合服务器期望格式
            payload = {
                "Payload": {
                    "algorithm": "hmac-sha256",
                    "serial_number": serial_number,
                    "challenge": challenge,
                    "hmac": hmac_signature,
                }
            }

            # 获取激活URL
            ota_url = self.url
            if not ota_url:
                self.logger.error("未找到OTA URL配置")
                return False

            # 确保URL以斜杠结尾
            if not ota_url.endswith("/"):
                ota_url += "/"

            activate_url = f"{ota_url}activate"
            logger.info(f"激活URL: {activate_url}")

            # 设置请求头
            headers = {
                "Activation-Version": "2",
                "Device-Id": self.deviceFingerprint.get_mac_address_from_efuse(),
                "Client-Id": self.deviceFingerprint.get_client_id_from_efuse(),
                "Content-Type": "application/json",
            }

            # 打印调试信息
            logger.debug(f"请求头: {headers}")
            payload_str = json.dumps(payload, indent=2, ensure_ascii=False)
            logger.debug(f"请求负载: {payload_str}")

            # 重试逻辑
            max_retries = 60  # 最长等待5分钟
            retry_interval = 5  # 设置5秒的重试间隔

            error_count = 0
            last_error = None

            # 创建aiohttp会话，设置合理的超时时间
            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                for attempt in range(max_retries):
                    try:
                        logger.info(
                            f"尝试激活 (尝试 {attempt + 1}/{max_retries})..."
                        )
                        text = f".请登录到控制面板添加设备，输入验证码：{' '.join(code)}..."
                        logger.info(text)

                        # 发送激活请求
                        async with session.post(
                            activate_url, headers=headers, json=payload
                        ) as response:
                            # 读取响应
                            response_text = await response.text()

                            # 打印完整响应
                            logger.warning(f"\n激活响应 (HTTP {response.status}):")
                            try:
                                response_json = json.loads(response_text)
                                logger.warning(json.dumps(response_json, indent=2))
                            except json.JSONDecodeError:
                                logger.warning(response_text)

                            # 检查响应状态码
                            if response.status == 200:
                                # 激活成功
                                logger.info("设备激活成功!")
                                return True

                            elif response.status == 202:
                                # 等待用户输入验证码
                                logger.info("等待用户输入验证码，继续等待...")

                                # 使用可取消的等待
                                await asyncio.sleep(retry_interval)

                            else:
                                # 处理其他错误但继续重试
                                error_msg = "未知错误"
                                try:
                                    error_data = json.loads(response_text)
                                    error_msg = error_data.get(
                                        "error", f"未知错误 (状态码: {response.status})"
                                    )
                                except json.JSONDecodeError:
                                    error_msg = (
                                        f"服务器返回错误 (状态码: {response.status})"
                                    )

                                # 记录错误但不终止流程
                                if error_msg != last_error:
                                    logger.warning(
                                        f"服务器返回: {error_msg}，继续等待验证码激活"
                                    )
                                    last_error = error_msg

                                # 计数连续相同错误
                                if "Device not found" in error_msg:
                                    error_count += 1
                                    if error_count >= 5 and error_count % 5 == 0:
                                        logger.warning(
                                            "\n提示: 如果错误持续出现，可能需要在网站上刷新页面获取新验证码\n"
                                        )

                                # 使用可取消的等待
                                await asyncio.sleep(retry_interval)

                    except asyncio.CancelledError:
                        # 响应取消信号
                        logger.info("激活流程被取消")
                        return False

                    except aiohttp.ClientError as e:
                        logger.warning(f"网络请求失败: {e}，重试中...")
                        await asyncio.sleep(retry_interval)

                    except asyncio.TimeoutError as e:
                        logger.warning(f"请求超时: {e}，重试中...")
                        await asyncio.sleep(retry_interval)

                    except Exception as e:
                        # 获取异常的详细信息
                        import traceback

                        error_detail = (
                            str(e) if str(e) else f"{type(e).__name__}: 未知错误"
                        )
                        logger.warning(
                            f"激活过程中发生错误: {error_detail}，重试中..."
                        )
                        # 调试模式下打印完整的异常信息
                        logger.debug(f"完整异常信息: {traceback.format_exc()}")
                        await asyncio.sleep(retry_interval)

            # 达到最大重试次数
            logger.error(
                f"激活失败，达到最大重试次数 ({max_retries})，最后错误: {last_error}"
            )
            return False

        except asyncio.CancelledError:
            logger.info("激活流程被取消")
            return False
