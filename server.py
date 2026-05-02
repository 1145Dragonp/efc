import threading
import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
# 新增: 导入执行命令的工具函数
from utils import execute_command

# 用户数据文件路径
USER_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user.json")

# 全局用户存储
server_users = {}

def load_users():
    """从文件加载用户数据"""
    global server_users
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                server_users = json.load(f)
            print(f"[服务端] 已加载 {len(server_users)} 个用户。")
        except Exception as e:
            print(f"[警告] 加载用户文件失败: {e}")
            server_users = {}
    else:
        server_users = {}

def save_users():
    """将用户数据保存到文件"""
    try:
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(server_users, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[错误] 保存用户文件失败: {e}")

def start_server(port=8080):
    """
    启动基于标准库 http.server 的简易服务端
    注意：此函数现在主要用于被 subprocess 调用，或在旧模式下使用。
    为了支持远程重启，我们依赖 self.server.shutdown()
    """
    # 启动时加载用户
    load_users()

    print(f"[系统] 服务端正在启动... (使用标准库 http.server, 端口: {port})")
    
    class SimpleAPIHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            # 解析路径和参数
            parsed_path = urlparse(self.path)
            query_params = parse_qs(parsed_path.query)
            
            # 获取参数
            cmd = query_params.get('cmd', [''])[0]
            user = query_params.get('user', [''])[0]
            # 修改: 支持 pw 字段，兼容之前的 password 字段
            password = query_params.get('pw', query_params.get('password', ['']))[0]
            
            # 新增: 打印接收到的请求日志，方便调试
            print(f"[服务端请求] 来自 {self.client_address[0]} | 用户: {user} | 命令: {cmd}")

            response_msg = ""
            
            # 新增: 处理远程重启命令
            if cmd == '__RESTART__':
                print("[服务端] 收到重启指令，正在关闭服务...")
                response_msg = "Auth=Success, Msg=Server Restarting"
                self.send_response(200)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(response_msg.encode('utf-8'))
                # 调度关闭，不能在请求处理线程中直接调用 shutdown 可能会死锁，取决于实现
                # 但通常 shutdown 是线程安全的，或者我们可以用 threading.Timer
                threading.Timer(1, self.server.shutdown).start()
                return

            # 修改: 改进的身份验证检查
            # 1. 检查用户名是否为空
            if not user:
                response_msg = "Auth=Failed, Msg=Username is required"
            # 2. 检查用户是否存在
            elif user not in server_users:
                response_msg = "Auth=Failed, Msg=User not found"
            else:
                stored_password = server_users[user]
                # 3. 验证密码
                is_authenticated = False
                
                # 如果用户设置了密码
                if stored_password:
                    if not password:
                        response_msg = "Auth=Failed, Msg=Password is required"
                    elif stored_password == password:
                        is_authenticated = True
                    else:
                        response_msg = "Auth=Failed, Msg=Invalid password"
                else:
                    # 用户未设置密码 (空密码)
                    # 为了安全，建议不允许空密码登录，或者要求必须显式传递空密码
                    # 这里保持原有逻辑：如果未设置密码，则允许登录，但建议在生产环境中禁用
                    is_authenticated = True
                
                if is_authenticated:
                    if not cmd:
                        response_msg = "Auth=Success, Msg=No command provided"
                    else:
                        # 新增: 实际执行命令
                        print(f"[服务端执行] 正在执行命令: {cmd}")
                        stdout, stderr, code = execute_command(cmd)
                        
                        # 构造返回结果
                        result_output = stdout if stdout else stderr
                        if not result_output:
                            result_output = f"Command executed with code: {code}"
                            
                        response_msg = f"Auth=Success\n--- Output ---\n{result_output}\n--- End ---\nCode: {code}"
                
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(response_msg.encode('utf-8'))
            
        def log_message(self, format, *args):
            # 抑制默认的控制台日志输出，保持界面整洁
            # 如果需要调试 HTTP 底层错误，可以暂时注释掉这行
            pass

    try:
        # 使用传入的端口
        server = HTTPServer(('0.0.0.0', port), SimpleAPIHandler)
        print(f"[服务端] 监听地址: http://0.0.0.0:{port} (所有接口)")
        # 直接运行 serve_forever，阻塞当前进程
        server.serve_forever()
    except Exception as e:
        print(f"[错误] 服务端启动失败: {str(e)}")
        sys.exit(1)

def add_user(username: str, password: str):
    """
    添加新用户到服务端并持久化保存
    """
    server_users[username] = password
    save_users()

# 新增: 允许作为独立脚本运行
if __name__ == "__main__":
    # 可以从命令行参数获取端口，默认为 8080
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("无效端口号，使用默认端口 8080")
    
    start_server(port=port)