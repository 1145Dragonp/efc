import urllib.request
import urllib.parse

# 客户端配置存储
client_config = {}

def start_client():
    """
    模拟启动客户端
    """
    print("[系统] 客户端正在启动... (模拟)")
    # 在此处添加实际的客户端启动代码
    return "客户端已启动"

def connect_to_server(ip_input: str, username: str, password: str):
    """
    配置服务器连接并发送心跳/认证请求
    """
    # 直接使用输入的 IP，假设用户输入的是纯净的 IP 地址或主机名
    clean_ip = ip_input.strip()
    
    # 保存配置
    global client_config
    client_config = {
        "ip": clean_ip,
        "user": username,
        "password": password
    }
    
    # 使用标准库 urllib 发送真实 HTTP 请求
    test_cmd = "ping"
    # 构造 URL，直接使用 IP
    url = f"http://{clean_ip}/?cmd={test_cmd}&user={username}&password={password}"
    
    print(f"[客户端] 配置成功。正在向 {clean_ip} 发送认证请求...")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            result = response.read().decode('utf-8')
            print(f"[响应] {result}")
            
            # 新增: 当客户端登陆时输出信息
            if "Auth=Success" in result:
                print(f"[登录成功] 用户 '{username}' 已成功连接到服务器 {clean_ip}")
            else:
                print(f"[登录失败] 认证未通过，请检查用户名和密码。")
                
    except Exception as e:
        print(f"[错误] 请求失败: {str(e)}")

def send_command_to_server(command: str):
    """
    将命令发送给已配置的服务端
    """
    global client_config
    
    if not client_config or "ip" not in client_config:
        print("[错误] 未配置服务器连接。请先使用 @intoservr 配置。")
        return
        
    ip = client_config["ip"]
    user = client_config["user"]
    password = client_config["password"]
    
    # 对命令进行 URL 编码，防止特殊字符破坏 URL 结构
    encoded_cmd = urllib.parse.quote(command)
    url = f"http://{ip}/?cmd={encoded_cmd}&user={user}&password={password}"
    
    print(f"[发送] 正在向服务器 {ip} 发送命令: {command}")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            result = response.read().decode('utf-8')
            print(f"[服务端响应] {result}")
    except Exception as e:
        print(f"[错误] 发送命令失败: {str(e)}")
